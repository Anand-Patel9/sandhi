"""Human approval: agents agree on terms, authorised people sign them off."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from ..core.models import Event, Terms
from ..db import repository as repo
from ..db.tables import NegotiationRow, UserRow


class ApprovalError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def required_roles(terms: Optional[Terms]) -> List[str]:
    roles = ["supplier", "buyer"]
    if terms is not None and terms.treds:
        roles.append("financier")
    return roles


def request_event(roles: List[str]) -> Event:
    return Event("approval_required", 0, "system",
                 "Agents reached agreement. Awaiting sign-off from: " + ", ".join(roles) + ".",
                 meta={"required": roles})


def decide(db: Session, row: NegotiationRow, user: UserRow, decision: str,
           role: Optional[str] = None, note: str = "") -> NegotiationRow:
    if row.status != "awaiting_approval":
        raise ApprovalError(409, f"Negotiation is not awaiting approval (status: {row.status})")
    required = (row.outcome or {}).get("required_approvals", [])
    kind = user.org.kind
    if kind == "platform":
        if role is None:
            raise ApprovalError(422, "Platform admins must specify which party they approve for")
    elif role is not None and role != kind:
        raise ApprovalError(403, f"A {kind} user cannot sign for the {role}")
    role = role or kind
    if role not in required:
        raise ApprovalError(403, f"The {role} is not a signing party for this deal")
    if any(a.role == role for a in row.approvals):
        raise ApprovalError(409, f"The {role} has already decided")

    repo.add_approval(db, row.id, role, decision, user, note)
    verb = "approved" if decision == "approve" else "rejected"
    repo.append_event(db, row.id, Event("approval", 0, role,
                                        f"{user.org.name} {verb} the terms ({user.email}).",
                                        meta={"decision": decision, "user": user.email, "note": note}))
    db.refresh(row)

    if decision == "reject":
        repo.set_status(db, row.id, "rejected")
        repo.append_event(db, row.id, Event("rejected", 0, "system",
                                            f"Deal rejected by the {role}. Terms are not binding."))
    elif all(any(a.role == r and a.decision == "approve" for a in row.approvals) for r in required):
        repo.set_status(db, row.id, "agreed")
        repo.append_event(db, row.id, Event("signed", 0, "system",
                                            "All parties approved. The agreement is final."))
    db.refresh(row)
    return row