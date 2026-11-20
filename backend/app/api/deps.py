import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, Website

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
    return user


def owned_website(website_id: uuid.UUID, user: User, db: Session) -> Website:
    website = db.get(Website, website_id)
    if website is None or (website.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    return website


def user_filter(stmt, model, user: User):
    if user.role == "admin":
        return stmt
    return stmt.where(model.user_id == user.id)
