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
    return results


class Level2CompoundConditionsTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()

    def test_and_condition(self):
        queries = [
            ["ADD_COMPOUND_RULE", "adult_admin",
             '{"and": [{"field": "age", "op": "gte", "value": "18"}, {"field": "role", "op": "eq", "value": "admin"}]}',
             "grant_admin"],
            ["EVALUATE", "age=25,role=admin"],
            ["EVALUATE", "age=15,role=admin"],
            ["EVALUATE", "age=25,role=user"],
        ]
        expected = ["true", "grant_admin", "", ""]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_or_condition(self):
        queries = [
            ["ADD_COMPOUND_RULE", "special_access",
             '{"or": [{"field": "role", "op": "eq", "value": "admin"}, {"field": "role", "op": "eq", "value": "moderator"}]}',
             "allow_dashboard"],
            ["EVALUATE", "role=admin"],
            ["EVALUATE", "role=moderator"],
            ["EVALUATE", "role=user"],
        ]
        expected = ["true", "allow_dashboard", "allow_dashboard", ""]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_nested_conditions(self):
        queries = [
            ["ADD_COMPOUND_RULE", "complex_rule",
             '{"and": [{"field": "age", "op": "gte", "value": "18"}, {"or": [{"field": "role", "op": "eq", "value": "admin"}, {"field": "level", "op": "gt", "value": "5"}]}]}',
             "advanced_access"],
            ["EVALUATE", "age=25,role=user,level=10"],
            ["EVALUATE", "age=25,role=admin,level=1"],
            ["EVALUATE", "age=15,role=admin,level=10"],
        ]
        expected = ["true", "advanced_access", "advanced_access", ""]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_match_count(self):
        queries = [
            ["ADD_RULE", "r1", "age", "gte", "18", "a1"],
            ["ADD_RULE", "r2", "role", "eq", "admin", "a2"],
            ["ADD_COMPOUND_RULE", "r3",
             '{"and": [{"field": "age", "op": "gte", "value": "21"}, {"field": "role", "op": "eq", "value": "admin"}]}',
             "a3"],
            ["MATCH_COUNT", "age=25,role=admin"],
            ["MATCH_COUNT", "age=19,role=user"],
        ]
        expected = ["true", "true", "true", "3", "1"]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_mixed_simple_and_compound(self):
        queries = [
            ["ADD_RULE", "simple1", "score", "gt", "80", "honor_roll"],
            ["ADD_COMPOUND_RULE", "compound1",
             '{"and": [{"field": "score", "op": "gt", "value": "90"}, {"field": "attendance", "op": "gte", "value": "95"}]}',
             "scholarship"],
            ["EVALUATE", "score=95,attendance=98"],
            ["EVALUATE", "score=85,attendance=98"],
        ]
        expected = ["true", "true", "honor_roll,scholarship", "honor_roll"]
        self.assertEqual(expected, run_queries(self.engine, queries))


if __name__ == "__main__":
    unittest.main()
