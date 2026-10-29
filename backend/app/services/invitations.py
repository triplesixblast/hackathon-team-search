from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.errors import BadRequest, Forbidden, NotFound
from app.models import (
    Invitation,
    InvitationKind,
    InvitationStatus,
    Registration,
    Team,
    User,
    utcnow,
)
from app.schemas import InvitationOut, PublicUser
from app.services.teams import join_team, lock_team, lock_user, team_out

# Сколько дней показывать пользователю результат его заявки
RESULT_VISIBLE_DAYS = 7

INVITATION_OPTIONS = (
    selectinload(Invitation.team).options(
        selectinload(Team.registrations).selectinload(Registration.user),
        joinedload(Team.hackathon),
    ),
    joinedload(Invitation.sent_by),
    joinedload(Invitation.user),
)


def invitation_out(inv: Invitation) -> InvitationOut:
    return InvitationOut(
        id=inv.id,
        team_id=inv.team_id,
        user_id=inv.user_id,
        sent_by_id=inv.sent_by_id,
        kind=inv.kind,
        status=inv.status,
        created_at=inv.created_at,
        responded_at=inv.responded_at,
        team=team_out(inv.team),
        sent_by=PublicUser.model_validate(inv.sent_by),
        user=PublicUser.model_validate(inv.user),
    )


async def _fetch(session: AsyncSession, *conditions, order) -> list[InvitationOut]:
    result = await session.execute(
        select(Invitation).where(*conditions).options(*INVITATION_OPTIONS).order_by(order)
    )
    return [invitation_out(i) for i in result.unique().scalars()]


async def list_mine(session: AsyncSession, user: User) -> list[InvitationOut]:
    """Входящие приглашения в ожидании и недавние результаты собственных заявок"""
    since = utcnow() - timedelta(days=RESULT_VISIBLE_DAYS)
    return await _fetch(
        session,
        Invitation.user_id == user.id,
        or_(
            (Invitation.kind == InvitationKind.INVITE) & (Invitation.status == InvitationStatus.PENDING),
            (Invitation.kind == InvitationKind.APPLICATION)
            & Invitation.status.in_([InvitationStatus.ACCEPTED, InvitationStatus.DECLINED])
            & (Invitation.responded_at >= since),
        ),
        order=Invitation.created_at.desc(),
    )


async def list_applications(session: AsyncSession, captain: User) -> list[InvitationOut]:
    """Ожидающие заявки в команды, где текущий пользователь — капитан"""
    return await _fetch(
        session,
        Invitation.kind == InvitationKind.APPLICATION,
        Invitation.status == InvitationStatus.PENDING,
        Invitation.team_id.in_(select(Team.id).where(Team.captain_id == captain.id)),
        order=Invitation.created_at,
    )


async def list_team_pending(session: AsyncSession, captain: User, team_id: int) -> list[InvitationOut]:
    """Отправленные капитаном приглашения, на которые ещё нет ответа"""
    team = await session.get(Team, team_id)
    if team is None:
        raise NotFound("Team not found")
    if team.captain_id != captain.id:
        raise Forbidden("Only team captain can view invitations")
    return await _fetch(
        session,
        Invitation.team_id == team_id,
        Invitation.kind == InvitationKind.INVITE,
        Invitation.status == InvitationStatus.PENDING,
        order=Invitation.created_at,
    )


async def _lock_invitation(session: AsyncSession, invitation_id: int) -> Invitation:
    invitation = (await session.execute(
        select(Invitation).where(Invitation.id == invitation_id).with_for_update()
    )).scalar_one_or_none()
    if invitation is None:
        raise NotFound("Invitation not found")
    return invitation


def _ensure_pending(invitation: Invitation, message: str = "Invitation already processed") -> None:
    if invitation.status != InvitationStatus.PENDING:
        raise BadRequest(message)


async def respond_to_invitation(session: AsyncSession, user: User, invitation_id: int, accept: bool) -> None:
    """Приглашённый принимает или отклоняет приглашение капитана"""
    await lock_user(session, user.id)
    invitation = await _lock_invitation(session, invitation_id)
    if invitation.user_id != user.id:
        raise Forbidden("This invitation is not for you")
    if invitation.kind != InvitationKind.INVITE:
        raise BadRequest("This is an application, not an invitation. Please wait for the captain's response.")
    _ensure_pending(invitation)

    if accept:
        team = await lock_team(session, invitation.team_id)
        await join_team(session, team, user.id, keep_invitation_id=invitation.id)
        invitation.status = InvitationStatus.ACCEPTED
    else:
        invitation.status = InvitationStatus.DECLINED
    invitation.responded_at = utcnow()
    await session.commit()


async def _application_for_captain(
    session: AsyncSession, captain: User, invitation_id: int, *, joins_user: bool
) -> Invitation:
    if joins_user:
        # порядок блокировок: сначала пользователь, которого добавляем (его id знаем из заявки)
        preview = await session.get(Invitation, invitation_id)
        if preview is not None:
            await lock_user(session, preview.user_id)
    invitation = await _lock_invitation(session, invitation_id)
    team = await session.get(Team, invitation.team_id)
    if team.captain_id != captain.id:
        raise Forbidden("Only team captain can answer applications")
    if invitation.kind != InvitationKind.APPLICATION:
        raise BadRequest("This is an invitation, not an application")
    _ensure_pending(invitation, "Application already processed")
    return invitation


async def approve_application(session: AsyncSession, captain: User, invitation_id: int) -> None:
    invitation = await _application_for_captain(session, captain, invitation_id, joins_user=True)
    team = await lock_team(session, invitation.team_id)
    try:
        await join_team(session, team, invitation.user_id, keep_invitation_id=invitation.id)
    except BadRequest as e:
        raise BadRequest(e.detail.replace("User must", "The applicant must")) from None
    invitation.status = InvitationStatus.ACCEPTED
    invitation.responded_at = utcnow()
    await session.commit()


async def reject_application(session: AsyncSession, captain: User, invitation_id: int) -> None:
    invitation = await _application_for_captain(session, captain, invitation_id, joins_user=False)
    invitation.status = InvitationStatus.DECLINED
    invitation.responded_at = utcnow()
    await session.commit()


async def cancel_invitation(session: AsyncSession, user: User, invitation_id: int) -> None:
    """Отозвать приглашение (капитан) или свою заявку (подавший её пользователь)"""
    invitation = await _lock_invitation(session, invitation_id)
    if invitation.kind == InvitationKind.APPLICATION:
        allowed = invitation.user_id == user.id
    else:
        team = await session.get(Team, invitation.team_id)
        allowed = team.captain_id == user.id
    if not allowed:
        raise Forbidden("You cannot cancel this invitation")
    _ensure_pending(invitation)
    invitation.status = InvitationStatus.CANCELLED
    invitation.responded_at = utcnow()
    await session.commit()

