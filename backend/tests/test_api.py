import time

from fastapi.testclient import TestClient

from app.db.session import session_scope
from app.db.tables import EventRow
from app.main import app

PASSWORD = "sandhi-demo"


def login(client, who):
    r = client.post("/api/auth/login", json={"email": f"{who}@sandhi.demo", "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait_until(client, nid, headers, states=("agreed", "no_deal", "failed", "awaiting_approval"), timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/negotiations/{nid}", headers=headers).json()
        if body["status"] in states:
            return body
        time.sleep(0.2)
    raise AssertionError("negotiation did not finish")


def start(client, headers, **extra):
    body = {"scenario": "auto_parts", "pace_seconds": 0, "shocks": [{"key": "rate_hike", "at_round": 4}], **extra}
    r = client.post("/api/negotiations", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_requires_authentication():
    with TestClient(app) as client:
        assert client.get("/api/negotiations").status_code == 401
        assert client.post("/api/auth/login", json={"email": "buyer@sandhi.demo", "password": "x"}).status_code == 401
        assert client.get("/api/health").status_code == 200


def test_full_lifecycle_with_human_approval():
    with TestClient(app) as client:
        admin = login(client, "admin")
        me = client.get("/api/auth/me", headers=admin).json()
        assert me["org"]["kind"] == "platform"

        nid = start(client, admin)
        done = wait_until(client, nid, admin)
        assert done["status"] == "awaiting_approval"
        assert done["outcome"]["transport"] == "a2a"
        assert done["outcome"]["compliance"]["msmed_compliant"]
        assert set(done["outcome"]["required_approvals"]) == {"supplier", "buyer", "financier"}
        assert client.get(f"/api/negotiations/{nid}/term-sheet", headers=admin).status_code == 409

        events = client.get(f"/api/negotiations/{nid}/events", headers=admin).json()
        assert events[0]["message"].startswith("Connected over A2A")
        assert events[1]["message"].startswith("Live data loaded over MCP")
        assert events[-1]["kind"] == "approval_required"

        supplier, buyer, financier = (login(client, w) for w in ("supplier", "buyer", "financier"))
        assert client.post(f"/api/negotiations/{nid}/approval", headers=supplier,
                           json={"decision": "approve", "role": "buyer"}).status_code == 403
        for headers in (supplier, buyer):
            r = client.post(f"/api/negotiations/{nid}/approval", headers=headers, json={"decision": "approve"})
            assert r.status_code == 200 and r.json()["status"] == "awaiting_approval"
        assert client.post(f"/api/negotiations/{nid}/approval", headers=buyer,
                           json={"decision": "approve"}).status_code == 409
        final = client.post(f"/api/negotiations/{nid}/approval", headers=financier,
                            json={"decision": "approve", "note": "Limit available"}).json()
        assert final["status"] == "agreed" and len(final["approvals"]) == 3

        pdf = client.get(f"/api/negotiations/{nid}/term-sheet", headers=buyer)
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

        audit = client.get(f"/api/negotiations/{nid}/audit", headers=buyer).json()
        assert audit["valid"] and audit["events"] == len(events) + 4

        with client.stream("GET", f"/api/negotiations/{nid}/stream?token={buyer['Authorization'][7:]}") as s:
            text = "".join(s.iter_text())
        assert "event: signed" in text and "event: end" in text

        ev = client.get(f"/api/negotiations/{nid}/evaluation", headers=buyer).json()
        assert ev["pareto_efficient"] and len(ev["approaches"]) == 6
        assert {a["role"] for a in client.get("/api/agents").json()} == {"supplier", "buyer", "financier"}
        assert len(client.get("/api/tools").json()) == 3
        assert client.get("/", follow_redirects=False).headers["location"] == "/docs"


def test_rejection_and_tamper_detection():
    with TestClient(app) as client:
        admin = login(client, "admin")
        nid = start(client, admin)
        wait_until(client, nid, admin)
        r = client.post(f"/api/negotiations/{nid}/approval", headers=admin,
                        json={"decision": "reject", "role": "buyer", "note": "Board review pending"})
        assert r.json()["status"] == "rejected"

        with session_scope() as db:
            row = db.query(EventRow).filter_by(negotiation_id=nid, seq=5).one()
            row.message = row.message + " (edited)"
        audit = client.get(f"/api/negotiations/{nid}/audit", headers=admin).json()
        assert not audit["valid"] and audit["broken_at_seq"] == 5


def test_approval_can_be_skipped_for_automation():
    with TestClient(app) as client:
        admin = login(client, "admin")
        nid = start(client, admin, require_approval=False)
        assert wait_until(client, nid, admin)["status"] == "agreed"


def test_validation_rejects_unknown_shock():
    with TestClient(app) as client:
        r = client.post("/api/negotiations", headers=login(client, "admin"),
                        json={"scenario": "auto_parts", "shocks": [{"key": "alien_invasion", "at_round": 2}]})
        assert r.status_code == 422


def test_running_negotiation_can_be_stopped():
    with TestClient(app) as client:
        admin = login(client, "admin")
        nid = start(client, admin, pace_seconds=0.3)
        time.sleep(1.0)
        assert client.post(f"/api/negotiations/{nid}/cancel", headers=admin).status_code == 200
        done = wait_until(client, nid, admin, states=("cancelled", "agreed", "awaiting_approval"))
        assert done["status"] == "cancelled"
        events = client.get(f"/api/negotiations/{nid}/events", headers=admin).json()
        assert events[-1]["kind"] == "cancelled"
        assert client.post(f"/api/negotiations/{nid}/cancel", headers=admin).status_code == 409