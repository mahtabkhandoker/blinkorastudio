"""SQLAlchemy models for the P0.5 persistent store.

Two groups of tables:

* **Auth** (`User`, `AuthSession`, `IdentityLink`): real relational rows —
  this is the authorization boundary and must stay simple to audit.
* **Orders** (`OrderRecord`, `OrderSequence`): the order aggregate is kept
  as one JSONB document per order (`OrderRecord.data`, a serialized
  `app.models.orders.Order`). `owner_user_id`, `number`, `channel` and
  `status` are promoted to real columns because every authorization check
  and the "my orders" listing filter on them; the nested answers/plan/
  generation/feedback stay inside the JSON, which is what the task brief
  calls out as fine ("typed columns or JSONB where appropriate") and avoids
  rewriting the P0 business logic in `services/orders/*`, which operates on
  the `Order` Pydantic model in memory.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('customer', 'operator')", name="ck_users_role"),
        CheckConstraint("status in ('active', 'disabled')", name="ck_users_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Stored lowercased; uniqueness is enforced on the normalized value so
    # "a@x.com" and "A@x.com" cannot register as two different accounts.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Never settable by a client request; defaults every self-service
    # registration to "customer". Nothing in the API can promote a user.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    identity_links: Mapped[list["IdentityLink"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    """A logged-in session. The cookie carries a random token; only its
    SHA-256 hash is stored, so a leaked database dump cannot be replayed
    as a live session cookie."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class IdentityLink(Base):
    """Future-proofing for WhatsApp (not wired up yet): a verified link
    from one account to a second channel identity. A phone number alone
    never grants access — a row here only exists once that channel's
    ownership was proven (e.g. an OTP sent to that WhatsApp number),
    recorded in `verified_at`. No code currently creates whatsapp rows;
    this only reserves the schema per the P0.5 brief."""

    __tablename__ = "identity_links"
    __table_args__ = (UniqueConstraint("channel", "external_ref", name="uq_identity_links_channel_ref"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # "web" | "whatsapp"
    external_ref: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g. a phone number
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="identity_links")


class OrderRecord(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_owner_updated", "owner_user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="web")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", index=True)
    # Full `Order` model dump (answers, plan, assets metadata, generation,
    # feedback, events) — see module docstring for why this stays JSONB.
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrderSequence(Base):
    """Single-row counter for human-readable order numbers (`ORD-000142`).
    Incremented under `SELECT ... FOR UPDATE` so concurrent workers never
    hand out the same number (the old JSON-file repo's counter file was
    single-process only)."""

    __tablename__ = "order_sequence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
