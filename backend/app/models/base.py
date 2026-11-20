import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as _PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class _UUIDPKType(TypeDecorator):  # type: ignore[misc]
    """Native UUID PK on PostgreSQL, VARCHAR(36) elsewhere (e.g. SQLite for tests)."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name != "postgresql" and isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                return value
        return value


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(_UUIDPKType(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )
