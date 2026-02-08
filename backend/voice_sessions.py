from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .config import QUESTIONS_ROOT, REPO_ROOT

SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pair_programming_voice_bot.agent import PairProgrammingVoiceBot
from pair_programming_voice_bot.modes import Mode
from pair_programming_voice_bot.workspace import QuestionWorkspace


@dataclass
class VoiceSession:
    session_id: str
    question_name: str
    bot: PairProgrammingVoiceBot
    conversation_history: List[Dict] = field(default_factory=list)


class VoiceSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, VoiceSession] = {}

    def create(self, session_id: str, question_name: str) -> VoiceSession:
        workspace_root = QUESTIONS_ROOT / question_name
        bot = PairProgrammingVoiceBot(
            workspace=QuestionWorkspace(workspace_root),
            question_name=question_name,
        )
        # Level numbers are 1-based for human-facing messaging.
        bot.struggle_detector.on_level_start(1)
        session = VoiceSession(session_id=session_id, question_name=question_name, bot=bot)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[VoiceSession]:
        return self._sessions.get(session_id)

    def set_mode(self, session_id: str, mode: Mode, trigger: str = "api") -> Optional[Mode]:
        session = self.get(session_id)
        if not session:
            return None
        session.bot.set_mode(mode, trigger=trigger)
        return session.bot.mode

