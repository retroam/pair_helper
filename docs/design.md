# Pair Programming Voice Bot Design

## 1. Overview

A Cartesia-powered voice agent that pair-programs with you through a progressive coding challenge. Two modes:

- **`bot_drives`**: The bot writes code, runs tests, narrates progress. Levels unlock as tests pass.
- **`human_drives`**: The human writes code in the Monaco editor. The bot watches silently and chimes in when it detects struggle — offering hints, or using Browserbase to look up and explain a concept.

Built on **Cartesia TTS + Anthropic LLM** using the `line.llm_agent` SDK.

**Demo task**: Build a Rule Engine — 4 progressive levels from basic condition matching to audit trails with snapshots.

## 2. What We Reuse

The [preparation/](../../preparation/) codebase provides a **complete assessment platform** with Docker-sandboxed execution, progressive level unlocking, and a full web UI. We reuse the infrastructure and swap in our own question.

| Component | Source | What it gives us |
|-----------|--------|-----------------|
| Code execution | `backend/runner.py` | Docker-sandboxed Python execution with resource limits, timeouts, network isolation |
| Test runner | `backend/runner.py` `run_stage_tests()` | Parses unittest output, tracks pass/fail per stage, handles progressive unlocking |
| Session management | `backend/sessions.py` | Session lifecycle, timer, stage progression tracking |
| API layer | `backend/app.py` | `/api/execute`, `/api/assessment/start`, `/api/questions/{name}` — all working |
| Frontend | `frontend/` | Monaco editor, three-pane layout, timer, stage indicators, test output panel |
| Activity logging | `backend/activity_logger.py` | Structured event log with timestamps and session tracking |

**What we add on top:**
- **Rule Engine question** in `questions/ruleengine/` (4 levels, starter code, visible + hidden tests)
- Cartesia TTS + Anthropic LLM voice layer via `line.llm_agent`
- Mode state machine (`bot_drives` / `human_drives`)
- Struggle detector for `human_drives`
- Browserbase tool for concept lookups
- Notion MCP integration for session logs

## 3. The Rule Engine Challenge

A 4-level progressive challenge in `questions/ruleengine/`:

| Level | Focus | Key Concept |
|-------|-------|-------------|
| **L1 — Basic Rules** | Add/remove/evaluate simple conditions (`field op value`) | Dict storage, operator dispatch |
| **L2 — Compound Conditions** | AND/OR groups, nested evaluation, match count | Recursive condition evaluation, JSON parsing |
| **L3 — Priority & Groups** | Priority ordering, group-based conflict resolution (first-match-wins) | Sorting, grouping logic |
| **L4 — Audit & Snapshots** | Timestamped history, top-fired rules, snapshot/restore | `deepcopy`, event tracking |

Each level has its own description (`desc.md`, `desc_level2.md`, etc.) revealed on unlock, visible tests (`basicTests.py`), and hidden tests (`hidden_level[2-4].py`).

## 4. Architecture

```
┌─────────────────────────────────────────────┐
│            Voice Interface                  │
│   Cartesia TTS · STT · Turn-taking          │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│            Agent Core                       │
│   Anthropic Claude · Mode state machine     │
│   Struggle detector (human_drives)          │
└────────┬───────────────┬────────────────────┘
         │               │
┌────────▼────────┐ ┌────▼────────────────────┐
│  Tool Gateway   │ │  Browserbase            │
│  read/edit/run  │ │  Concept lookups when   │
│  @passthrough   │ │  human is stuck         │
└────────┬────────┘ └────┬────────────────────┘
         │               │
┌────────▼───────────────▼────────────────────┐
│     Assessment Backend (reused as-is)       │
│  FastAPI · Docker sandbox · Question bank   │
│  Session mgmt · Stage progression · Logging │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│     Notion Integration (MCP)                │
│  Session log · Diffs · Test timeline        │
└─────────────────────────────────────────────┘
```

