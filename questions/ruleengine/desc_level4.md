# Rule Engine — Level 4: Audit Trail & Snapshots

Extend your rule engine with an audit trail and snapshot/restore functionality.

### New Concepts

- Every `EVALUATE` call is now timestamped (integer, strictly increasing).
- The engine maintains a **history** of all evaluations: which rules fired, for which record, at what timestamp.
- **Snapshots** save the current rule set at a given timestamp. **Restore** rolls back to a snapshot.

### New Operations

- `EVALUATE timestamp field1=value1,...` — Evaluate with a timestamp. Return fired actions as before.
- `HISTORY rule_name` — Return comma-separated timestamps where this rule fired (chronological), or `""` if never fired.
- `TOP_RULES n` — Return the top N most-frequently-fired rule names, sorted by fire count (descending), then alphabetically. Comma-separated.
- `SNAPSHOT timestamp` — Save current rule set. Return the number of rules as a string.
- `RESTORE timestamp` — Restore rule set from snapshot. Return `"true"` if snapshot exists, `"false"` otherwise. History is preserved (not rolled back).
