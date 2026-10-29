from fastapi import APIRouter, Response

from app.db import SessionDep
from app.deps import CurrentAdmin
from app.schemas import AssignUserRequest, HackathonAnalytics, HackathonOut
from app.services import admin as service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _csv(content: str, filename: str) -> Response:
    # BOM нужен, чтобы Excel правильно прочитал кириллицу в UTF-8
    return Response(
        content="﻿" + content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/hackathons", response_model=list[HackathonOut])
async def hackathons(_: CurrentAdmin, session: SessionDep):
    return await service.list_all_hackathons(session)


@router.get("/{hackathon_id}/analytics", response_model=HackathonAnalytics)
async def analytics(hackathon_id: int, _: CurrentAdmin, session: SessionDep):
    return await service.analytics(session, hackathon_id)


@router.get("/{hackathon_id}/participants/export")
async def export_participants(hackathon_id: int, _: CurrentAdmin, session: SessionDep):
    return _csv(await service.export_participants(session, hackathon_id), f"participants_{hackathon_id}.csv")


@router.get("/{hackathon_id}/teams/export")
async def export_teams(hackathon_id: int, _: CurrentAdmin, session: SessionDep):
    return _csv(await service.export_teams(session, hackathon_id), f"teams_{hackathon_id}.csv")


@router.post("/hackathons/{hackathon_id}/assign-user")
async def assign_user(hackathon_id: int, body: AssignUserRequest, _: CurrentAdmin, session: SessionDep):
    message = await service.assign_user(session, hackathon_id, body.user_id, body.team_id)
    return {"message": message, "user_id": body.user_id, "team_id": body.team_id}
