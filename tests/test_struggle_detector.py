import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pair_programming_voice_bot.struggle_detector import StruggleDetector


class StruggleDetectorTests(unittest.TestCase):
    def test_backtrack_signal(self):
        detector = StruggleDetector(nudge_cooldown=0)
        self.assertIsNone(detector.on_code_update("1234567890", now=10.0))
        signal = detector.on_code_update("12", now=11.0)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.kind, "backtrack")

    def test_repeated_failure_signal(self):
        detector = StruggleDetector(nudge_cooldown=0)
        self.assertIsNone(detector.on_run_result(1, "AssertionError", 2, now=20.0))
        signal = detector.on_run_result(1, "AssertionError", 2, now=21.0)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.kind, "repeated_failure")

    def test_idle_and_level_wall(self):
        detector = StruggleDetector(idle_threshold_seconds=30, level_wall_seconds=300, nudge_cooldown=0)
        detector.on_code_update("abc", now=100.0)
        idle = detector.check_idle(tests_still_failing=True, now=131.0)
        self.assertIsNotNone(idle)
        self.assertEqual(idle.kind, "long_pause")

        detector.on_level_start(3, now=200.0)
        wall = detector.check_level_wall(current_level=3, now=501.0)
        self.assertIsNotNone(wall)
        self.assertEqual(wall.kind, "level_wall")

    def test_cooldown_suppresses_extra_signals(self):
        detector = StruggleDetector(nudge_cooldown=60)
        detector.on_code_update("abcdefghij", now=10.0)
        first = detector.on_code_update("a", now=11.0)
        self.assertIsNotNone(first)
        second = detector.on_run_result(1, "AssertionError", 2, now=12.0)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()