### Stack

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| Voice (TTS)   | Cartesia                                    |
| LLM           | Anthropic Claude                            |
| SDK           | `line.llm_agent`                            |
| Tools         | `@passthrough_tool` pattern                 |
| Code editor   | Monaco Editor (reused from preparation)     |
| Code exec     | Docker sandbox (reused from preparation)    |
| Web research  | Browserbase (headless browser for concepts) |
| Integration   | Notion MCP (session logs, artifacts)        |

## 5. Mode Details

### 5.1 `bot_drives`

The bot works through the Rule Engine level by level.

**Flow:**
1. Session starts. Bot reads `desc.md` and `ruleengine.py` (starter code).
2. Bot reads `basicTests.py` to understand Level 1 expectations.
3. Bot implements `add_rule`, `remove_rule`, `evaluate` with simple condition matching.
4. Calls `/api/execute` → Level 1 passes → Level 2 unlocks.
5. Bot reads `desc_level2.md` and `hidden_level2.py`.
6. Narrates: "Level 1 done. Level 2 adds compound AND/OR conditions. I'll need recursive evaluation."
7. Repeats through Level 4.

**Tactical knowledge baked into system prompt:**
- L1/L2: store rules in a dict, dispatch operators with a lookup table
- L2: recursively evaluate nested AND/OR by walking the JSON tree
- L3: `sorted()` with priority key, group dict for first-match-wins
- L4: `deepcopy` for snapshots, list of `(timestamp, rule_name)` for history

**Tools used:** `read_file`, `apply_patch`, `execute_tests` (wraps `/api/execute`), `list_files`

### 5.2 `human_drives`

The human writes code in the Monaco editor. The bot watches and only speaks when it detects struggle.

**Struggle detection signals:**

| Signal | Detection | Example |
|--------|-----------|---------|
| Long pause | No edits for 30+ seconds while tests still fail | Human staring at compound condition logic |
| Repeated failure | Same test error on 2+ consecutive runs | `AssertionError: [] != ['allow_entry']` twice |
| Backtracking | Code shrinks by >20% between snapshots | Human deletes their AND/OR evaluator |
| Explicit ask | Human says "help", "what should I do" | — |
| Level wall | Same level for 5+ minutes | Stuck on L3 priority sorting |

**When the bot chimes in, it can:**

1. **Give a tactical hint**:
   - "For compound conditions, try a recursive approach: if the condition has an 'and' key, evaluate all children and return True only if they all pass."

2. **Explain a concept via Browserbase**:
   - "Let me look that up... A forward-chaining rule engine evaluates all conditions against the current data and fires every matching rule. You want to check each rule independently."

3. **Point out the specific error**:
   - "Your test expects actions sorted alphabetically, but you're returning them in insertion order. Try wrapping with `sorted()`."

4. **Suggest a snippet** (spoken, not applied):
   - "For the operator dispatch, try a dict mapping: `{'eq': lambda a, b: a == b, 'gt': lambda a, b: int(a) > int(b)}`."

**The bot does NOT edit code or run commands in this mode.** It only speaks.

### 5.3 Mode Switching

- Voice: "take over" / "you drive" → `bot_drives`
- Voice: "let me try" / "I'll drive" / "my turn" → `human_drives`
- UI toggle button in the header bar

## 6. Browserbase Integration

Used in `human_drives` when the struggle is conceptual rather than syntactic.

```python
async def lookup_concept(
    env,
    query: Annotated[str, "search query for the concept to explain"],
):
    """Search the web for a programming concept and return a concise explanation.
    Use when the human is stuck on a concept (e.g., rule engine patterns,
    conflict resolution, snapshot/restore) rather than a syntax issue."""
    bb = Browserbase()
    session = bb.sessions.create(project_id=PROJECT_ID)
    # navigate, extract content, return summary to LLM
    ...
```

## 7. Tool Definitions

All tools follow the `line.llm_agent` SDK pattern.

### Shared tools (both modes)

