from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models import HackathonStatus, InvitationKind, InvitationStatus, TeamStatus


def _as_utc(value: datetime) -> datetime:
    """Naive-даты от клиента считаем UTC, aware приводим к UTC"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(max_length=5000)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ───────── auth ─────────

class GenerateCodeRequest(BaseModel):
    telegram_id: int = Field(gt=0)
    telegram_username: Annotated[str, Field(max_length=64)] | None = None


class VerifyCodeRequest(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=16)]


class AdminLoginRequest(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=256)]


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int


# ───────── users ─────────

class PublicUser(ORM):
    """Профиль, видимый другим пользователям (без telegram_id)"""
    id: int
    telegram_username: str | None
    full_name: str
    bio: str | None
    skills: list[str]
    role_preference: str | None
    experience_level: str
    avatar_url: str | None
    created_at: datetime


class UserProfile(PublicUser):
    """Собственный профиль"""
    telegram_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserUpdate(BaseModel):
    full_name: Name | None = None
    bio: LongText | None = None
    skills: Annotated[list[Annotated[str, Field(min_length=1, max_length=50)]], Field(max_length=30)] | None = None
    role_preference: Annotated[str, Field(max_length=50)] | None = None
    experience_level: Annotated[str, Field(max_length=50)] | None = None
    avatar_url: Annotated[str, Field(max_length=500, pattern=r"^https?://")] | None = None


class UserListItem(ORM):
    id: int
    full_name: str
    skills: list[str]
    role_preference: str | None
    experience_level: str
    avatar_url: str | None


# ───────── hackathons ─────────

class HackathonCreate(BaseModel):
    name: Name
    description: LongText | None = None
    start_date: UtcDatetime
    end_date: UtcDatetime
    max_team_size: int = Field(default=5, ge=1, le=100)

    @model_validator(mode="after")
    def _check_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be later than start_date")
        return self


class HackathonUpdate(BaseModel):
    name: Name | None = None
    description: LongText | None = None
    start_date: UtcDatetime | None = None
    end_date: UtcDatetime | None = None
    status: HackathonStatus | None = None
    max_team_size: int | None = Field(default=None, ge=1, le=100)


class HackathonOut(ORM):
    id: int
    name: str
    description: str | None
    start_date: datetime
    end_date: datetime
    status: HackathonStatus
    max_team_size: int
    created_at: datetime


class HackathonDetail(HackathonOut):
    is_registered: bool
    team_id: int | None


# ───────── teams ─────────

class TeamCreate(BaseModel):
    hackathon_id: int
    name: Name
    description: LongText | None = None


class TeamUpdate(BaseModel):
    name: Name | None = None
    description: LongText | None = None
    status: TeamStatus | None = None


class TeamMemberOut(BaseModel):
    id: int
    full_name: str
    role_preference: str | None
    skills: list[str]


class TeamOut(BaseModel):
    id: int
    hackathon_id: int
    name: str
    description: str | None
    captain_id: int
    status: TeamStatus
    created_at: datetime
    members: list[TeamMemberOut]
    max_team_size: int


class TeamDetail(TeamOut):
    captain: PublicUser
    hackathon: HackathonOut


class MyTeamItem(BaseModel):
    id: int
    name: str
    description: str | None
    hackathon_id: int
    hackathon_name: str
    status: TeamStatus


class CanCreateTeam(BaseModel):
    can_create: bool
    reason: str | None = None


# ───────── invitations ─────────

class InvitationOut(BaseModel):
    id: int
    team_id: int
    user_id: int
    sent_by_id: int
    kind: InvitationKind
    status: InvitationStatus
    created_at: datetime
    responded_at: datetime | None
    team: TeamOut | None = None
    sent_by: PublicUser | None = None
    user: PublicUser | None = None  # приглашённый / подавший заявку


class InvitationReply(BaseModel):
    accept: bool = True


# ───────── admin ─────────

class HackathonAnalytics(BaseModel):
    total_participants: int
    total_teams: int
    participants_without_team: int
    participants_in_team: int
    average_team_size: float
    skills_frequency: dict[str, int]
    experience_distribution: dict[str, int]


class AssignUserRequest(BaseModel):
    user_id: int
    team_id: int | None = None  # None — убрать из команды


Status = Literal["ok"]
