# Rule Engine

Your task is to implement a rule engine that evaluates conditions against data records and fires matching actions. The engine processes rules defined as structured objects with conditions and actions.

A **data record** is a dictionary mapping string field names to string values (e.g., `{"age": "25", "role": "admin"}`).

A **rule** has a name, a condition, and an action string. When a record satisfies the condition, the rule "fires" and its action is returned.

## Level 1 — Basic Rules

Implement a rule engine that supports:

- **Adding rules** with simple conditions: a single field, operator (`eq`, `neq`, `gt`, `lt`, `gte`, `lte`), and a comparison value.
- **Evaluating** a data record against all rules, returning the list of fired action strings.
- **Removing rules** by name.
- Numeric comparisons use integer parsing. If a field is missing from the record, the condition does not match.

### Operations

- `ADD_RULE name field operator value action` — Add a rule. Return `"true"` if added, `"false"` if a rule with that name already exists.
- `EVALUATE field1=value1,field2=value2,...` — Evaluate a record against all rules. Return comma-separated fired actions sorted alphabetically, or `""` if none fire.
- `REMOVE_RULE name` — Remove a rule. Return `"true"` if removed, `"false"` if not found.
