"""Claude LLM client for pair-programming voice bot."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

import anthropic


SYSTEM_PROMPT_HUMAN_DRIVES = """You are a pair-programming voice coach. The human is driving (writing code).
You observe their code and test results. Keep responses to 1-2 SHORT sentences since they will be spoken aloud via TTS.
Be encouraging but direct. Reference specific code when giving hints. Never write full solutions — nudge toward the answer.
If you see a struggle signal, give a targeted micro-hint about the exact issue."""

SYSTEM_PROMPT_BOT_DRIVES = """You are a pair-programming voice bot. You are driving — writing code and running tests.
Narrate your thinking in 1-2 SHORT sentences (spoken aloud via TTS). Be concise and action-oriented.
When generating code patches, output them in this exact format:
<patch>
FILE: filename.py
OLD:
old code here
NEW:
new code here
</patch>
After the patch block, add a 1-sentence narration of what you did and why."""

SYSTEM_PROMPT_BOT_STEP = """You are an expert Python developer pair-programming live. You talk casually, like a real dev thinking out loud.

Your job: implement the Rule Engine solution ONE SMALL STEP at a time. Look at failing tests, figure out what's needed, and write working code.

CRITICAL RULES:
- NEVER return None from any public method. Return '' (empty string), [] (empty list), or False instead.
- NEVER leave methods with just 'pass' or 'return None'. Always implement real logic.
- Each step: fix ONE method or ONE issue. Don't try to do everything at once.
- After seeing test output, fix EXACTLY what the tests complain about.

LEVEL IMPLEMENTATION GUIDE:
Level 1 - Basic Rules:
  - __init__: self.rules = {} (dict mapping rule_name -> rule_dict)
  - add_rule(name, rule): store rule in self.rules, return True
  - remove_rule(name): remove from self.rules, return True if existed, False if not
  - evaluate(data): check each rule's condition against data, return comma-separated string of matching rule actions sorted alphabetically
  - Condition format: {"field": "age", "operator": "eq", "value": "25"}
  - Operators: eq, neq, gt, lt, gte, lte (compare as strings or ints as appropriate)

Level 2 - Compound Conditions:
  - Support AND/OR compound conditions: {"and": [cond1, cond2]} or {"or": [cond1, cond2]}
  - Recursively evaluate nested conditions
  - add_compound_rule works like add_rule but with compound condition

Level 3 - Priority & Groups:
  - Rules have priority (higher = fires first) and optional group
  - Within a group, only the highest-priority match fires (first-match-wins)
  - Sort results by priority descending, then alphabetically for ties

Level 4 - Audit & Snapshots:
  - Track evaluation history with timestamps
  - top_rules(n) returns most-fired rules
  - snapshot()/restore() with deepcopy, history survives restore

OUTPUT FORMAT — follow EXACTLY:
1. First, 1-2 sentences narrating what you'll do. Talk like a dev: "OK let me wire up add_rule to store rules in the dict and return True."
2. Then the COMPLETE updated file in a <code> block:

<code file="ruleengine.py">
...entire file content...
</code>

