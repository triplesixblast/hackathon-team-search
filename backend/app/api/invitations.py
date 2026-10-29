from fastapi import APIRouter

from app.db import SessionDep
from app.deps import CurrentUser
from app.schemas import InvitationOut, InvitationReply
from app.services import invitations as service

router = APIRouter(prefix="/api/invitations", tags=["invitations"])


@router.get("", response_model=list[InvitationOut])
async def my_invitations(user: CurrentUser, session: SessionDep):
    return await service.list_mine(session, user)


@router.get("/applications", response_model=list[InvitationOut])
async def applications(user: CurrentUser, session: SessionDep):
    return await service.list_applications(session, user)


@router.get("/team/{team_id}/pending", response_model=list[InvitationOut])
async def team_pending(team_id: int, user: CurrentUser, session: SessionDep):
    return await service.list_team_pending(session, user, team_id)


@router.post("/{invitation_id}/accept")
async def respond(invitation_id: int, user: CurrentUser, session: SessionDep, body: InvitationReply | None = None):
    accept = body.accept if body else True
    await service.respond_to_invitation(session, user, invitation_id, accept)
    return {"message": f"Invitation {'accepted' if accept else 'declined'}", "invitation_id": invitation_id}


@router.post("/{invitation_id}/approve")
async def approve(invitation_id: int, user: CurrentUser, session: SessionDep):
    await service.approve_application(session, user, invitation_id)
    return {"message": "Application approved", "invitation_id": invitation_id}


@router.post("/{invitation_id}/reject")
async def reject(invitation_id: int, user: CurrentUser, session: SessionDep):
    await service.reject_application(session, user, invitation_id)
    return {"message": "Application rejected", "invitation_id": invitation_id}


@router.delete("/{invitation_id}")
async def cancel(invitation_id: int, user: CurrentUser, session: SessionDep):
    await service.cancel_invitation(session, user, invitation_id)
    return {"message": "Invitation cancelled", "invitation_id": invitation_id}
