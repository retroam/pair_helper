import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTION_ROOT = ROOT / "questions" / "ruleengine"
if str(QUESTION_ROOT) not in sys.path:
    sys.path.insert(0, str(QUESTION_ROOT))

from ruleengine import RuleEngine


class RuleEngineSolutionTests(unittest.TestCase):
    def test_group_conflict_resolution_and_ordering(self):
        engine = RuleEngine()
        self.assertEqual("true", engine.add_rule("g1_hi", "x", "eq", "1", "g_hi", "10", "grp"))
        self.assertEqual("true", engine.add_rule("g1_lo", "x", "eq", "1", "g_lo", "5", "grp"))
        self.assertEqual("true", engine.add_rule("free", "x", "eq", "1", "free", "7", ""))
        self.assertEqual("g_hi,free", engine.evaluate("x=1"))

    def test_snapshot_restore_keeps_history(self):
        engine = RuleEngine()
        engine.add_rule("r1", "x", "eq", "1", "a1")
        self.assertEqual("a1", engine.evaluate("x=1", "100"))
        self.assertEqual("1", engine.snapshot("200"))
        engine.remove_rule("r1")
        self.assertEqual("", engine.evaluate("x=1", "300"))
        self.assertEqual("true", engine.restore("200"))
        self.assertEqual("a1", engine.evaluate("x=1", "400"))
        self.assertEqual("100,400", engine.history("r1"))


if __name__ == "__main__":
    unittest.main()