The <code> block MUST contain the COMPLETE file — not a diff, not a snippet. Include ALL methods, even unchanged ones."""


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def generate_response(
        self,
        *,
        mode: str,
        utterance: str = "",
        current_code: str = "",
        test_output: str = "",
        level_description: str = "",
        current_level: int = 1,
        struggle_signal: str = "",
        run_history: Optional[List[Dict]] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> str:
        system = SYSTEM_PROMPT_HUMAN_DRIVES if mode == "human_drives" else SYSTEM_PROMPT_BOT_DRIVES

        context_parts = []
        if level_description:
            context_parts.append(f"## Current Level ({current_level})\n{level_description[:1000]}")
        if current_code:
            context_parts.append(f"## Current Code\n```python\n{current_code[:3000]}\n```")
        if test_output:
            context_parts.append(f"## Latest Test Output\n```\n{test_output[:1500]}\n```")
        if struggle_signal:
            context_parts.append(f"## Struggle Signal Detected: {struggle_signal}")
        if run_history:
            recent = run_history[-3:]
            history_str = "\n".join(
                f"- Run {i+1}: {r.get('visible_passed',0)}/{r.get('visible_total',0)} passed"
                for i, r in enumerate(recent)
            )
            context_parts.append(f"## Recent Runs\n{history_str}")

        context_block = "\n\n".join(context_parts)

        user_msg = ""
        if utterance:
            user_msg = f"Human says: \"{utterance}\"\n\n"
        user_msg += f"Context:\n{context_block}\n\nRespond concisely (1-2 sentences, will be spoken aloud)."

        messages = []
        if conversation_history:
            messages.extend(conversation_history[-20:])
        messages.append({"role": "user", "content": user_msg})

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                system=system,
                messages=messages,
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"I had trouble thinking about that. {str(e)[:100]}"

    def generate_bot_step(
        self,
        *,
        current_code: str,
        test_output: str,
        level_description: str,
        current_level: int,
        run_history: Optional[List[Dict]] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, str]:
        """Generate a code patch and narration for bot_drives mode."""
        context_parts = []
        if level_description:
            context_parts.append(f"## Level {current_level} Description\n{level_description[:1500]}")
        if current_code:
            context_parts.append(f"## Current Code (ruleengine.py)\n```python\n{current_code[:4000]}\n```")
        if test_output:
            context_parts.append(f"## Latest Test Output\n```\n{test_output[:2000]}\n```")
        if run_history:
            recent = run_history[-3:]
            history_str = "\n".join(
                f"- Run {i+1}: {r.get('visible_passed',0)}/{r.get('visible_total',0)} passed"
                for i, r in enumerate(recent)
            )
            context_parts.append(f"## Recent Runs\n{history_str}")

        context_block = "\n\n".join(context_parts)
        user_msg = f"{context_block}\n\nWrite the next small implementation step. First narrate what you'll do (1-2 sentences), then output the complete updated file in a <code> block."

        messages = []
        if conversation_history:
            messages.extend(conversation_history[-20:])
        messages.append({"role": "user", "content": user_msg})

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                system=SYSTEM_PROMPT_BOT_STEP,
                messages=messages,
            )
            result_text = response.content[0].text.strip()

            if "<code file=" in result_text:
                code_match = re.search(r"<code file=[^>]+>(.*?)</code>", result_text, re.DOTALL)
                if code_match:
                    code_body = code_match.group(1)
                    public_methods = re.findall(
                        r"def\s+(add_rule|remove_rule|evaluate)\b.*?(?=\n    def |\nclass |\Z)",
                        code_body,
                        re.DOTALL,
                    )
                    has_return_none = bool(
                        re.search(
                            r"def\s+(?:add_rule|remove_rule|evaluate)\b[^}]*?return\s+None",
                            code_body,
                            re.DOTALL,
                        )
                    )
                    if has_return_none:
                        messages.append({"role": "assistant", "content": result_text})
                        messages.append({
                            "role": "user",
                            "content": (
                                "Your code has 'return None' in public methods. Fix this - "
                                "add_rule should return True, remove_rule should return True/False, "
                                "evaluate should return a string. Output the corrected COMPLETE file "
                                "in a <code> block."
                            ),
                        })
                        retry_response = self.client.messages.create(
                            model="claude-sonnet-4-5-20250929",
                            max_tokens=8000,
                            system=SYSTEM_PROMPT_BOT_STEP,
                            messages=messages,
                        )
                        result_text = retry_response.content[0].text.strip()

            return {"narration": result_text}
        except Exception as e:
            return {"narration": f"I had trouble generating the next step. {str(e)[:100]}"}

    def summarize_concept(self, query: str, raw_text: str) -> str:
        """Summarize a concept lookup result into 1-2 sentences for TTS."""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=150,
                system="Summarize the following into 1-2 concise sentences suitable for speaking aloud. Focus on practical understanding.",
                messages=[{"role": "user", "content": f"Query: {query}\n\nSource text:\n{raw_text[:2000]}"}],
            )
            return response.content[0].text.strip()
        except Exception:
            return raw_text[:200]
