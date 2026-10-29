from typing import Annotated

from fastapi import APIRouter, Query

from app.db import SessionDep
from app.deps import CurrentUser
from app.schemas import PublicUser, UserListItem, UserProfile, UserUpdate
from app.services import users as service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_me(user: CurrentUser):
    return user


@router.put("/me", response_model=UserProfile)
async def update_me(body: UserUpdate, user: CurrentUser, session: SessionDep):
    return await service.update_profile(session, user, body)


@router.get("/hackathons/{hackathon_id}/participants", response_model=list[UserListItem])
async def participants(
    hackathon_id: int,
    user: CurrentUser,
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    role_preference: str | None = None,
    experience_level: str | None = None,
    skill: str | None = None,
    search: str | None = None,
):
    return await service.list_participants(
        session, user, hackathon_id, skip=skip, limit=limit, role_preference=role_preference,
        experience_level=experience_level, skill=skill, search=search,
    )


@router.get("/{user_id}", response_model=PublicUser)
async def get_user(user_id: int, _: CurrentUser, session: SessionDep):
    return await service.get_user(session, user_id)
