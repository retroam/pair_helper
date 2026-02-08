import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pair_programming_voice_bot.modes import Mode
from pair_programming_voice_bot.policy import ToolAction, ToolPolicy, ToolPolicyViolation


class ToolPolicyTests(unittest.TestCase):
    def test_bot_drives_can_edit_and_execute(self):
        ToolPolicy.assert_allowed(Mode.BOT_DRIVES, ToolAction.APPLY_PATCH)
        ToolPolicy.assert_allowed(Mode.BOT_DRIVES, ToolAction.EXECUTE_TESTS)

    def test_human_drives_cannot_edit_or_execute(self):
        with self.assertRaises(ToolPolicyViolation):
            ToolPolicy.assert_allowed(Mode.HUMAN_DRIVES, ToolAction.APPLY_PATCH)
        with self.assertRaises(ToolPolicyViolation):
            ToolPolicy.assert_allowed(Mode.HUMAN_DRIVES, ToolAction.EXECUTE_TESTS)

    def test_human_drives_can_read_code_and_history(self):
        ToolPolicy.assert_allowed(Mode.HUMAN_DRIVES, ToolAction.GET_CURRENT_CODE)
        ToolPolicy.assert_allowed(Mode.HUMAN_DRIVES, ToolAction.GET_RUN_HISTORY)


if __name__ == "__main__":
    unittest.main()

