import enum
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class HackathonStatus(enum.StrEnum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    FINISHED = "finished"


class TeamStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class InvitationKind(enum.StrEnum):
    INVITE = "invite"            # капитан приглашает пользователя
    APPLICATION = "application"  # пользователь подаёт заявку капитану


class InvitationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Строковый enum (VARCHAR + CHECK): добавлять значения проще, чем в нативном ENUM"""
    return Enum(
        enum_cls, name=name, native_enum=False, create_constraint=True, length=20,
        values_callable=lambda e: [m.value for m in e],
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


def _updated_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=list, server_default=text("'{}'::varchar[]")
    )
    role_preference: Mapped[str | None] = mapped_column(String(50))
    experience_level: Mapped[str] = mapped_column(String(50), default="junior", server_default="junior")
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created_at()


class AuthCode(Base):
    """Одноразовый код входа, выданный ботом"""

    __tablename__ = "auth_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(6))
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    used: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        # среди неиспользованных кодов значение уникально: по коду однозначно находим запись
        Index("uq_auth_codes_active_code", "code", unique=True, postgresql_where=text("NOT used")),
    )


class Hackathon(Base):
    __tablename__ = "hackathons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[HackathonStatus] = mapped_column(
        _enum(HackathonStatus, "hackathon_status"),
        default=HackathonStatus.UPCOMING, server_default=HackathonStatus.UPCOMING.value,
    )
    max_team_size: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    __table_args__ = (
        CheckConstraint("max_team_size BETWEEN 1 AND 100", name="max_team_size_range"),
        CheckConstraint("end_date > start_date", name="dates_order"),
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id", ondelete="CASCADE"), index=True)
    captain_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TeamStatus] = mapped_column(
        _enum(TeamStatus, "team_status"), default=TeamStatus.OPEN, server_default=TeamStatus.OPEN.value
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    hackathon: Mapped[Hackathon] = relationship(lazy="raise")
    captain: Mapped[User] = relationship(lazy="raise")
    # Члены команды = регистрации с team_id этой команды
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="team",
        lazy="raise",
        passive_deletes=True,
        order_by="Registration.joined_team_at, Registration.id",
    )

    __table_args__ = (
        # у пользователя не больше одной собственной команды на хакатон (в т.ч. при гонках)
        UniqueConstraint("hackathon_id", "captain_id"),
    )


class Registration(Base):
    """Участие пользователя в хакатоне и его текущая команда"""

    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hackathon_id: Mapped[int] = mapped_column(ForeignKey("hackathons.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    joined_team_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    user: Mapped[User] = relationship(lazy="raise")
    hackathon: Mapped[Hackathon] = relationship(lazy="raise")
    team: Mapped[Team | None] = relationship(back_populates="registrations", lazy="raise")

    __table_args__ = (
        UniqueConstraint("user_id", "hackathon_id"),
    )


class Invitation(Base):
    """
    Приглашение капитана (kind=invite, отвечает user) или заявка пользователя
    (kind=application, отвечает капитан). sent_by — инициатор.
    """

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sent_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[InvitationKind] = mapped_column(_enum(InvitationKind, "invitation_kind"))
    status: Mapped[InvitationStatus] = mapped_column(
        _enum(InvitationStatus, "invitation_status"),
        default=InvitationStatus.PENDING, server_default=InvitationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = _created_at()
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    team: Mapped[Team] = relationship(lazy="raise")
    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="raise")
    sent_by: Mapped[User] = relationship(foreign_keys=[sent_by_id], lazy="raise")

    __table_args__ = (
        # одно ожидающее приглашение/заявка на пару (команда, пользователь)
        Index(
            "uq_invitations_pending", "team_id", "user_id", unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )
