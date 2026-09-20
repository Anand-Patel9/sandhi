"""Data access functions. All SQL lives here."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import GENESIS, event_hash, payload_of
from ..core.models import Event
from .tables import ApprovalRow, EventRow, NegotiationRow, OrganizationRow, UserRow

TERMINAL = {"agreed", "no_deal", "failed", "rejected", "cancelled"}
STREAM_END = TERMINAL | {"awaiting_approval"}


# --- organisations and users ---
def get_or_create_org(db: Session, name: str, kind: str) -> OrganizationRow:
    org = db.scalar(select(OrganizationRow).where(OrganizationRow.name == name))
    if org is None:
        org = OrganizationRow(name=name, kind=kind)
        db.add(org)
        db.flush()
    return org


def create_user(db: Session, email: str, name: str, org_id: str, password_hash: str) -> UserRow:
    user = UserRow(email=email.lower(), name=name, org_id=org_id, password_hash=password_hash)
    db.add(user)
    db.flush()
    return user


def get_user(db: Session, user_id: str) -> Optional[UserRow]:
    return db.get(UserRow, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[UserRow]:
    return db.scalar(select(UserRow).where(UserRow.email == email.lower()))


# --- negotiations ---
def create_negotiation(db: Session, scenario_key: str, title: str, config: dict,
                       created_by: Optional[str] = None) -> NegotiationRow:
    row = NegotiationRow(scenario_key=scenario_key, title=title, config=config, status="pending",
                         created_by=created_by)
    db.add(row)
    db.flush()
    return row


def get_negotiation(db: Session, negotiation_id: str) -> Optional[NegotiationRow]:
    return db.get(NegotiationRow, negotiation_id)


def list_negotiations(db: Session, limit: int = 50, offset: int = 0) -> List[NegotiationRow]:
    stmt = select(NegotiationRow).order_by(NegotiationRow.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def set_status(db: Session, negotiation_id: str, status: str, error: Optional[str] = None) -> None:
    row = db.get(NegotiationRow, negotiation_id)
    row.status = status
    row.error = error
    if status in TERMINAL or status == "awaiting_approval":
        row.finished_at = datetime.now(timezone.utc)


def finish(db: Session, negotiation_id: str, status: str, outcome: dict, final_state: dict) -> None:
    row = db.get(NegotiationRow, negotiation_id)
    row.outcome = outcome
    row.final_state = final_state
    set_status(db, negotiation_id, status)


# --- events (hash-chained) ---
def last_event(db: Session, negotiation_id: str) -> Optional[EventRow]:
    stmt = (select(EventRow).where(EventRow.negotiation_id == negotiation_id)
            .order_by(EventRow.seq.desc()).limit(1))
    return db.scalar(stmt)


def append_event(db: Session, negotiation_id: str, event: Event) -> EventRow:
    last = last_event(db, negotiation_id)
    seq = (last.seq if last else 0) + 1
    prev = last.hash if last else GENESIS
    data = event.to_dict()
    digest = event_hash(prev, payload_of(seq, data["kind"], data["round"], data["agent"], data["message"],
                                         data["terms"], data["utilities"], data["meta"]))
    row = EventRow(negotiation_id=negotiation_id, seq=seq, kind=data["kind"], round=data["round"],
                   agent=data["agent"], message=data["message"], terms=data["terms"],
                   utilities=data["utilities"], meta=data["meta"], prev_hash=prev, hash=digest)
    db.add(row)
    db.flush()
    return row


def events_after(db: Session, negotiation_id: str, after_seq: int = 0) -> List[EventRow]:
    stmt = (select(EventRow).where(EventRow.negotiation_id == negotiation_id, EventRow.seq > after_seq)
            .order_by(EventRow.seq))
    return list(db.scalars(stmt))


# --- approvals ---
def add_approval(db: Session, negotiation_id: str, role: str, decision: str, user: UserRow,
                 note: str = "") -> ApprovalRow:
    row = ApprovalRow(negotiation_id=negotiation_id, role=role, decision=decision, note=note,
                      user_id=user.id, user_email=user.email)
    db.add(row)
    db.flush()
    return row