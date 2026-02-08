import io
import os
import re
import time
from dataclasses import asdict
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .activity_logger import log_event, save_snapshot
from .questions import list_question_names, load_question_config, load_visible_files, question_root
from .runner import ExecutionError, run_code
from .sessions import SessionStore
from .voice_sessions import VoiceSessionStore

from pair_programming_voice_bot.modes import Mode

# LLM + TTS (graceful fallback if keys missing)
_llm_client = None
_tts_client = None

try:
    from .llm import ClaudeClient
    if os.environ.get("ANTHROPIC_API_KEY"):
        _llm_client = ClaudeClient()
except Exception:
    pass

try:
    from .tts import CartesiaTTS
    if os.environ.get("CARTESIA_API_KEY"):
        _tts_client = CartesiaTTS()
except Exception:
    pass

app = FastAPI(title="CodeSignal Assessment Clone")
sessions = SessionStore()
voice_sessions = VoiceSessionStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    question_name: str
    duration_minutes: Optional[int] = None
    user_id: Optional[str] = None


class ExecuteRequest(BaseModel):
    session_id: str
    question_name: str
    files: Dict[str, str]


class LogEventRequest(BaseModel):
    session_id: str
    question_name: str
    action: str
    payload: Optional[Dict] = None


class VoiceModeRequest(BaseModel):
    session_id: str
    mode: str


class VoiceInputRequest(BaseModel):
    session_id: str
    utterance: str
    current_level: Optional[int] = None


class VoiceCodeUpdateRequest(BaseModel):
    session_id: str
    code: str
    current_level: Optional[int] = None


class VoiceCheckRequest(BaseModel):
    session_id: str
    current_level: Optional[int] = None
    tests_still_failing: bool = True


class VoiceLookupRequest(BaseModel):
    session_id: str
    query: str


class TTSRequest(BaseModel):
    text: str


class BotStepRequest(BaseModel):
    session_id: str
    current_level: Optional[int] = None


# ─── Helper: get context for LLM ───

def _get_llm_context(voice_session, current_level: int, utterance: str = "", struggle_signal: str = "") -> Dict:
    bot = voice_session.bot
    current_code = ""
    try:
        current_code = bot.workspace.get_current_code("ruleengine.py")
    except Exception:
        pass
    level_desc = ""
    try:
        level_desc = bot.workspace.read_description(level=current_level)
    except Exception:
        pass
    test_output = ""
    if bot.run_history:
        last_run = bot.run_history[-1]
        test_output = str(last_run.get("stderr", ""))
    return {
        "mode": bot.mode.value,
        "utterance": utterance,
        "current_code": current_code,
        "test_output": test_output,
        "level_description": level_desc,
        "current_level": current_level,
        "struggle_signal": struggle_signal,
        "run_history": bot.run_history[-5:] if bot.run_history else None,
    }


# ─── Assessment endpoints (unchanged) ───

@app.get("/api/questions")
def list_questions():
    return {"questions": list_question_names()}


