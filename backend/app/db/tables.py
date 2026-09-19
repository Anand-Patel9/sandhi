"""Database tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    org: Mapped[OrganizationRow] = relationship(lazy="joined")


class NegotiationRow(Base):
    __tablename__ = "negotiations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scenario_key: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), index=True, default="pending")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["EventRow"]] = relationship(back_populates="negotiation",
                                                    cascade="all, delete-orphan",
                                                    order_by="EventRow.seq")
    approvals: Mapped[list["ApprovalRow"]] = relationship(cascade="all, delete-orphan", lazy="selectin",
                                                          order_by="ApprovalRow.id")


class EventRow(Base):
    __tablename__ = "negotiation_events"
    __table_args__ = (UniqueConstraint("negotiation_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    round: Mapped[int] = mapped_column(Integer)
    agent: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text, default="")
    terms: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    utilities: Mapped[dict] = mapped_column(JSON, default=dict)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    negotiation: Mapped[NegotiationRow] = relationship(back_populates="events")


class ApprovalRow(Base):
    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("negotiation_id", "role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    negotiation_id: Mapped[str] = mapped_column(ForeignKey("negotiations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str] = mapped_column(String(10))
    note: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    user_email: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)