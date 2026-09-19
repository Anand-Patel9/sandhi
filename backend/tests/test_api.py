import time

from fastapi.testclient import TestClient

from app.main import app


def wait_until_done(client, nid, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/negotiations/{nid}").json()
        if body["status"] in ("agreed", "no_deal", "failed"):
            return body
        time.sleep(0.2)
    raise AssertionError("negotiation did not finish")


def test_full_lifecycle():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert len(client.get("/api/scenarios").json()) >= 2

        r = client.post("/api/negotiations", json={
            "scenario": "auto_parts", "pace_seconds": 0,
            "shocks": [{"key": "rate_hike", "at_round": 4}]})
        assert r.status_code == 201
        nid = r.json()["id"]

        done = wait_until_done(client, nid)
        assert done["status"] == "agreed"
        assert done["outcome"]["terms"]["days"] <= 45

        events = client.get(f"/api/negotiations/{nid}/events").json()
        assert events[0]["seq"] == 1 and events[-1]["kind"] == "deal"

        with client.stream("GET", f"/api/negotiations/{nid}/stream") as s:
            text = "".join(s.iter_text())
        assert "event: deal" in text and "event: end" in text

        assert done["outcome"]["transport"] == "a2a"
        assert events[0]["message"].startswith("Connected over A2A")

        ev = client.get(f"/api/negotiations/{nid}/evaluation").json()
        assert ev["pareto_efficient"] and len(ev["approaches"]) == 6

        agents = client.get("/api/agents").json()
        assert {a["role"] for a in agents} == {"supplier", "buyer", "financier"}
        assert client.get("/", follow_redirects=False).headers["location"] == "/docs"


def test_validation_rejects_unknown_shock():
    with TestClient(app) as client:
        r = client.post("/api/negotiations", json={"scenario": "auto_parts",
                                                   "shocks": [{"key": "alien_invasion", "at_round": 2}]})
        assert r.status_code == 422