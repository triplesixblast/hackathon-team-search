from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    Hackathon,
    Invitation,
    InvitationKind,
    InvitationStatus,
    Registration,
    Team,
    TeamStatus,
    User,
    utcnow,
)
from app.schemas import (
    HackathonOut,
    MyTeamItem,
    PublicUser,
    TeamCreate,
    TeamDetail,
    TeamMemberOut,
    TeamOut,
    TeamUpdate,
)
from app.services.hackathons import ensure_open, get_hackathon, get_registration

TEAM_OPTIONS = (
    selectinload(Team.registrations).selectinload(Registration.user),
    joinedload(Team.hackathon),
)


# ───────── загрузка и представление ─────────

async def load_team(session: AsyncSession, team_id: int) -> Team:
    """Команда с участниками и хакатоном (данные обновляются из БД)"""
    team = (await session.execute(
        select(Team).where(Team.id == team_id).options(*TEAM_OPTIONS)
        .execution_options(populate_existing=True)
    )).unique().scalar_one_or_none()
    if team is None:
        raise NotFound("Team not found")
    return team


async def lock_user(session: AsyncSession, user_id: int) -> None:
    """Блокировка «на пользователя» до конца транзакции (advisory lock, пространство 1)"""
    await session.execute(select(func.pg_advisory_xact_lock(1, user_id)))


async def lock_team(session: AsyncSession, team_id: int) -> Team:
    """Блокировка строки команды на время транзакции"""
    team = (await session.execute(
        select(Team).where(Team.id == team_id).with_for_update()
    )).scalar_one_or_none()
    if team is None:
        raise NotFound("Team not found")
    return team


def team_out(team: Team) -> TeamOut:
    """Команда с участниками; капитан первым. Нужны загруженные registrations.user и hackathon."""
    members = sorted(team.registrations, key=lambda r: r.user_id != team.captain_id)
    return TeamOut(
        id=team.id,
        hackathon_id=team.hackathon_id,
        name=team.name,
        description=team.description,
        captain_id=team.captain_id,
        status=team.status,
        created_at=team.created_at,
        members=[
            TeamMemberOut(
                id=r.user.id, full_name=r.user.full_name,
                role_preference=r.user.role_preference, skills=r.user.skills,
            )
            for r in members
        ],
        max_team_size=team.hackathon.max_team_size,
    )


async def team_detail(session: AsyncSession, team_id: int) -> TeamDetail:
    team = await load_team(session, team_id)
    captain = await session.get(User, team.captain_id)
    return TeamDetail(
        **team_out(team).model_dump(),
        captain=PublicUser.model_validate(captain),
        hackathon=HackathonOut.model_validate(team.hackathon),
    )


# ───────── общие правила ─────────

