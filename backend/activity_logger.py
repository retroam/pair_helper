import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .config import LOG_DIR, LOG_FILE, SNAPSHOTS_DIR


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def save_snapshot(session_id: str, stage: int, files: Dict[str, str]) -> None:
    """
    Overwrite the current code snapshot for a session/stage.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = SNAPSHOTS_DIR / f"{session_id}_stage{stage}.json"
    snapshot = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "stage": stage,
        "files": files,
    }
    snapshot_file.write_text(json.dumps(snapshot, ensure_ascii=True), encoding="utf-8")


def log_event(session_id: str, question_name: str, action: str, payload: Dict[str, Any]) -> None:
    """
    Append a single-line JSON log entry with basic session context.
    """
    ensure_log_dir()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "question": question_name,
        "action": action,
        "payload": payload,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")
