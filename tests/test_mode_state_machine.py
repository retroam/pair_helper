import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pair_programming_voice_bot.modes import Mode, ModeStateMachine, detect_mode_command


class ModeStateMachineTests(unittest.TestCase):
    def test_detect_mode_command(self):
        self.assertEqual(detect_mode_command("you drive"), Mode.BOT_DRIVES)
        self.assertEqual(detect_mode_command("my turn"), Mode.HUMAN_DRIVES)
        self.assertIsNone(detect_mode_command("keep going"))

    def test_transition_only_when_mode_changes(self):
        machine = ModeStateMachine(initial_mode=Mode.BOT_DRIVES)
        self.assertIsNone(machine.apply_voice_command("take over"))
        transition = machine.apply_voice_command("let me try")
        self.assertIsNotNone(transition)
        self.assertEqual(transition.previous, Mode.BOT_DRIVES)
        self.assertEqual(transition.current, Mode.HUMAN_DRIVES)
        self.assertEqual(machine.mode, Mode.HUMAN_DRIVES)


if __name__ == "__main__":
    unittest.main()