@app.get("/api/questions/{question_name}")
def get_question(question_name: str):
    try:
        cfg = load_question_config(question_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    files = load_visible_files(question_name, cfg)
    safe_cfg = {k: v for k, v in asdict(cfg).items() if k != "stages"}
    return {"question": safe_cfg, "files": files, "stages": [stage.name for stage in cfg.stages]}


@app.post("/api/assessment/start")
def start_assessment(payload: StartRequest):
    question_name = payload.question_name
    try:
        cfg = load_question_config(question_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    session = sessions.create(question_name, payload.duration_minutes or cfg.default_duration_minutes)
    voice_sessions.create(session.session_id, question_name)
    log_event(session.session_id, question_name, "start", {"duration_minutes": session.duration_minutes})
    remaining = sessions.remaining_seconds(session)
    expires_at = session.started_at.timestamp() + session.duration_minutes * 60
    return {
        "session_id": session.session_id,
        "question_name": question_name,
        "remaining_seconds": remaining,
        "expires_at": expires_at,
        "status": session.status,
        "current_stage_index": session.current_stage_index,
        "stages": [stage.name for stage in cfg.stages],
    }


@app.get("/api/assessment/{session_id}")
def get_assessment(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    remaining = sessions.remaining_seconds(session)
    expires_at = session.started_at.timestamp() + session.duration_minutes * 60
    return {
        "session_id": session.session_id,
        "question_name": session.question_name,
        "remaining_seconds": remaining,
        "expires_at": expires_at,
        "status": session.status,
        "final_score": session.final_score,
        "current_stage_index": session.current_stage_index,
        "stages": [stage.name for stage in load_question_config(session.question_name).stages],
    }


@app.post("/api/execute")
def execute_code(payload: ExecuteRequest):
    session = sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.question_name != payload.question_name:
        raise HTTPException(status_code=400, detail="Question mismatch for session")
    remaining = sessions.remaining_seconds(session)
    if remaining <= 0:
        session.status = "expired"
        raise HTTPException(status_code=410, detail="Session expired")

    start = time.time()
    try:
        results = run_code(payload.question_name, payload.files, session.current_stage_index)
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    runtime_ms = int((time.time() - start) * 1000)
    unlocked_stage_index = None
    unlocked_stage_name = None
    new_visible_files: Dict[str, str] = {}
    is_final_stage = results["stage"]["current_index"] == results["stage"]["total_stages"] - 1
    if is_final_stage and results["stage"]["current_passed"]:
        sessions.mark_score(session.session_id, results["final_score"])
    if results["stage"]["unlocked_next"]:
        sessions.advance_stage(session.session_id)
        updated_session = sessions.get(session.session_id)
        unlocked_stage_index = updated_session.current_stage_index
        cfg = load_question_config(payload.question_name)
        if unlocked_stage_index < len(cfg.stages):
            stage = cfg.stages[unlocked_stage_index]
            unlocked_stage_name = stage.name
            files_to_reveal = (stage.reveal_files or []) + stage.visible_tests
            for rel_path in files_to_reveal:
                path = question_root(payload.question_name) / rel_path
                if path.exists():
                    new_visible_files[rel_path] = path.read_text(encoding="utf-8")
    log_payload = {
        "runtime_ms": runtime_ms,
        "visible_passed": results["visible"]["passed"],
        "visible_total": results["visible"]["total"],
        "stage": results["stage"]["current_index"],
        "unlocked_next": results["stage"]["unlocked_next"],
    }
    save_snapshot(session.session_id, results["stage"]["current_index"], payload.files)
    log_event(
        session.session_id,
        payload.question_name,
        "run",
        log_payload,
    )
    voice_session = voice_sessions.get(session.session_id)
    if voice_session:
        stage_index = int(results["stage"]["current_index"])
        current_level = stage_index + 1
        exit_code = 0 if bool(results["stage"]["current_passed"]) else 1
        visible_output = str(results["visible"].get("output", ""))
        voice_session.bot.observe_run_result(
            exit_code=exit_code,
            stderr=visible_output,
            stage_index=stage_index,
            visible_passed=int(results["visible"].get("passed", 0)),
            visible_total=int(results["visible"].get("total", 0)),
        )
        if results["stage"]["unlocked_next"]:
            voice_session.bot.struggle_detector.on_level_start(current_level + 1)
    return {
        "visible": results["visible"],
        "hidden": results["hidden"],
        "runtime_ms": runtime_ms,
        "final_score": results["final_score"],
        "stage": results["stage"],
        "unlocked_stage_index": unlocked_stage_index,
        "unlocked_stage_name": unlocked_stage_name,
        "new_visible_files": new_visible_files,
    }


@app.post("/api/log")
def log_activity(payload: LogEventRequest):
    session = sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    log_event(payload.session_id, payload.question_name, payload.action, payload.payload or {})
    return {"status": "logged"}


# ─── Voice endpoints (LLM-enhanced) ───

@app.get("/api/voice/{session_id}")
def get_voice_state(session_id: str):
    voice_session = voice_sessions.get(session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    return {
        "session_id": session_id,
        "mode": voice_session.bot.mode.value,
        "run_history_size": len(voice_session.bot.run_history),
    }


@app.post("/api/voice/mode")
def set_voice_mode(payload: VoiceModeRequest):
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    try:
        target_mode = Mode(payload.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode")
    voice_session.bot.set_mode(target_mode, trigger="ui_toggle")
    return {"session_id": payload.session_id, "mode": voice_session.bot.mode.value}


@app.post("/api/voice/input")
def voice_input(payload: VoiceInputRequest):
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    current_level = payload.current_level or 1

    # First, let the existing rule-based logic handle mode commands
    messages = voice_session.bot.handle_voice_input(payload.utterance, current_level=current_level)

    # If no rule-based response and LLM is available, get an intelligent response
    if not messages and _llm_client:
        ctx = _get_llm_context(voice_session, current_level, utterance=payload.utterance)
        llm_response = _llm_client.generate_response(
            **ctx, conversation_history=voice_session.conversation_history
        )
        messages = [llm_response]
        voice_session.conversation_history.append({"role": "user", "content": payload.utterance})
        voice_session.conversation_history.append({"role": "assistant", "content": llm_response})
        voice_session.conversation_history = voice_session.conversation_history[-20:]

    return {"messages": messages, "mode": voice_session.bot.mode.value}


@app.post("/api/voice/code_update")
def voice_code_update(payload: VoiceCodeUpdateRequest):
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    current_level = payload.current_level or 1
    message = voice_session.bot.observe_code_update(
        payload.code,
        current_level=current_level,
    )

    # If struggle detected and LLM available, enhance the hint
    if message and _llm_client:
        ctx = _get_llm_context(voice_session, current_level, struggle_signal="code_change_struggle")
        message = _llm_client.generate_response(
            **ctx, conversation_history=voice_session.conversation_history
        )
        voice_session.conversation_history.append({"role": "system", "content": "Code update observed. Struggle signal detected."})
        voice_session.conversation_history.append({"role": "assistant", "content": message})
        voice_session.conversation_history = voice_session.conversation_history[-20:]

    return {"message": message, "mode": voice_session.bot.mode.value}


@app.post("/api/voice/check")
def voice_check(payload: VoiceCheckRequest):
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    current_level = payload.current_level or 1
    message = voice_session.bot.periodic_check(
        current_level=current_level,
        tests_still_failing=payload.tests_still_failing,
    )

    # If struggle detected and LLM available, enhance the hint
    if message and _llm_client:
        ctx = _get_llm_context(voice_session, current_level, struggle_signal="periodic_check")
        message = _llm_client.generate_response(
            **ctx, conversation_history=voice_session.conversation_history
        )
        voice_session.conversation_history.append({"role": "system", "content": "Periodic check. Struggle signal detected."})
        voice_session.conversation_history.append({"role": "assistant", "content": message})
        voice_session.conversation_history = voice_session.conversation_history[-20:]

    return {"message": message, "mode": voice_session.bot.mode.value}


@app.post("/api/voice/lookup")
def voice_lookup(payload: VoiceLookupRequest):
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    summary = voice_session.bot.lookup_concept(payload.query)

    # If LLM available, enhance the concept explanation
    if _llm_client:
        summary = _llm_client.summarize_concept(payload.query, summary)

    return {"summary": summary, "mode": voice_session.bot.mode.value}


# ─── TTS endpoint (Cartesia proxy) ───

@app.post("/api/tts")
def text_to_speech(payload: TTSRequest):
    if not _tts_client:
        raise HTTPException(status_code=503, detail="TTS not configured — set CARTESIA_API_KEY")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    def audio_stream():
        for chunk in _tts_client.stream_audio(payload.text):
            yield chunk

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline"},
    )


# ─── Parse bot response into narration + file replacements ───

_CODE_RE = re.compile(r'<code\s+file="([^"]+)">\s*\n(.*?)</code>', re.DOTALL)


def _parse_bot_response(raw: str) -> Dict:
    file_updates: Dict[str, str] = {}
    for m in _CODE_RE.finditer(raw):
        filename = m.group(1).strip()
        content = m.group(2).rstrip()
        file_updates[filename] = content
    # Everything outside <code> blocks is narration
    narration = _CODE_RE.sub("", raw).strip()
    narration = re.sub(r"\n{3,}", "\n\n", narration)
    return {"narration": narration, "file_updates": file_updates}


# ─── Bot step endpoint (for bot_drives auto-drive) ───

@app.post("/api/voice/bot_step")
def bot_step(payload: BotStepRequest):
    """One step of bot-driven coding: LLM analyzes code + tests, returns narration."""
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")
    if voice_session.bot.mode != Mode.BOT_DRIVES:
        raise HTTPException(status_code=409, detail="Not in bot_drives mode")
    if not _llm_client:
        raise HTTPException(status_code=503, detail="LLM not configured")

    current_level = payload.current_level or 1
    ctx = _get_llm_context(voice_session, current_level)
    result = _llm_client.generate_bot_step(
        current_code=ctx["current_code"],
        test_output=ctx["test_output"],
        level_description=ctx["level_description"],
        current_level=current_level,
        run_history=ctx["run_history"],
        conversation_history=voice_session.conversation_history,
    )
    parsed = _parse_bot_response(result["narration"])
    voice_session.conversation_history.append({"role": "user", "content": f"[bot_step] Level {current_level} — generate next implementation step."})
    voice_session.conversation_history.append({"role": "assistant", "content": result["narration"]})
    voice_session.conversation_history = voice_session.conversation_history[-20:]
    return {
        "narration": parsed["narration"],
        "file_updates": parsed["file_updates"],
        "mode": voice_session.bot.mode.value,
    }


# ─── Session publish to Notion ───

class PublishRequest(BaseModel):
    session_id: str


@app.post("/api/session/publish")
def publish_session(payload: PublishRequest):
    """Publish session journal to Notion."""
    voice_session = voice_sessions.get(payload.session_id)
    if not voice_session:
        raise HTTPException(status_code=404, detail="Voice session not found")

    bot = voice_session.bot
    try:
        bot.journal.set_final_code(bot.workspace.get_current_code("ruleengine.py"))
    except Exception:
        pass

    url = bot.journal.upload_to_notion()
    if url:
        return {"status": "published", "notion_url": url}

    # Fallback: save locally
    import tempfile
    path = f"/tmp/session_{payload.session_id}.json"
    bot.journal.save(path)
    return {"status": "saved_locally", "path": path}
