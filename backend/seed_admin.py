#!/usr/bin/env python3
"""Bootstrap the first admin user.

Usage:
    cd backend
    python seed_admin.py

Reads ADMIN_EMAIL and ADMIN_PASSWORD from the environment (or .env file).
Does nothing if the account already exists.
"""
from __future__ import annotations

import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User
from sqlalchemy import select


def main() -> None:
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be set in the environment or .env file.")
        sys.exit(1)
    db = SessionLocal()
    try:
        existing = db.scalars(select(User).where(User.email == settings.admin_email.lower())).first()
        if existing:
            print(f"User {settings.admin_email} already exists (role={existing.role}). Nothing to do.")
            return
        user = User(
            email=settings.admin_email.lower(),
            password_hash=hash_password(settings.admin_password),
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {settings.admin_email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
