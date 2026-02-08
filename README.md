# Pair Programming Voice Bot

A real-time voice-powered pair programming assistant that coaches developers through coding challenges. Built with **Cartesia Line SDK** for low-latency voice, **Anthropic Claude** for reasoning, **Browserbase** for live concept lookups, and **Notion** for session journaling.

The bot operates in two collaboration modes — **Bot Drives** (the AI writes code and narrates its reasoning) and **Human Drives** (the developer codes while the AI watches, detects struggles, and offers targeted hints).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Monaco   │  │  Voice   │  │   TTS    │  │  Push   │ │
│  │  Editor   │  │   Orb    │  │  Player  │  │ to Talk │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │              │             │              │      │
└───────┼──────────────┼─────────────┼──────────────┼──────┘
        │ REST         │ REST        │ Audio        │ STT
        ▼              ▼             ▼              ▼
┌───────────────────────────────────────────────────────────┐
│                   FastAPI Backend (:8000)                  │
│                                                           │
│  /api/execute ─── Docker sandbox ─── Test runner          │
│  /api/voice/*  ── Voice session store                     │
│  /api/tts ────── Cartesia TTS proxy                       │
│  /api/session/publish ── Notion page upload               │
│                                                           │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ Claude LLM  │  │ Struggle │  │ Mode State Machine   │ │
│  │  (Anthropic) │  │ Detector │  │ bot_drives ⇄ human  │ │
│  └─────────────┘  └──────────┘  └──────────────────────┘ │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│              Cartesia Line Voice Agent                     │
│                                                           │
│  VoiceAgentApp + LlmAgent (Claude via LiteLLM)           │
│  Sonic TTS (WebSocket) + Ink STT                          │
│                                                           │
│  Tools:                                                   │
│    @passthrough_tool run_tests      → /api/execute        │
│    @passthrough_tool switch_mode    → /api/voice/mode     │
│    @passthrough_tool lookup_concept → /api/voice/lookup   │
│    @passthrough_tool publish_notion → /api/session/publish│
│    generate_code                    → /api/voice/bot_step │
└───────────────────────────────────────────────────────────┘
```

## Tools & Integrations

| Tool | Purpose |
|------|---------|
| **Cartesia Line SDK** | Real-time voice agent with Sonic TTS + Ink STT over WebSocket |
| **Anthropic Claude** | Code generation, coaching hints, concept explanations |
| **Browserbase** | Live web search for programming concepts via headless browser |
| **Notion API** | Session journal upload — test timeline, struggle moments, mode switches, final code |
| **Docker** | Sandboxed code execution with resource limits |
| **Monaco Editor** | In-browser code editing with syntax highlighting |

## Key Features

- **Two collaboration modes** — toggle via voice ("you drive" / "my turn") or UI button
- **Struggle detection** — detects backtracking, repeated failures, long pauses, and explicit help requests
- **Progressive challenge levels** — tests unlock incrementally as you pass each stage
- **Concept lookup** — say "lookup forward chaining" to search docs via Browserbase
- **Session journal** — publish a full session report to Notion with one click
- **Voice orb** — animated orb with idle/speaking/listening states

## Project Structure

```
backend/
  app.py              # FastAPI server — assessment + voice endpoints
  voice_agent.py      # Cartesia Line SDK voice agent server
  llm.py              # Claude client for coaching + code generation
  tts.py              # Cartesia TTS proxy (REST fallback)
  runner.py           # Docker-sandboxed test execution
  sessions.py         # Assessment session store
  voice_sessions.py   # Voice session store with bot state

frontend/src/
  App.tsx             # Main app — editor, terminal, voice panel
  VoiceOrb.tsx        # Animated voice orb component
  tts.ts              # TTS audio playback (Cartesia direct or proxy)
  mic.ts              # Push-to-talk via Web Speech API

src/pair_programming_voice_bot/
  agent.py            # Core bot — mode management, struggle response, tools
  modes.py            # Mode state machine (bot_drives ⇄ human_drives)
  struggle_detector.py # Detects coding struggles from signals
  concept_lookup.py   # Browserbase + static KB concept search
  notion_logger.py    # Session journal → Notion page upload
  workspace.py        # File system tools for the challenge workspace
  policy.py           # Tool access control per mode

questions/ruleengine/ # 4-level progressive Rule Engine challenge
```

## Run Locally

### Setup

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, CARTESIA_API_KEY
# Optional: BROWSERBASE_API_KEY, NOTION_API_KEY, NOTION_PARENT_PAGE_ID
```

### Backend

```bash
pip install -r backend/requirements.txt
PYTHONPATH=src uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### Line Voice Agent

```bash
python3 backend/voice_agent.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
