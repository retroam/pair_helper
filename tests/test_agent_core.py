import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pair_programming_voice_bot.agent import PairProgrammingVoiceBot
from pair_programming_voice_bot.modes import Mode
from pair_programming_voice_bot.policy import ToolPolicyViolation
from pair_programming_voice_bot.struggle_detector import StruggleDetector
from pair_programming_voice_bot.workspace import QuestionWorkspace


class AgentCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        (root / "desc.md").write_text("# Rule Engine\n", encoding="utf-8")
        (root / "desc_level2.md").write_text("# Level 2\n", encoding="utf-8")
        (root / "ruleengine.py").write_text("print('hello')\n", encoding="utf-8")
        self.workspace = QuestionWorkspace(root)
        self.bot = PairProgrammingVoiceBot(
            workspace=self.workspace,
            question_name="ruleengine",
            struggle_detector=StruggleDetector(nudge_cooldown=0),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_voice_mode_switch(self):
        self.assertEqual(self.bot.mode, Mode.BOT_DRIVES)
        response = self.bot.handle_voice_input("my turn", current_level=1)
        self.assertEqual(self.bot.mode, Mode.HUMAN_DRIVES)
        self.assertEqual(len(response), 1)

    def test_policy_blocks_apply_patch_in_human_mode(self):
        self.bot.set_mode(Mode.HUMAN_DRIVES, trigger="test")
        with self.assertRaises(ToolPolicyViolation):
            self.bot.apply_patch("ruleengine.py", "hello", "world")

    def test_human_mode_gets_hint_on_backtrack(self):
        self.bot.set_mode(Mode.HUMAN_DRIVES, trigger="test")
        self.bot.observe_code_update("1234567890", current_level=3, now=10.0)
        hint = self.bot.observe_code_update("1", current_level=3, now=11.0)
        self.assertIsNotNone(hint)
        self.assertIn("first-match-wins", hint)

    def test_can_save_journal(self):
        self.bot.set_mode(Mode.HUMAN_DRIVES, trigger="test")
        self.bot.handle_voice_input("help", current_level=2)
        output = Path(self.tmpdir.name) / "journal.json"
        self.bot.save_session_journal(str(output))
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["question_name"], "ruleengine")
        self.assertTrue("final_code" in data)


if __name__ == "__main__":
    unittest.main()

