from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, hash_token, new_token, verify_password
from app.models import RefreshToken, User
from app.schemas.common import RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _issue(db: Session, user: User) -> TokenPair:
    raw = new_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, user.role), refresh_token=raw, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    existing = db.scalars(select(User).where(User.email == body.email.lower())).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), full_name=body.full_name.strip(), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue(db, user)


@router.post("/login", response_model=TokenPair)
def login(body: UserLogin, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalars(select(User).where(User.email == body.email.lower())).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled")
    return _issue(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token))).first()
    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    # Compare naively if the stored value lost timezone info (SQLite in tests)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    row.revoked_at = now
    replacement = new_token()
    new_row = RefreshToken(user_id=user.id, token_hash=hash_token(replacement), expires_at=now + timedelta(days=settings.refresh_token_days))
    db.add(new_row)
    db.flush()
    row.replaced_by_id = new_row.id
    db.commit()
    return TokenPair(access_token=create_access_token(user.id, user.role), refresh_token=replacement, user=UserOut.model_validate(user))


@router.post("/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token))).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.commit()
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.notify_email is not None:
        user.notify_email = body.notify_email
    if body.theme is not None:
        user.theme = body.theme
    db.commit()
    db.refresh(user)
    return user
