"""Tamper-evident audit chain: each event's hash covers its content and the previous hash."""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Optional

GENESIS = "0" * 64


def event_hash(prev_hash: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def payload_of(seq: int, kind: str, round_no: int, agent: str, message: str, terms: Optional[dict],
               utilities: dict, meta: dict) -> dict:
    return {"seq": seq, "kind": kind, "round": round_no, "agent": agent, "message": message,
            "terms": terms, "utilities": utilities, "meta": meta}


def verify(rows: Iterable) -> dict:
    """Recompute the chain. Returns validity, length, head hash and the first broken sequence number."""
    prev, count = GENESIS, 0
    for row in rows:
        count += 1
        expected = event_hash(prev, payload_of(row.seq, row.kind, row.round, row.agent, row.message,
                                               row.terms, row.utilities or {}, row.meta or {}))
        if row.prev_hash != prev or row.hash != expected:
            return {"valid": False, "events": count, "head_hash": row.hash, "broken_at_seq": row.seq}
        prev = row.hash
    return {"valid": True, "events": count, "head_hash": prev, "broken_at_seq": None}