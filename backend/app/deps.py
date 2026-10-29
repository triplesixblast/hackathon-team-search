from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import SessionDep
from app.errors import Forbidden, Unauthorized
from app.models import Admin, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _payload(credentials: HTTPAuthorizationCredentials | None):
    payload = decode_access_token(credentials.credentials) if credentials else None
    if payload is None:
        raise Unauthorized("Invalid or expired token")
    return payload


async def current_user(
    session: SessionDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    payload = _payload(credentials)
    user = await session.get(User, payload.subject) if payload.role == "user" else None
    if user is None:
        raise Unauthorized("Invalid token or insufficient permissions")
    return user


async def current_admin(
    session: SessionDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> Admin:
    payload = _payload(credentials)
    if payload.role != "admin":
        raise Forbidden("Admin access required")
    admin = await session.get(Admin, payload.subject)
    if admin is None:
        raise Unauthorized("Admin not found")
    return admin


CurrentUser = Annotated[User, Depends(current_user)]
CurrentAdmin = Annotated[Admin, Depends(current_admin)]
