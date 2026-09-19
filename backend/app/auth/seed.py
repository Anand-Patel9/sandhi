"""Demo organisations and users for the sandbox."""
from __future__ import annotations

from ..config import get_settings
from ..db import repository as repo
from ..db.session import session_scope
from .security import hash_password

DEMO = [
    ("Rajkot Castings Pvt Ltd", "supplier", "supplier@sandhi.demo", "Supplier user"),
    ("Bharat Motors Ltd", "buyer", "buyer@sandhi.demo", "Buyer user"),
    ("Trident TReDS Bank", "financier", "financier@sandhi.demo", "Financier user"),
    ("Sandhi Platform", "platform", "admin@sandhi.demo", "Platform admin"),
]


def seed_demo_users() -> None:
    settings = get_settings()
    if not settings.seed_demo_users:
        return
    with session_scope() as db:
        for org_name, kind, email, name in DEMO:
            if repo.get_user_by_email(db, email):
                continue
            org = repo.get_or_create_org(db, org_name, kind)
            repo.create_user(db, email=email, name=name, org_id=org.id,
                             password_hash=hash_password(settings.demo_password))