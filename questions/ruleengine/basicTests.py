import unittest

from ruleengine import RuleEngine


def run_queries(engine: RuleEngine, queries):
    results = []
    for query in queries:
        command = query[0]
        if command == "ADD_RULE":
            priority = query[6] if len(query) > 6 else "0"
            group = query[7] if len(query) > 7 else ""
            results.append(engine.add_rule(query[1], query[2], query[3], query[4], query[5], priority, group))
        elif command == "ADD_COMPOUND_RULE":
            priority = query[4] if len(query) > 4 else "0"
            group = query[5] if len(query) > 5 else ""
            results.append(engine.add_compound_rule(query[1], query[2], query[3], priority, group))
        elif command == "REMOVE_RULE":
            results.append(engine.remove_rule(query[1]))
        elif command == "EVALUATE":
            timestamp = query[2] if len(query) > 2 else ""
            results.append(engine.evaluate(query[1], timestamp))
        elif command == "MATCH_COUNT":
            results.append(engine.match_count(query[1]))
        elif command == "LIST_GROUP":
            results.append(engine.list_group(query[1]))
        elif command == "HISTORY":
            results.append(engine.history(query[1]))
        elif command == "TOP_RULES":
            results.append(engine.top_rules(query[1]))
        elif command == "SNAPSHOT":
            results.append(engine.snapshot(query[1]))
        elif command == "RESTORE":
            results.append(engine.restore(query[1]))
    return results


class Level1BasicRulesTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()

    def test_add_and_evaluate_simple_rules(self):
        queries = [
            ["ADD_RULE", "age_check", "age", "gte", "18", "allow_entry"],
            ["ADD_RULE", "vip_check", "role", "eq", "vip", "fast_track"],
            ["ADD_RULE", "age_check", "age", "gt", "21", "duplicate"],  # duplicate name
            ["EVALUATE", "age=25,role=vip"],
            ["EVALUATE", "age=15,role=vip"],
            ["EVALUATE", "age=25,role=member"],
        ]
        expected = [
            "true",
            "true",
            "false",
            "allow_entry,fast_track",
            "fast_track",
            "allow_entry",
        ]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_remove_rule(self):
        queries = [
            ["ADD_RULE", "r1", "score", "gt", "50", "pass"],
            ["EVALUATE", "score=60"],
            ["REMOVE_RULE", "r1"],
            ["EVALUATE", "score=60"],
            ["REMOVE_RULE", "r1"],  # already removed
        ]
        expected = ["true", "pass", "true", "", "false"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_operators(self):
        queries = [
            ["ADD_RULE", "eq_test", "status", "eq", "active", "a1"],
            ["ADD_RULE", "neq_test", "status", "neq", "banned", "a2"],
            ["ADD_RULE", "gt_test", "level", "gt", "5", "a3"],
            ["ADD_RULE", "lt_test", "level", "lt", "10", "a4"],
            ["ADD_RULE", "gte_test", "level", "gte", "5", "a5"],
            ["ADD_RULE", "lte_test", "level", "lte", "5", "a6"],
            ["EVALUATE", "status=active,level=5"],
        ]
        expected = ["true", "true", "true", "true", "true", "true", "a1,a2,a4,a5,a6"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_missing_field(self):
        queries = [
            ["ADD_RULE", "r1", "age", "gt", "18", "allow"],
            ["EVALUATE", "name=alice"],
        ]
        expected = ["true", ""]
        self.assertEqual(expected, run_queries(self.engine, queries))


if __name__ == "__main__":
    unittest.main()
