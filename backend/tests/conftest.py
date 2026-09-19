import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sandhi.db")
os.environ.setdefault("PACE_SECONDS", "0")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "offline")
os.environ.setdefault("AGENT_TRANSPORT", "a2a")
os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="session", autouse=True)
def agent_server():
    """Runs the app on a real port so A2A calls travel over HTTP, as in production."""
    import uvicorn

    from app.main import app

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{PORT}"
    server.should_exit = True
    thread.join(timeout=5)