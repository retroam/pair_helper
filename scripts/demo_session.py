#!/usr/bin/env python3
"""Small CLI demo for the pair-programming voice bot core."""

from __future__ import annotations

import argparse
from pathlib import Path

from pair_programming_voice_bot.agent import PairProgrammingVoiceBot
from pair_programming_voice_bot.modes import Mode
from pair_programming_voice_bot.workspace import QuestionWorkspace


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local bot session demo.")
    parser.add_argument(
        "--question-root",
        default=str(Path(__file__).resolve().parents[1] / "questions" / "ruleengine"),
        help="Path to the question workspace.",
    )
    args = parser.parse_args()

    workspace = QuestionWorkspace(args.question_root)
    bot = PairProgrammingVoiceBot(workspace=workspace, question_name="ruleengine")

    print("Mode:", bot.mode.value)
    print("Description preview:", bot.read_description(1).splitlines()[0])

    bot.set_mode(Mode.HUMAN_DRIVES, trigger="demo")
    print("Mode switched to:", bot.mode.value)

    response = bot.observe_code_update("abcde", current_level=3, now=10.0)
    print("Update 1 response:", response)
    response = bot.observe_code_update("a", current_level=3, now=11.0)
    print("Update 2 response:", response)

    concept = bot.lookup_concept("snapshot restore pattern in python")
    print("Lookup:", concept)

    output = Path(args.question_root).parent.parent / "tests" / "artifacts" / "demo_session_log.json"
    bot.save_session_journal(str(output))
    print("Saved journal:", output)


if __name__ == "__main__":
    main()

