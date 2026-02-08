"""Optional FastAPI surface around the agent core."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .agent import PairProgrammingVoiceBot
from .modes import Mode
from .workspace import QuestionWorkspace

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - optional runtime dependency
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment]


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[2] / "questions" / "ruleengine"


class ModeRequest(BaseModel):  # type: ignore[misc]
    mode: str


class VoiceRequest(BaseModel):  # type: ignore[misc]
    utterance: str
    current_level: int = 1


class CodeUpdateRequest(BaseModel):  # type: ignore[misc]
    code: str
    current_level: int = 1


class RunResultRequest(BaseModel):  # type: ignore[misc]
    exit_code: int
    stderr: str
    stage_index: int
    visible_passed: int = 0
    visible_total: int = 0


class PeriodicRequest(BaseModel):  # type: ignore[misc]
    current_level: int
    tests_still_failing: bool = True


def create_app(bot: Optional[PairProgrammingVoiceBot] = None):  # pragma: no cover - thin wrapper
    if FastAPI is None:
        raise RuntimeError("fastapi is not installed; install it to run the API server.")

    app = FastAPI(title="Pair Programming Voice Bot API")
    agent = bot or PairProgrammingVoiceBot(
        workspace=QuestionWorkspace(_default_workspace_root()),
        question_name="ruleengine",
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": agent.mode.value}

    @app.get("/mode")
    def get_mode():
        return {"mode": agent.mode.value}

    @app.post("/mode")
    def set_mode(payload: ModeRequest):
        try:
            mode = Mode(payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        agent.set_mode(mode, trigger="api")
        return {"mode": agent.mode.value}

    @app.post("/voice")
    def voice(payload: VoiceRequest):
        messages = agent.handle_voice_input(payload.utterance, payload.current_level)
        return {"mode": agent.mode.value, "messages": messages}

    @app.post("/signals/code")
    def code_signal(payload: CodeUpdateRequest):
        message = agent.observe_code_update(payload.code, current_level=payload.current_level)
        return {"message": message}

    @app.post("/signals/run")
    def run_signal(payload: RunResultRequest):
        message = agent.observe_run_result(
            exit_code=payload.exit_code,
            stderr=payload.stderr,
            stage_index=payload.stage_index,
            visible_passed=payload.visible_passed,
            visible_total=payload.visible_total,
        )
        return {"message": message}

    @app.post("/signals/check")
    def periodic(payload: PeriodicRequest):
        message = agent.periodic_check(
            current_level=payload.current_level,
            tests_still_failing=payload.tests_still_failing,
        )
        return {"message": message}

    return app


if FastAPI is not None:  # pragma: no cover
    app = create_app()

