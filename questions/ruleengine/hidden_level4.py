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
        elif command == "HISTORY":
            results.append(engine.history(query[1]))
        elif command == "TOP_RULES":
            results.append(engine.top_rules(query[1]))
        elif command == "SNAPSHOT":
            results.append(engine.snapshot(query[1]))
        elif command == "RESTORE":
            results.append(engine.restore(query[1]))
    return results


class Level4AuditAndSnapshotsTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()

    def test_timestamped_evaluation_and_history(self):
        queries = [
            ["ADD_RULE", "r1", "age", "gte", "18", "allow"],
            ["ADD_RULE", "r2", "role", "eq", "admin", "admin_access"],
            ["EVALUATE", "age=25,role=admin", "100"],
            ["EVALUATE", "age=25,role=user", "200"],
            ["EVALUATE", "age=15,role=admin", "300"],
            ["HISTORY", "r1"],
            ["HISTORY", "r2"],
        ]
        expected = [
            "true", "true",
            "admin_access,allow",  # both fire at t=100
            "allow",               # only r1 at t=200
            "admin_access",        # only r2 at t=300
            "100,200",             # r1 fired at 100, 200
            "100,300",             # r2 fired at 100, 300
        ]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_top_rules(self):
        queries = [
            ["ADD_RULE", "r1", "x", "eq", "1", "a1"],
            ["ADD_RULE", "r2", "x", "eq", "1", "a2"],
            ["ADD_RULE", "r3", "y", "eq", "1", "a3"],
            ["EVALUATE", "x=1,y=1", "1"],
            ["EVALUATE", "x=1", "2"],
            ["EVALUATE", "x=1,y=1", "3"],
            ["TOP_RULES", "2"],
            ["TOP_RULES", "10"],
        ]
        expected = [
            "true", "true", "true",
            "a1,a2,a3",  # all fire
            "a1,a2",     # r1, r2 fire
            "a1,a2,a3",  # all fire
            "r1,r2",     # r1=3, r2=3, r3=2 → top 2
            "r1,r2,r3",  # all of them
        ]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_snapshot_and_restore(self):
        queries = [
            ["ADD_RULE", "r1", "x", "eq", "1", "a1"],
            ["ADD_RULE", "r2", "y", "eq", "1", "a2"],
            ["SNAPSHOT", "100"],
            ["ADD_RULE", "r3", "z", "eq", "1", "a3"],
            ["REMOVE_RULE", "r1"],
            ["EVALUATE", "x=1,y=1,z=1", "200"],
            ["RESTORE", "100"],
            ["EVALUATE", "x=1,y=1,z=1", "300"],
            ["RESTORE", "999"],  # doesn't exist
        ]
        expected = [
            "true", "true",
            "2",             # snapshot has 2 rules
            "true",          # r3 added
            "true",          # r1 removed
            "a2,a3",         # r2 and r3 fire (r1 gone)
            "true",          # restore to snapshot
            "a1,a2",         # r1 and r2 back (r3 gone)
            "false",         # no snapshot at 999
        ]
        self.assertEqual(expected, run_queries(self.engine, queries))

    def test_history_survives_restore(self):
        queries = [
            ["ADD_RULE", "r1", "x", "eq", "1", "a1"],
            ["EVALUATE", "x=1", "10"],
            ["SNAPSHOT", "20"],
            ["REMOVE_RULE", "r1"],
            ["RESTORE", "20"],
            ["EVALUATE", "x=1", "30"],
            ["HISTORY", "r1"],
        ]
        expected = [
            "true",
            "a1",       # fires at t=10
            "1",        # snapshot: 1 rule
            "true",     # removed
            "true",     # restored
            "a1",       # fires again at t=30
            "10,30",    # history preserved across restore
        ]
        self.assertEqual(expected, run_queries(self.engine, queries))


if __name__ == "__main__":
    unittest.main()
