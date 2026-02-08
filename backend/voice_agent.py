import os
from typing import Annotated

import httpx

from . import env  # noqa: F401

from line.events import AgentSendText
from line.llm_agent import LlmAgent, LlmConfig, passthrough_tool
from line.voice_agent_app import AgentEnv, CallRequest, PreCallResult, VoiceAgentApp

FASTAPI_BASE = "http://localhost:8000"

SYSTEM_PROMPT = """\
You are a pair-programming voice coach helping a developer solve the "Rule Engine" coding challenge. \
You speak concisely — 1 to 3 SHORT sentences max, since your words are read aloud via TTS.

The Rule Engine challenge has these concepts: conditions with field/operator/value, \
logical operators (AND/OR), nested condition groups, rule priorities, and state snapshots. \
Levels unlock progressively as tests pass.

You operate in two modes:
- **human_drives**: the user writes code and you coach them with hints and encouragement.
- **bot_drives**: you generate code step-by-step and narrate your reasoning.

You can: run tests, switch modes, look up programming concepts, generate code (bot_drives), \
and publish the session journal to Notion.

Be encouraging but direct. Never repeat the full problem statement. \
Focus on the user's current stuck point or next step.\
"""


@passthrough_tool
async def run_tests(
    ctx,
    session_id: Annotated[str, "The active session ID"],
    question_name: Annotated[str, "The question name, e.g. 'ruleengine'"],
    code: Annotated[str, "The current code to test"],
):
    """Run the user's code against the test suite and report results."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{FASTAPI_BASE}/api/execute",
            json={
                "session_id": session_id,
                "question_name": question_name,
                "files": {"ruleengine.py": code},
            },
        )
    if resp.status_code == 200:
        data = resp.json()
        visible = data.get("visible", {})
        passed = visible.get("passed", 0)
        total = visible.get("total", 0)
        stage = data.get("stage", {})
        summary = f"Tests: {passed}/{total} passed."
        if stage.get("unlocked_next"):
            summary += " Next stage unlocked!"
    else:
        summary = f"Test run failed: {resp.text[:200]}"
    yield AgentSendText(text=summary)


@passthrough_tool
async def switch_mode(
    ctx,
    session_id: Annotated[str, "The active session ID"],
    mode: Annotated[str, "Target mode: 'bot_drives' or 'human_drives'"],
):
    """Switch between bot_drives and human_drives collaboration modes."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{FASTAPI_BASE}/api/voice/mode",
            json={"session_id": session_id, "mode": mode},
        )
    if resp.status_code == 200:
        new_mode = resp.json().get("mode", mode)
        yield AgentSendText(text=f"Switched to {new_mode.replace('_', ' ')} mode.")
    else:
        yield AgentSendText(text="Could not switch mode right now.")


@passthrough_tool
async def lookup_concept(
    ctx,
    session_id: Annotated[str, "The active session ID"],
    query: Annotated[str, "The programming concept to look up"],
):
    """Look up a programming concept using web search and knowledge base."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{FASTAPI_BASE}/api/voice/lookup",
            json={"session_id": session_id, "query": query},
        )
    if resp.status_code == 200:
        summary = resp.json().get("summary", "No information found.")
    else:
        summary = "Lookup failed. Try rephrasing your question."
    yield AgentSendText(text=summary)


@passthrough_tool
async def publish_to_notion(
    ctx,
    session_id: Annotated[str, "The active session ID"],
):
    """Publish the session journal to Notion for review and sharing."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{FASTAPI_BASE}/api/session/publish",
            json={"session_id": session_id},
        )
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "published":
            yield AgentSendText(text=f"Published to Notion! {data.get('notion_url', '')}")
        else:
            yield AgentSendText(text="Session saved locally.")
    else:
        yield AgentSendText(text="Could not publish to Notion right now.")


async def generate_code(
    ctx,
    session_id: Annotated[str, "The active session ID"],
    current_level: Annotated[int, "The current challenge level (1-based)"] = 1,
) -> str:
    """Generate the next code implementation step for the current level."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{FASTAPI_BASE}/api/voice/bot_step",
            json={"session_id": session_id, "current_level": current_level},
        )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("narration", "Code step generated.")
    return f"Code generation failed: {resp.text[:200]}"


async def get_agent(env: AgentEnv, call_request: CallRequest) -> LlmAgent:
    return LlmAgent(
        model="anthropic/claude-sonnet-4-5-20250929",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        tools=[run_tests, switch_mode, lookup_concept, publish_to_notion, generate_code],
        config=LlmConfig(
            system_prompt=SYSTEM_PROMPT,
            introduction="Hey! I'm your pair-programming voice coach. Say 'you drive' to let me code, or ask me anything about the challenge.",
        ),
    )


async def pre_call_handler(call_request: CallRequest) -> PreCallResult:
    return PreCallResult(
        config={
            "tts": {
                "voice": "a0e99841-438c-4a64-b679-ae501e7d6091",
                "model": "sonic-2",
                "language": "en",
            }
        }
    )


app = VoiceAgentApp(
    get_agent=get_agent,
    pre_call_handler=pre_call_handler,
)

if __name__ == "__main__":
    app.run()
