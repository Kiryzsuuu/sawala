"""Holds per-participant temporal detector state (liveness tracker, fatigue
tracker, oncam duration state), keyed by a stable slot key.

Two kinds of key are used depending on the frame source:
  - int tile index, from the screen-capture + tile-splitter pipeline
    (Skenario B), where gallery view tile order is generally stable
    within a session but real identity is unknown.
  - str participant name/id, from a source that already knows real
    participant identity (e.g. a Zoom Meeting SDK bot feeding named
    frames directly, bypassing screen capture and grid guessing).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from src.detection.fatigue_detector import FatigueTracker
from src.detection.liveness_detector import LivenessTracker
from src.detection.oncam_detector import OnCamState
from src.utils.config import CONFIG

SlotKey = Union[int, str]


@dataclass
class ParticipantSlot:
    participant_id: str
    name: str
    liveness: LivenessTracker
    fatigue: FatigueTracker
    oncam_state: OnCamState


class FrameBuffer:
    """Registry of ParticipantSlot, one per slot key."""

    def __init__(self):
        self._slots: dict[SlotKey, ParticipantSlot] = {}
        self._names: dict[SlotKey, str] = {}

    def set_name(self, key: SlotKey, name: str) -> None:
        self._names[key] = name

    def has_slot(self, key: SlotKey) -> bool:
        """True if this slot has already been confirmed as a real
        participant (a face was detected on it at least once)."""
        return key in self._slots

    def get_slot(self, key: SlotKey) -> ParticipantSlot:
        if key not in self._slots:
            if isinstance(key, str):
                default_name = key
                participant_id = key
            else:
                default_name = f"Participant {key + 1}"
                participant_id = f"P{key + 1:03d}"
            name = self._names.get(key, default_name)
            self._slots[key] = ParticipantSlot(
                participant_id=participant_id,
                name=name,
                liveness=LivenessTracker(),
                fatigue=FatigueTracker(
                    ear_threshold=CONFIG.thresholds.ear_fatigue,
                    consecutive_frames=CONFIG.thresholds.ear_fatigue_frames,
                    head_pitch_threshold_deg=CONFIG.thresholds.get("head_pitch_fatigue_deg", 20.0),
                    frame_interval_seconds=CONFIG.capture.interval_seconds,
                ),
                oncam_state=OnCamState(),
            )
        return self._slots[key]

    def active_slots(self) -> list[ParticipantSlot]:
        return list(self._slots.values())

    def reset(self) -> None:
        self._slots.clear()
