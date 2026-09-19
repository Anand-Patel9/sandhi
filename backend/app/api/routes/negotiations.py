"""Negotiation lifecycle: create, read, live stream, approval, audit, evaluation and term sheet."""
from __future__ import annotations

import asyncio
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from ...auth.deps import current_user
from ...core import audit, metrics
from ...core.models import Scenario, Terms
from ...core.scenarios import SCENARIOS
from ...db import repository as repo
from ...db.session import get_db, session_scope
from ...db.tables import UserRow
from ...documents.term_sheet import build_term_sheet
from ...orchestrator import approvals, runner
from ..schemas import (ApprovalIn, AuditOut, EvaluationOut, EventOut, NegotiationCreate,
                       NegotiationOut)

router = APIRouter(prefix="/negotiations", tags=["negotiations"], dependencies=[Depends(current_user)])
POLL_SECONDS = 0.3
EVALUABLE = {"agreed", "no_deal", "awaiting_approval", "rejected"}


def _get_or_404(db: Session, negotiation_id: str):
    row = repo.get_negotiation(db, negotiation_id)
    if row is None:
        raise HTTPException(404, "Negotiation not found")
    return row


@router.post("", response_model=NegotiationOut, status_code=201)
def create_negotiation(body: NegotiationCreate, db: Session = Depends(get_db),
                       user: UserRow = Depends(current_user)):
    config = body.model_dump(exclude_none=True)
    row = repo.create_negotiation(db, body.scenario, SCENARIOS[body.scenario].title, config, user.id)
    db.commit()
    runner.submit(row.id)
    return row


@router.get("", response_model=List[NegotiationOut])
def list_negotiations(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_db)):
    return repo.list_negotiations(db, limit, offset)


@router.get("/{negotiation_id}", response_model=NegotiationOut)
def get_negotiation(negotiation_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, negotiation_id)


@router.get("/{negotiation_id}/events", response_model=List[EventOut])
def get_events(negotiation_id: str, after: int = Query(0, ge=0), db: Session = Depends(get_db)):
    _get_or_404(db, negotiation_id)
    return repo.events_after(db, negotiation_id, after)


@router.get("/{negotiation_id}/stream")
async def stream_events(negotiation_id: str, request: Request, after: int = Query(0, ge=0)):
    """Server-Sent Events: replays stored events, then follows the live negotiation."""
    with session_scope() as db:
        _get_or_404(db, negotiation_id)

    async def event_source():
        last = after
        while True:
            if await request.is_disconnected():
                break
            with session_scope() as db:
                rows = repo.events_after(db, negotiation_id, last)
                status = repo.get_negotiation(db, negotiation_id).status
                payloads = [EventOut.model_validate(r).model_dump(mode="json") for r in rows]
            for p in payloads:
                last = p["seq"]
                yield f"id: {p['seq']}\nevent: {p['kind']}\ndata: {json.dumps(p)}\n\n"
            if status in repo.STREAM_END and not payloads:
                yield f"event: end\ndata: {json.dumps({'status': status})}\n\n"
                break
            await asyncio.sleep(POLL_SECONDS)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(event_source(), media_type="text/event-stream", headers=headers)


@router.post("/{negotiation_id}/approval", response_model=NegotiationOut)
def decide(negotiation_id: str, body: ApprovalIn, db: Session = Depends(get_db),
           user: UserRow = Depends(current_user)):
    row = _get_or_404(db, negotiation_id)
    try:
        return approvals.decide(db, row, user, body.decision, body.role, body.note)
    except approvals.ApprovalError as err:
        raise HTTPException(err.status_code, err.detail)


@router.get("/{negotiation_id}/audit", response_model=AuditOut)
def verify_audit(negotiation_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, negotiation_id)
    return AuditOut(negotiation_id=negotiation_id, **audit.verify(repo.events_after(db, negotiation_id)))


@router.get("/{negotiation_id}/evaluation", response_model=EvaluationOut)
def get_evaluation(negotiation_id: str, db: Session = Depends(get_db)):
    row = _get_or_404(db, negotiation_id)
    if row.status not in EVALUABLE:
        raise HTTPException(409, f"Evaluation is available once agents finish (status: {row.status})")
    if not row.final_state:
        raise HTTPException(403, "Evaluation requires sandbox mode")
    sc = Scenario.from_dict(row.final_state)
    terms = Terms.from_dict((row.outcome or {}).get("terms"))
    return EvaluationOut(negotiation_id=row.id, deal_zone=metrics.deal_zone(sc), **metrics.summary(sc, terms))


@router.get("/{negotiation_id}/term-sheet", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def term_sheet(negotiation_id: str, db: Session = Depends(get_db)):
    row = _get_or_404(db, negotiation_id)
    if row.status != "agreed":
        raise HTTPException(409, f"A term sheet is issued once all parties approve (status: {row.status})")
    pdf = build_term_sheet(row, audit.verify(repo.events_after(db, negotiation_id)))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="sandhi-term-sheet-{row.id[:8]}.pdf"'})