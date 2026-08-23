"""Pydantic data models used across the API and engine layers."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ParticipantStatus(BaseModel):
    id: str
    name: str
    oncam: bool = False
    oncam_duration_seconds: float = 0.0
    is_real_person: Optional[bool] = None
    liveness_score: Optional[float] = None
    avatar_flag: bool = False
    holding_phone: bool = False
    phone_confidence: float = 0.0
    fatigue_detected: bool = False
    ear_value: Optional[float] = None
    head_pitch_angle: Optional[float] = None
    fatigue_duration_seconds: float = 0.0
    smiling: bool = False
    smile_confidence: float = 0.0
    dominant_emotion: str = "unknown"
    last_seen: Optional[str] = None
    flags: list[str] = Field(default_factory=list)


class SessionInfo(BaseModel):
    session_id: str
    started_at: str
    active: bool
    participant_count: int


class LiveUpdatePayload(BaseModel):
    timestamp: str
    participants: list[ParticipantStatus]
