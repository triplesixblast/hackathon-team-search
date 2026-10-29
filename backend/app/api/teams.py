from fastapi import APIRouter

from app.db import SessionDep
from app.deps import CurrentUser
from app.models import TeamStatus
from app.schemas import CanCreateTeam, MyTeamItem, TeamCreate, TeamDetail, TeamOut, TeamUpdate
from app.services import teams as service

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("", response_model=TeamDetail)
async def create_team(body: TeamCreate, user: CurrentUser, session: SessionDep):
    return await service.create_team(session, user, body)


@router.get("/my", response_model=list[MyTeamItem])
async def my_teams(user: CurrentUser, session: SessionDep):
    return await service.my_teams(session, user)


@router.get("/can-create/{hackathon_id}", response_model=CanCreateTeam)
async def can_create(hackathon_id: int, user: CurrentUser, session: SessionDep):
    allowed, reason = await service.can_create_team(session, user, hackathon_id)
    return CanCreateTeam(can_create=allowed, reason=reason)


@router.get("/hackathons/{hackathon_id}", response_model=list[TeamOut])
async def list_teams(
    hackathon_id: int, _: CurrentUser, session: SessionDep, status_filter: TeamStatus = TeamStatus.OPEN
):
    return await service.list_teams(session, hackathon_id, status_filter)


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(team_id: int, _: CurrentUser, session: SessionDep):
    return await service.team_detail(session, team_id)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(team_id: int, body: TeamUpdate, user: CurrentUser, session: SessionDep):
    return await service.update_team(session, user, team_id, body)


@router.delete("/{team_id}")
async def delete_team(team_id: int, user: CurrentUser, session: SessionDep):
    await service.delete_team(session, user, team_id)
    return {"message": "Team deleted"}


@router.post("/{team_id}/apply")
async def apply(team_id: int, user: CurrentUser, session: SessionDep):
    invitation = await service.apply_to_team(session, user, team_id)
    return {
        "message": "Application sent. The team captain will review your request.",
        "invitation_id": invitation.id,
    }


@router.post("/{team_id}/invite")
async def invite(team_id: int, user_id: int, user: CurrentUser, session: SessionDep):
    invitation = await service.invite_to_team(session, user, team_id, user_id)
    return {"message": "Invitation sent", "invitation_id": invitation.id}


@router.post("/{team_id}/leave")
async def leave(team_id: int, user: CurrentUser, session: SessionDep):
    await service.leave_team(session, user, team_id)
    return {"message": "You have left the team"}


@router.post("/{team_id}/transfer-captain")
async def transfer_captain(team_id: int, user_id: int, user: CurrentUser, session: SessionDep):
    await service.transfer_captain(session, user, team_id, user_id)
    return {"message": "Captaincy transferred", "captain_id": user_id}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(team_id: int, user_id: int, user: CurrentUser, session: SessionDep):
    await service.remove_member(session, user, team_id, user_id)
    return {"message": "Member removed from team"}