```python
async def read_file(
    env,
    path: Annotated[str, "file path relative to question root"],
):
    """Read a file from the current question workspace."""
    ...

async def read_description(
    env,
    level: Annotated[int, "level number (1-4)"] = 1,
):
    """Read the problem description for a specific level."""
    ...

async def lookup_concept(
    env,
    query: Annotated[str, "concept to look up via web search"],
):
    """Use Browserbase to search and explain a programming concept."""
    ...
```

### `bot_drives` only tools

```python
@passthrough_tool
async def apply_patch(
    env,
    file_path: Annotated[str, "file to edit"],
    old_text: Annotated[str, "exact text to replace"],
    new_text: Annotated[str, "replacement text"],
):
    """Apply a targeted text replacement to a source file."""
    result = do_patch(file_path, old_text, new_text)
    yield AgentSendText(content=f"Patched {file_path}.")

@passthrough_tool
async def execute_tests(env):
    """Run the test suite via the assessment backend.
    Calls POST /api/execute with the current session and files."""
    result = call_execute_api(session_id, question_name, current_files)
    stage = result["stage"]
    visible = result["visible"]
    if stage["current_passed"]:
        if stage["unlocked_next"]:
            yield AgentSendText(
                content=f"Level {stage['current_index'] + 1} passed. "
                        f"Unlocking Level {stage['current_index'] + 2}."
            )
        else:
            yield AgentSendText(content="All levels complete!")
    else:
        yield AgentSendText(
            content=f"Level {stage['current_index'] + 1}: "
                    f"{visible['passed']}/{visible['total']} tests passing. "
                    f"Let me read the failures."
        )
```

### `human_drives` only tools

```python
async def get_current_code(env):
    """Get the code the human is currently writing in the editor."""
    ...

async def get_run_history(env):
    """Get recent test execution results to detect repeated failures."""
    ...
```

## 8. Struggle Detector

Server-side module monitoring the human's coding session.

```python
class StruggleDetector:
    def __init__(self):
        self.last_edit_time = None
        self.run_results = []
        self.code_snapshots = []
        self.level_start_time = {}
        self.nudge_cooldown = 60  # seconds

    def on_code_update(self, code: str):
        now = time.time()
        if self.code_snapshots and len(code) < len(self.code_snapshots[-1]) * 0.8:
            self.signal("backtrack")
        self.code_snapshots.append(code)
        self.last_edit_time = now

    def on_run_result(self, exit_code: int, stderr: str, stage_index: int):
        h = hashlib.md5(stderr.encode()).hexdigest()
        self.run_results.append((exit_code, h, stage_index))
        if len(self.run_results) >= 2 and self.run_results[-1][:2] == self.run_results[-2][:2]:
            self.signal("repeated_failure")

    def on_level_start(self, level: int):
        self.level_start_time[level] = time.time()

    def check_idle(self):
        if self.last_edit_time and time.time() - self.last_edit_time > 30:
            self.signal("long_pause")

    def check_level_wall(self, current_level: int):
        start = self.level_start_time.get(current_level)
        if start and time.time() - start > 300:
            self.signal("level_wall", level=current_level)

    def signal(self, kind: str, **context):
        # inject into agent context:
        # "The human appears stuck ({kind}). Consider offering help."
        ...
```

## 9. Demo Script

### Act 1 — `bot_drives` (2–3 min)

1. "Start the Rule Engine challenge."
2. Bot reads `desc.md` and `basicTests.py`.
3. Bot narrates: "Level 1 needs add, remove, evaluate with simple conditions. I'll use a dict for rules and a lookup table for operators."
4. Bot implements `__init__`, `add_rule`, `remove_rule`, `evaluate`.
5. Runs tests → Level 1 passes → Level 2 unlocks.
6. Bot reads `desc_level2.md`: "Level 2 adds AND/OR compound conditions. I'll add recursive evaluation."
7. Bot implements `add_compound_rule`, updates `evaluate` → tests pass.
8. "Two levels down. Say 'my turn' to take over, or I'll keep going."

### Act 2 — `human_drives` (2–3 min)

