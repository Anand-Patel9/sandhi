"""Data access functions. All SQL lives here."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.models import Event
from .tables import EventRow, NegotiationRow

TERMINAL = {"agreed", "no_deal", "failed"}


def create_negotiation(db: Session, scenario_key: str, title: str, config: dict) -> NegotiationRow:
    row = NegotiationRow(scenario_key=scenario_key, title=title, config=config, status="pending")
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
    if status in TERMINAL:
        row.finished_at = datetime.now(timezone.utc)


def finish(db: Session, negotiation_id: str, status: str, outcome: dict, final_state: dict) -> None:
    row = db.get(NegotiationRow, negotiation_id)
    row.outcome = outcome
    row.final_state = final_state
    set_status(db, negotiation_id, status)


def next_seq(db: Session, negotiation_id: str) -> int:
    current = db.scalar(select(func.max(EventRow.seq)).where(EventRow.negotiation_id == negotiation_id))
    return (current or 0) + 1


def add_event(db: Session, negotiation_id: str, seq: int, event: Event) -> EventRow:
    data = event.to_dict()
    row = EventRow(negotiation_id=negotiation_id, seq=seq, kind=data["kind"], round=data["round"],
                   agent=data["agent"], message=data["message"], terms=data["terms"],
                   utilities=data["utilities"], meta=data["meta"])
    db.add(row)
    return row


def events_after(db: Session, negotiation_id: str, after_seq: int = 0) -> List[EventRow]:
    stmt = (select(EventRow).where(EventRow.negotiation_id == negotiation_id, EventRow.seq > after_seq)
            .order_by(EventRow.seq))
    return list(db.scalars(stmt))