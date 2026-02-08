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
        elif command == "EVALUATE":
            timestamp = query[2] if len(query) > 2 else ""
            results.append(engine.evaluate(query[1], timestamp))
        elif command == "LIST_GROUP":
            results.append(engine.list_group(query[1]))
    return results


class Level3PriorityAndGroupsTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()

    def test_priority_ordering(self):
        queries = [
            ["ADD_RULE", "low", "age", "gte", "18", "allow", "1", ""],
            ["ADD_RULE", "high", "age", "gte", "18", "vip_allow", "10", ""],
            ["ADD_RULE", "mid", "age", "gte", "18", "standard", "5", ""],
            ["EVALUATE", "age=25"],
        ]
        # priority desc: vip_allow(10), standard(5), allow(1)
        expected = ["true", "true", "true", "vip_allow,standard,allow"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_same_priority_alpha_sort(self):
        queries = [
            ["ADD_RULE", "r_b", "x", "eq", "1", "beta", "5", ""],
            ["ADD_RULE", "r_a", "x", "eq", "1", "alpha", "5", ""],
            ["ADD_RULE", "r_c", "x", "eq", "1", "gamma", "5", ""],
            ["EVALUATE", "x=1"],
        ]
        # same priority → alphabetical by action
        expected = ["true", "true", "true", "alpha,beta,gamma"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_group_first_match_wins(self):
        queries = [
            ["ADD_RULE", "strict", "age", "gte", "21", "full_access", "10", "access_level"],
            ["ADD_RULE", "relaxed", "age", "gte", "18", "limited_access", "5", "access_level"],
            ["ADD_RULE", "child", "age", "lt", "18", "no_access", "1", "access_level"],
            ["EVALUATE", "age=25"],
            ["EVALUATE", "age=19"],
            ["EVALUATE", "age=10"],
        ]
        # group: only highest priority match fires
        expected = ["true", "true", "true", "full_access", "limited_access", "no_access"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_group_with_ungrouped(self):
        queries = [
            ["ADD_RULE", "grouped_high", "x", "eq", "1", "g_high", "10", "grp"],
            ["ADD_RULE", "grouped_low", "x", "eq", "1", "g_low", "1", "grp"],
            ["ADD_RULE", "free1", "x", "eq", "1", "free_a", "5", ""],
            ["ADD_RULE", "free2", "x", "eq", "1", "free_b", "3", ""],
            ["EVALUATE", "x=1"],
        ]
        # grouped: only g_high fires. ungrouped: both fire. ordered by priority desc.
        expected = ["true", "true", "true", "true", "g_high,free_a,free_b"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_list_group(self):
        queries = [
            ["ADD_RULE", "r1", "x", "eq", "1", "a1", "5", "mygroup"],
            ["ADD_RULE", "r2", "x", "eq", "1", "a2", "10", "mygroup"],
            ["ADD_RULE", "r3", "x", "eq", "1", "a3", "1", "mygroup"],
            ["LIST_GROUP", "mygroup"],
            ["LIST_GROUP", "nonexistent"],
        ]
        expected = ["true", "true", "true", "r2,r1,r3", ""]
        self.assertEqual(expected, run_queries(self.engine, queries))


if __name__ == "__main__":
    unittest.main()
