"""Mode state machine and voice-command mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Mode(str, Enum):
    BOT_DRIVES = "bot_drives"
    HUMAN_DRIVES = "human_drives"


BOT_SWITCH_PHRASES = (
    "take over",
    "you drive",
    "bot drives",
    "your turn",
)

HUMAN_SWITCH_PHRASES = (
    "let me try",
    "i'll drive",
    "my turn",
    "i will drive",
)


def normalize_utterance(text: str) -> str:
    return " ".join(text.lower().strip().replace("-", " ").split())


def detect_mode_command(utterance: str) -> Optional[Mode]:
    normalized = normalize_utterance(utterance)
    for phrase in BOT_SWITCH_PHRASES:
        if phrase in normalized:
            return Mode.BOT_DRIVES
    for phrase in HUMAN_SWITCH_PHRASES:
        if phrase in normalized:
            return Mode.HUMAN_DRIVES
    return None


@dataclass(frozen=True)
class ModeTransition:
    previous: Mode
    current: Mode
    trigger: str


class ModeStateMachine:
    """Tiny deterministic state machine for bot/human driving mode."""

    def __init__(self, initial_mode: Mode = Mode.BOT_DRIVES) -> None:
        self._mode = initial_mode

    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode, trigger: str = "manual") -> Optional[ModeTransition]:
        if mode == self._mode:
            return None
        previous = self._mode
        self._mode = mode
        return ModeTransition(previous=previous, current=mode, trigger=trigger)

    def apply_voice_command(self, utterance: str) -> Optional[ModeTransition]:
        target_mode = detect_mode_command(utterance)
        if target_mode is None:
            return None
        return self.set_mode(target_mode, trigger=utterance)

