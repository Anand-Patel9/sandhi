"""FastAPI dependencies that resolve the signed-in user."""
from __future__ import annotations

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..db import repository as repo
from ..db.session import get_db
from ..db.tables import UserRow
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def current_user(header_token: Optional[str] = Depends(oauth2),
                 token: Optional[str] = Query(None, description="Access token (for EventSource streams)"),
                 db: Session = Depends(get_db)) -> UserRow:
    raw = header_token or token
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                                 headers={"WWW-Authenticate": "Bearer"})
    if not raw:
        raise unauthorized
    try:
        claims = decode_token(raw)
    except jwt.PyJWTError:
        raise unauthorized
    user = repo.get_user(db, claims.get("sub", ""))
    if user is None or not user.active:
        raise unauthorized
    return user