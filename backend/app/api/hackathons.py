from typing import Annotated

from fastapi import APIRouter, Query

from app.db import SessionDep
from app.deps import CurrentAdmin, CurrentUser
from app.schemas import HackathonCreate, HackathonDetail, HackathonOut, HackathonUpdate
from app.services import hackathons as service

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


@router.get("", response_model=list[HackathonOut])
async def list_hackathons(
    _: CurrentUser,
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return await service.list_hackathons(session, skip, limit)


@router.get("/{hackathon_id}", response_model=HackathonDetail)
async def get_hackathon(hackathon_id: int, user: CurrentUser, session: SessionDep):
    hackathon = await service.get_hackathon(session, hackathon_id)
    registration = await service.get_registration(session, user.id, hackathon_id)
    return HackathonDetail(
        **HackathonOut.model_validate(hackathon).model_dump(),
        is_registered=registration is not None,
        team_id=registration.team_id if registration else None,
    )


@router.post("/{hackathon_id}/register")
async def register(hackathon_id: int, user: CurrentUser, session: SessionDep):
    await service.register(session, user, hackathon_id)
    return {"message": "Registered successfully", "hackathon_id": hackathon_id}


@router.post("", response_model=HackathonOut)
async def create_hackathon(body: HackathonCreate, _: CurrentAdmin, session: SessionDep):
    return await service.create_hackathon(session, body)


@router.put("/{hackathon_id}", response_model=HackathonOut)
async def update_hackathon(hackathon_id: int, body: HackathonUpdate, _: CurrentAdmin, session: SessionDep):
    return await service.update_hackathon(session, hackathon_id, body)
