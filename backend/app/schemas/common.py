import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    notify_email: bool | None = None
    theme: str | None = Field(default=None, pattern="^(system|light|dark)$")


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    notify_email: bool
    theme: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class WebsiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    url: str


class WebsiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)


class MonitoringUpdate(BaseModel):
    state: str = Field(pattern="^(active|paused|stopped)$")
    interval_seconds: int | None = Field(default=None, ge=300, le=86400)
    pagespeed_enabled: bool | None = None
    security_enabled: bool | None = None
    seo_enabled: bool | None = None


class WebsiteOut(ORMModel):
    id: uuid.UUID
    name: str
    url: str
    hostname: str
    monitoring_state: str
    latest_status: str
    latest_checked_at: datetime | None
    created_at: datetime
    interval_seconds: int | None = None


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    website_id: uuid.UUID | None = None


class AgentMetricIn(BaseModel):
    recorded_at: datetime | None = None
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_percent: float | None = Field(default=None, ge=0, le=100)
    disk_percent: float | None = Field(default=None, ge=0, le=100)
    network: dict[str, Any] = Field(default_factory=dict)
    processes: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    logs: list[str] = Field(default_factory=list, max_length=50)


class SimulationRequest(BaseModel):
    scenario: str
    website_name: str | None = None


class ReportRequest(BaseModel):
    website_id: uuid.UUID | None = None
    title: str | None = None
