# Rule Engine — Level 3: Priority & Conflict Resolution

Extend your rule engine with rule priorities and conflict resolution.

### New Concepts

- Each rule now has an optional **priority** (integer, default 0). Higher priority fires first.
- **Rule groups**: rules can be assigned to a named group. Within a group, only the highest-priority matching rule fires (first-match-wins).
- Rules without a group always fire if they match (no conflict resolution).

### New / Modified Operations

- `ADD_RULE name field operator value action priority group` — Priority and group are optional (default: `0` and `""` for no group).
- `ADD_COMPOUND_RULE name condition_json action priority group` — Same optional fields.
- `EVALUATE` now respects priority ordering and group conflict resolution.
  - Return actions in priority order (descending). For equal priority, sort alphabetically.
  - Within a group, only the highest-priority match fires.
- `LIST_GROUP group_name` — Return comma-separated rule names in the group sorted by priority (descending), or `""` if group doesn't exist.
