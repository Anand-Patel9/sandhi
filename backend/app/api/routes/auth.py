"""Sign-in and current-user endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...auth.deps import current_user
from ...auth.security import create_token, verify_password
from ...db import repository as repo
from ...db.session import get_db
from ...db.tables import UserRow
from ..schemas import LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue(db: Session, email: str, password: str) -> TokenOut:
    user = repo.get_user_by_email(db, email)
    if user is None or not user.active or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenOut(access_token=create_token(user.id, user.org.kind), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    return _issue(db, body.email, body.password)


@router.post("/token", response_model=TokenOut, include_in_schema=False)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return _issue(db, form.username, form.password)


@router.get("/me", response_model=UserOut)
def me(user: UserRow = Depends(current_user)):
    return user