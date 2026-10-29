import csv
import io

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.errors import BadRequest, NotFound
from app.models import Hackathon, Registration, Team, User
from app.schemas import HackathonAnalytics
from app.services.hackathons import get_hackathon, get_registration
from app.services.teams import cancel_pending_for_user, join_team, lock_team, lock_user

# Excel/LibreOffice исполняют ячейки, начинающиеся с этих символов, как формулы
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Защита от CSV-инъекции: текст, похожий на формулу, экранируется апострофом"""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _to_csv(header: list[str], rows: list[list]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows([[csv_safe(c) for c in row] for row in rows])
    return out.getvalue()


async def analytics(session: AsyncSession, hackathon_id: int) -> HackathonAnalytics:
    await get_hackathon(session, hackathon_id)

    total_participants, in_team = (await session.execute(
        select(func.count(), func.count(Registration.team_id)).where(Registration.hackathon_id == hackathon_id)
    )).one()
    total_teams = (await session.execute(
        select(func.count()).select_from(Team).where(Team.hackathon_id == hackathon_id)
    )).scalar_one()

    skills = (await session.execute(text("""
        SELECT lower(s) AS skill, count(*) AS n
        FROM registrations r
        JOIN users u ON u.id = r.user_id
        CROSS JOIN LATERAL unnest(u.skills) AS s
        WHERE r.hackathon_id = :hid
        GROUP BY 1 ORDER BY 2 DESC, 1
    """), {"hid": hackathon_id})).all()
    levels = (await session.execute(
        select(User.experience_level, func.count())
        .join(Registration, Registration.user_id == User.id)
        .where(Registration.hackathon_id == hackathon_id)
        .group_by(User.experience_level)
    )).all()

    return HackathonAnalytics(
        total_participants=total_participants,
        total_teams=total_teams,
        participants_in_team=in_team,
        participants_without_team=total_participants - in_team,
        average_team_size=round(in_team / total_teams, 2) if total_teams else 0,
        skills_frequency={skill: n for skill, n in skills},
        experience_distribution={level: n for level, n in levels},
    )


async def export_participants(session: AsyncSession, hackathon_id: int) -> str:
    await get_hackathon(session, hackathon_id)
    rows = (await session.execute(
        select(User, Team)
        .join(Registration, Registration.user_id == User.id)
        .outerjoin(Team, Team.id == Registration.team_id)
        .where(Registration.hackathon_id == hackathon_id)
        .order_by(User.id)
    )).all()
    return _to_csv(
        ["ID", "Full Name", "Telegram Username", "Skills", "Role Preference",
         "Experience Level", "Team Name", "Team Status"],
        [
            [u.id, u.full_name, u.telegram_username or "", ", ".join(u.skills),
             u.role_preference or "", u.experience_level,
             t.name if t else "", t.status.value if t else ""]
            for u, t in rows
        ],
    )


async def export_teams(session: AsyncSession, hackathon_id: int) -> str:
    await get_hackathon(session, hackathon_id)
    teams = (await session.execute(
        select(Team).where(Team.hackathon_id == hackathon_id)
        .options(joinedload(Team.captain), selectinload(Team.registrations).selectinload(Registration.user))
        .order_by(Team.id)
    )).unique().scalars()
    return _to_csv(
        ["Team ID", "Team Name", "Team Status", "Captain Name", "Member Count", "Members"],
        [
            [t.id, t.name, t.status.value, t.captain.full_name, len(t.registrations),
             ", ".join(r.user.full_name for r in t.registrations)]
            for t in teams
        ],
    )


async def assign_user(
    session: AsyncSession, hackathon_id: int, user_id: int, team_id: int | None
) -> str:
    """Ручное распределение: team_id — добавить в команду, None — оставить без команды"""
    await get_hackathon(session, hackathon_id)
    if await session.get(User, user_id) is None:
        raise NotFound("User not found")
    await lock_user(session, user_id)
    registration = await get_registration(session, user_id, hackathon_id, lock=True)

    if team_id is None:
        if registration is None:
            raise BadRequest("User is not registered for this hackathon")
        if registration.team_id is not None:
            team = await session.get(Team, registration.team_id)
            if team.captain_id == user_id:
                raise BadRequest("Team captain cannot be unassigned. Transfer captaincy first.")
            registration.team_id = None
            registration.joined_team_at = None
        await session.commit()
        return "User unassigned from any team in this hackathon"

    team = await session.get(Team, team_id)
    if team is None or team.hackathon_id != hackathon_id:
        raise BadRequest("Team not found in this hackathon")

    if registration is None:  # админ может записать на хакатон сам
        registration = Registration(user_id=user_id, hackathon_id=hackathon_id)
        session.add(registration)
        await session.flush()
    await lock_team(session, team_id)
    await join_team(session, team, user_id, force=True)
    await cancel_pending_for_user(session, user_id, hackathon_id)
    await session.commit()
    return "User assigned to team"


async def list_all_hackathons(session: AsyncSession) -> list[Hackathon]:
    result = await session.execute(select(Hackathon).order_by(Hackathon.created_at.desc(), Hackathon.id.desc()))
    return list(result.scalars())
