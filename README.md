# Pair Programming Voice Bot

Implements the design in `docs/design.md` using the reusable assessment stack plus voice-mode orchestration.

## Repo structure

- `backend/`: FastAPI assessment API (copied from `preparation/`) plus voice endpoints.
- `frontend/`: React + Monaco assessment UI (copied from `preparation/`) plus voice-mode UI controls.
- `questions/ruleengine/`: 4-level progressive Rule Engine challenge.
- `src/pair_programming_voice_bot/`: core mode state machine, struggle detector, tool policy, and agent orchestration.
- `tests/`: unit/integration tests for the new core modules.
- `docker-compose.yml`: local full-stack runner.

## Voice features added

- Mode state machine: `bot_drives` and `human_drives`.
- Backend voice session store keyed by assessment session.
- New API endpoints:
  - `GET /api/voice/{session_id}`
  - `POST /api/voice/mode`
  - `POST /api/voice/input`
  - `POST /api/voice/code_update`
  - `POST /api/voice/check`
  - `POST /api/voice/lookup`
- Frontend:
  - Header mode toggle.
  - Voice coach panel with command input (`my turn`, `you drive`, `lookup ...`).
  - Automatic struggle-signal polling in `human_drives`.

## Rule Engine status

`questions/ruleengine/ruleengine.py` now fully implements:

- Level 1: simple rule add/remove/evaluate.
- Level 2: nested AND/OR compound rules.
- Level 3: priority ordering + first-match-wins groups.
- Level 4: history, top rules, snapshot/restore (history preserved).

## Run locally

### Environment

```bash
cp .env.example .env
```

Current required value:
- `VITE_API_PROXY_TARGET` (defaults to `http://127.0.0.1:8000` in `.env`).

### Backend

```bash
pip install -r backend/requirements.txt
PYTHONPATH=src uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

By default Vite proxies `/api` to `http://127.0.0.1:8000`.

## Run tests

From repo root:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
python3 questions/ruleengine/basicTests.py
python3 questions/ruleengine/hidden_level2.py
python3 questions/ruleengine/hidden_level3.py
python3 questions/ruleengine/hidden_level4.py
```

## Quick core demo

```bash
PYTHONPATH=src python3 scripts/demo_session.py
```
