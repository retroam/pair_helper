# Rule Engine — Level 2: Compound Conditions

Extend your rule engine to support compound conditions using AND/OR groups.

A **compound condition** is either:
- A **simple condition**: `{"field": "age", "op": "gt", "value": "18"}`
- An **AND group**: `{"and": [condition, condition, ...]}`
- An **OR group**: `{"or": [condition, condition, ...]}`

Conditions can be nested arbitrarily.

### New Operations

- `ADD_COMPOUND_RULE name condition_json action` — Add a rule with a compound condition (JSON string). Return `"true"` if added, `"false"` if name exists.
- `EVALUATE` now also evaluates compound rules.
- `MATCH_COUNT field1=value1,...` — Return the number of rules that match the record as a string.

### Example

```json
{"and": [{"field": "age", "op": "gte", "value": "18"}, {"field": "role", "op": "eq", "value": "admin"}]}
```
This fires only if age >= 18 AND role == "admin".