1. Human: "I'll drive. Let me try Level 3."
2. Bot: "You got it. Level 3 adds priority ordering and group-based conflict resolution. I'll be here if you need me."
3. Human starts coding. Pauses for 30 seconds on the group logic.
4. Bot chimes in: "For groups, think first-match-wins: collect all matching rules in the group, sort by priority descending, and only fire the top one."
5. Human writes code, runs tests. Gets same assertion error twice.
6. Bot: "Your actions are in insertion order, but the test expects priority ordering — highest priority first, then alphabetical for ties."
7. Human fixes it. Tests pass.

### Act 3 — Browserbase moment (30 sec)

1. Human on Level 4: "What's a snapshot/restore pattern?"
2. Bot uses Browserbase: "Let me look that up... Snapshot means saving a deep copy of your current state at a timestamp. Restore copies it back. Use Python's `copy.deepcopy()`. Important: history should survive a restore — only the rule set rolls back."

### Act 4 — Show Notion (30 sec)

- Notion page with session log: levels completed, who drove each level, struggle moments, Browserbase lookups, test timeline.

## 10. System Prompt (Draft)

```
You are a pair-programming voice assistant helping a developer build a
Rule Engine through 4 progressive levels.

You have two modes:
- bot_drives: You write code, run tests, and narrate your progress.
- human_drives: You watch silently. Only speak when the human is struggling
  (long pauses, repeated failures, backtracking) or asks for help.

Level progression:
- L1: Simple conditions (field op value). Store in dict, dispatch operators.
- L2: Compound AND/OR conditions. Parse JSON, evaluate recursively.
- L3: Priority + groups. Sort by priority desc. Groups use first-match-wins.
- L4: Timestamped history, top-fired stats, snapshot/restore with deepcopy.

When helping in human_drives:
- Be concise and specific. Point out the exact issue.
- Use lookup_concept for conceptual questions.
- Never be condescending.
- Common traps: forgetting to sort actions alphabetically, not handling
  missing fields, returning None instead of empty string.
```

## 11. Notion Integration

After each session, log to Notion via MCP:

- **Session summary**: question, levels completed, mode switches, duration
- **Per-level log**: who drove (bot/human), attempts, time spent
- **Struggle moments**: what triggered the bot, what help was given
- **Browserbase lookups**: queries and summaries
- **Test timeline**: pass/fail progression across all 4 levels
- **Final code**: the completed solution

## 12. Safety Constraints

- Execution sandboxed via Docker: no network, 1 CPU, 512MB RAM, 10s timeout.
- Bot tools (`apply_patch`, `execute_tests`) disabled in `human_drives` mode.
- Filesystem scoped to question workspace.
- Struggle detector has 60-second cooldown between nudges.
- No secrets in logs or model context.

## 13. Implementation Plan

**Phase 1 — Voice loop on top of assessment backend (hour 1–2)**
- Set up `line.llm_agent` with Cartesia TTS + Anthropic LLM.
- System prompt with Rule Engine context.
- Wire to `/api/execute` and `/api/questions` endpoints.
- Mode state machine with voice commands.

**Phase 2 — `bot_drives` (hour 2–4)**
- Implement `read_file`, `apply_patch`, `execute_tests` tools.
- Bot reads desc → writes code → runs tests → handles stage progression.
- End-to-end: bot completes Rule Engine L1–L2.

**Phase 3 — `human_drives` + struggle detection (hour 4–6)**
- Hook into activity logger for code snapshots and run results.
- Implement `StruggleDetector` with signal injection into agent context.
- Browserbase tool for concept lookups.
- Bot only speaks on struggle signals or explicit asks.

**Phase 4 — Notion + demo polish (hour 6–8)**
- Notion MCP integration for session logging.
- Rehearse 5-minute demo with Rule Engine.
- Polish voice narration and struggle detection thresholds.

## 14. Stretch Goals

- Let the user pick from multiple questions at session start.
- Voice-triggered undo ("revert that last change").
- Bot references specific test names when explaining failures.
- Difficulty adaptation: bot gives less help as levels progress.
