import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from .config import DEFAULT_DURATION_MINUTES, MAX_DURATION_MINUTES, MIN_DURATION_MINUTES


@dataclass
class Session:
    session_id: str
    question_name: str
    started_at: datetime
    duration_minutes: int
    status: str = "active"  # active, expired
    final_score: Optional[float] = None
    current_stage_index: int = 0


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def create(self, question_name: str, duration_minutes: Optional[int]) -> Session:
        duration = duration_minutes or DEFAULT_DURATION_MINUTES
        duration = max(MIN_DURATION_MINUTES, min(MAX_DURATION_MINUTES, duration))
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            question_name=question_name,
            started_at=datetime.now(timezone.utc),
            duration_minutes=duration,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        # update status based on time
        if session.status == "active" and self.remaining_seconds(session) <= 0:
            session.status = "expired"
        return session

    def remaining_seconds(self, session: Session) -> int:
        expires_at = session.started_at + timedelta(minutes=session.duration_minutes)
        delta = expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))

    def mark_score(self, session_id: str, score: float) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.final_score = score
            if session.status != "expired" and self.remaining_seconds(session) <= 0:
                session.status = "expired"

    def advance_stage(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.current_stage_index += 1
