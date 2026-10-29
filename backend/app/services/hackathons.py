from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BadRequest, Conflict, NotFound
from app.models import Hackathon, HackathonStatus, Registration, User
from app.schemas import HackathonCreate, HackathonUpdate


async def get_hackathon(session: AsyncSession, hackathon_id: int) -> Hackathon:
    hackathon = await session.get(Hackathon, hackathon_id)
    if hackathon is None:
        raise NotFound("Hackathon not found")
    return hackathon


def ensure_open(hackathon: Hackathon) -> None:
    """В завершённом хакатоне нельзя регистрироваться и менять составы команд"""
    if hackathon.status == HackathonStatus.FINISHED:
        raise BadRequest("Hackathon is finished")


async def list_hackathons(session: AsyncSession, skip: int, limit: int, newest_first: bool = False):
    order = Hackathon.created_at.desc() if newest_first else Hackathon.id
    result = await session.execute(select(Hackathon).order_by(order, Hackathon.id).offset(skip).limit(limit))
    return list(result.scalars())


async def get_registration(
    session: AsyncSession, user_id: int, hackathon_id: int, *, lock: bool = False
) -> Registration | None:
    query = select(Registration).where(
        Registration.user_id == user_id, Registration.hackathon_id == hackathon_id
    )
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def register(session: AsyncSession, user: User, hackathon_id: int) -> None:
    hackathon = await get_hackathon(session, hackathon_id)
    ensure_open(hackathon)
    session.add(Registration(user_id=user.id, hackathon_id=hackathon_id))
    try:
        await session.commit()
    except IntegrityError:  # уже зарегистрирован (в т.ч. параллельный запрос)
        raise Conflict("Already registered for this hackathon") from None


async def create_hackathon(session: AsyncSession, data: HackathonCreate) -> Hackathon:
    hackathon = Hackathon(**data.model_dump())
    session.add(hackathon)
    try:
        await session.commit()
    except IntegrityError:
        raise Conflict("Hackathon with this name already exists") from None
    return hackathon


async def update_hackathon(session: AsyncSession, hackathon_id: int, data: HackathonUpdate) -> Hackathon:
    hackathon = await get_hackathon(session, hackathon_id)
    fields = data.model_dump(exclude_unset=True, exclude_none=True)

    start = fields.get("start_date", hackathon.start_date)
    end = fields.get("end_date", hackathon.end_date)
    if end <= start:
        raise BadRequest("end_date must be later than start_date")

    if "max_team_size" in fields:
        sizes = (
            select(func.count().label("n"))
            .where(Registration.hackathon_id == hackathon_id, Registration.team_id.is_not(None))
            .group_by(Registration.team_id)
            .subquery()
        )
        biggest = (await session.execute(select(func.coalesce(func.max(sizes.c.n), 0)))).scalar_one()
        if fields["max_team_size"] < biggest:
            raise BadRequest(f"Some team already has {biggest} members")

    for name, value in fields.items():
        setattr(hackathon, name, value)
    try:
        await session.commit()
    except IntegrityError:
        raise Conflict("Hackathon with this name already exists") from None
    return hackathon
