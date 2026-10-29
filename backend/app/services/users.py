from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import Forbidden, NotFound
from app.models import Registration, User
from app.schemas import UserUpdate


def normalize_skills(skills: list[str]) -> list[str]:
    """Обрезает пробелы и убирает дубли без учёта регистра, сохраняя первое написание"""
    seen: set[str] = set()
    result = []
    for skill in skills:
        skill = skill.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            result.append(skill)
    return result


async def get_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    return user


async def update_profile(session: AsyncSession, user: User, data: UserUpdate) -> User:
    fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if "skills" in data.model_fields_set and data.skills is not None:
        fields["skills"] = normalize_skills(data.skills)
    for name, value in fields.items():
        setattr(user, name, value)
    await session.commit()
    return user


async def list_participants(
    session: AsyncSession,
    viewer: User,
    hackathon_id: int,
    *,
    skip: int,
    limit: int,
    role_preference: str | None,
    experience_level: str | None,
    skill: str | None,
    search: str | None,
) -> list[User]:
    """Участники хакатона. Список видят только сами участники."""
    registered = (await session.execute(
        select(Registration.id).where(
            Registration.user_id == viewer.id, Registration.hackathon_id == hackathon_id
        )
    )).first()
    if registered is None:
        raise Forbidden("You must register for the hackathon first")

    query = (
        select(User)
        .join(Registration, Registration.user_id == User.id)
        .where(Registration.hackathon_id == hackathon_id, User.id != viewer.id)
    )
    if role_preference:
        query = query.where(User.role_preference == role_preference)
    if experience_level:
        query = query.where(User.experience_level == experience_level)
    if skill:
        query = query.where(
            text("EXISTS (SELECT 1 FROM unnest(users.skills) AS s WHERE lower(s) = :skill)")
            .bindparams(skill=skill.strip().lower())
        )
    if search:
        query = query.where(User.full_name.icontains(search, autoescape=True))

    result = await session.execute(query.order_by(User.id).offset(skip).limit(limit))
    return list(result.scalars())
