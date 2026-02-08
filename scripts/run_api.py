#!/usr/bin/env python3
"""Run the optional FastAPI app for the voice-bot core."""

from __future__ import annotations

try:
    import uvicorn
except ImportError as exc:  # pragma: no cover
    raise SystemExit("uvicorn is required. Install with: pip install uvicorn fastapi") from exc

from pair_programming_voice_bot.server import app


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="127.0.0.1", port=8002)