async def cancel_pending_for_user(
    session: AsyncSession, user_id: int, hackathon_id: int, keep_id: int | None = None
) -> None:
    """Пользователь вошёл в команду: его остальные заявки и приглашения этого хакатона закрываются"""
    stmt = (
        update(Invitation)
        .where(
            Invitation.user_id == user_id,
            Invitation.status == InvitationStatus.PENDING,
            Invitation.team_id.in_(select(Team.id).where(Team.hackathon_id == hackathon_id)),
        )
        .values(status=InvitationStatus.CANCELLED, responded_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if keep_id is not None:
        stmt = stmt.where(Invitation.id != keep_id)
    await session.execute(stmt)


async def member_count(session: AsyncSession, team_id: int) -> int:
    return (await session.execute(
        select(func.count()).select_from(Registration).where(Registration.team_id == team_id)
    )).scalar_one()


async def join_team(
    session: AsyncSession, team: Team, user_id: int, *, force: bool = False,
    keep_invitation_id: int | None = None,
) -> None:
    """
    Добавить пользователя в команду. team должна быть заблокирована (lock_team).
    force=True (действие админа) пропускает проверки статуса хакатона/команды и лимита.
    """
    hackathon = await session.get(Hackathon, team.hackathon_id)
    if not force:
        ensure_open(hackathon)
        if team.status != TeamStatus.OPEN:
            raise BadRequest("Team is not accepting new members")
        if await member_count(session, team.id) >= hackathon.max_team_size:
            raise BadRequest(f"Team is full. Maximum team size is {hackathon.max_team_size}")

    registration = await get_registration(session, user_id, team.hackathon_id, lock=True)
    if registration is None:
        raise BadRequest("User must register for the hackathon first")
    if registration.team_id == team.id:
        raise BadRequest("User is already a member of this team")
    if registration.team_id is not None:
        raise BadRequest("User is already in a team for this hackathon")

    registration.team_id = team.id
    registration.joined_team_at = utcnow()
    await cancel_pending_for_user(session, user_id, team.hackathon_id, keep_id=keep_invitation_id)


async def _remove_from_team(session: AsyncSession, team: Team, user_id: int) -> None:
    registration = (await session.execute(
        select(Registration).where(Registration.team_id == team.id, Registration.user_id == user_id)
        .with_for_update()
    )).scalar_one_or_none()
    if registration is None:
        raise NotFound("Member not found in team")
    registration.team_id = None
    registration.joined_team_at = None


# ───────── команды ─────────

async def create_team(session: AsyncSession, user: User, data: TeamCreate) -> TeamDetail:
    await lock_user(session, user.id)
    hackathon = await get_hackathon(session, data.hackathon_id)
    ensure_open(hackathon)

    registration = await get_registration(session, user.id, data.hackathon_id, lock=True)
    if registration is None:
        raise BadRequest("You must register for the hackathon first")
    if registration.team_id is not None:
        raise BadRequest("You are already in a team for this hackathon")

    team = Team(
        hackathon_id=data.hackathon_id, captain_id=user.id, name=data.name, description=data.description
    )
    session.add(team)
    try:
        await session.flush()
    except IntegrityError:  # параллельный запрос успел создать команду
        raise Conflict("You have already created a team for this hackathon") from None

    registration.team_id = team.id
    registration.joined_team_at = utcnow()
    await cancel_pending_for_user(session, user.id, data.hackathon_id)
    await session.commit()
    return await team_detail(session, team.id)


async def can_create_team(session: AsyncSession, user: User, hackathon_id: int) -> tuple[bool, str | None]:
    hackathon = await session.get(Hackathon, hackathon_id)
    if hackathon is None:
        return False, "Hackathon not found"
    if hackathon.status.value == "finished":
        return False, "Hackathon is finished"
    registration = await get_registration(session, user.id, hackathon_id)
    if registration is None:
        return False, "You must register for the hackathon first"
    if registration.team_id is not None:
        return False, "You are already in a team for this hackathon"
    return True, None


async def my_teams(session: AsyncSession, user: User) -> list[MyTeamItem]:
    result = await session.execute(
        select(Team)
        .join(Registration, Registration.team_id == Team.id)
        .where(Registration.user_id == user.id)
        .options(joinedload(Team.hackathon))
        .order_by(Team.id)
    )
    return [
        MyTeamItem(
            id=t.id, name=t.name, description=t.description, hackathon_id=t.hackathon_id,
            hackathon_name=t.hackathon.name, status=t.status,
        )
        for t in result.unique().scalars()
    ]


async def list_teams(session: AsyncSession, hackathon_id: int, status: TeamStatus) -> list[TeamOut]:
    result = await session.execute(
        select(Team).where(Team.hackathon_id == hackathon_id, Team.status == status)
        .options(*TEAM_OPTIONS).order_by(Team.id)
    )
    return [team_out(t) for t in result.unique().scalars()]


async def _team_as_captain(session: AsyncSession, team_id: int, user: User) -> Team:
    team = await lock_team(session, team_id)
    if team.captain_id != user.id:
        raise Forbidden("Only team captain can do this")
    return team


async def update_team(session: AsyncSession, user: User, team_id: int, data: TeamUpdate) -> TeamOut:
    team = await _team_as_captain(session, team_id, user)
    for name, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(team, name, value)
    await session.commit()
    return team_out(await load_team(session, team_id))


async def delete_team(session: AsyncSession, user: User, team_id: int) -> None:
    """Расформировать команду. Участники остаются зарегистрированными на хакатон."""
    team = await _team_as_captain(session, team_id, user)
    await session.execute(
        update(Registration).where(Registration.team_id == team_id)
        .values(team_id=None, joined_team_at=None).execution_options(synchronize_session=False)
    )
    await session.delete(team)  # приглашения удаляются каскадом
    await session.commit()


async def transfer_captain(session: AsyncSession, user: User, team_id: int, new_captain_id: int) -> None:
    team = await _team_as_captain(session, team_id, user)
    if new_captain_id == user.id:
        raise BadRequest("You are already the captain")
    member = (await session.execute(
        select(Registration.id).where(Registration.team_id == team_id, Registration.user_id == new_captain_id)
    )).first()
    if member is None:
        raise BadRequest("New captain must be a member of the team")
    team.captain_id = new_captain_id
    await session.commit()


async def remove_member(session: AsyncSession, actor: User, team_id: int, user_id: int) -> None:
    """Исключить участника (капитан) или выйти самому. Капитана исключить нельзя."""
    team = await lock_team(session, team_id)
    if team.captain_id != actor.id and actor.id != user_id:
        raise Forbidden("You don't have permission to remove this member")
    if user_id == team.captain_id:
        raise BadRequest("Team captain cannot be removed. Transfer captaincy first or delete the team.")
    await _remove_from_team(session, team, user_id)
    await session.commit()


async def leave_team(session: AsyncSession, user: User, team_id: int) -> None:
    team = await lock_team(session, team_id)
    if team.captain_id == user.id:
        raise BadRequest(
            "Team captain cannot leave the team. Transfer captaincy first or delete the team."
        )
    try:
        await _remove_from_team(session, team, user.id)
    except NotFound:
        raise NotFound("You are not a member of this team") from None
    await session.commit()


# ───────── заявки и приглашения (создание) ─────────

async def _add_invitation(session: AsyncSession, invitation: Invitation, conflict_message: str) -> Invitation:
    session.add(invitation)
    try:
        await session.commit()
    except IntegrityError:  # частичный уникальный индекс: уже есть ожидающее на эту пару
        raise Conflict(conflict_message) from None
    return invitation


async def apply_to_team(session: AsyncSession, user: User, team_id: int) -> Invitation:
    """Заявка пользователя в команду: инициатор — пользователь, отвечает капитан"""
    team = await load_team(session, team_id)
    if team.captain_id == user.id:
        raise BadRequest("You are the captain of this team")
    ensure_open(team.hackathon)
    if team.status != TeamStatus.OPEN:
        raise BadRequest("Team is not accepting new members")
    if len(team.registrations) >= team.hackathon.max_team_size:
        raise BadRequest(f"Team is full. Maximum team size is {team.hackathon.max_team_size}")

    registration = await get_registration(session, user.id, team.hackathon_id)
    if registration is None:
        raise BadRequest("You must register for the hackathon first")
    if registration.team_id == team.id:
        raise BadRequest("You are already a member of this team")
    if registration.team_id is not None:
        raise BadRequest("You are already in another team for this hackathon")

    return await _add_invitation(
        session,
        Invitation(team_id=team.id, user_id=user.id, sent_by_id=user.id, kind=InvitationKind.APPLICATION),
        "You already have a pending invitation or application to this team",
    )


async def invite_to_team(session: AsyncSession, captain: User, team_id: int, user_id: int) -> Invitation:
    """Приглашение капитана: инициатор — капитан, отвечает приглашённый"""
    team = await load_team(session, team_id)
    if team.captain_id != captain.id:
        raise Forbidden("Only team captain can send invitations")
    ensure_open(team.hackathon)
    if team.status != TeamStatus.OPEN:
        raise BadRequest("Team is not accepting new members")
    if len(team.registrations) >= team.hackathon.max_team_size:
        raise BadRequest(f"Team is full. Maximum team size is {team.hackathon.max_team_size}")

    if await session.get(User, user_id) is None:
        raise NotFound("User not found")
    registration = await get_registration(session, user_id, team.hackathon_id)
    if registration is None:
        raise BadRequest("User is not registered for this hackathon")
    if registration.team_id is not None:
        raise BadRequest("User is already in a team for this hackathon")

    return await _add_invitation(
        session,
        Invitation(team_id=team.id, user_id=user_id, sent_by_id=captain.id, kind=InvitationKind.INVITE),
        "User already has a pending invitation or application",
    )
