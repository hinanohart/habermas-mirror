"""Pydantic request/response models for the public API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionIn(BaseModel):
    topic: str = Field(min_length=1, max_length=512)


class OpinionIn(BaseModel):
    author: str = Field(min_length=1, max_length=128)
    body: str = Field(min_length=1, max_length=4000)


class OpinionOut(BaseModel):
    id: int
    session_id: str
    author: str
    body: str
    created_at: datetime


class StatementOut(BaseModel):
    id: int
    session_id: str
    stage: str
    body: str
    provider: str
    created_at: datetime


class SessionOut(BaseModel):
    id: str
    topic: str
    created_at: datetime
    opinions: list[OpinionOut] = []
    statements: list[StatementOut] = []
