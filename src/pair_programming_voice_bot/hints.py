"""Signal-to-hint mapping used in human_drives mode."""

from __future__ import annotations

from .struggle_detector import StruggleSignal


def hint_for_signal(signal: StruggleSignal, current_level: int) -> str:
    if signal.kind == "long_pause":
        if current_level <= 2:
            return (
                "Try evaluating conditions in small steps. "
                "For AND/OR logic, a recursive helper usually keeps this clean."
            )
        return (
            "You can break this into two passes: first find all matches, "
            "then apply ordering/group conflict rules."
        )

    if signal.kind == "repeated_failure":
        if current_level == 3:
            return (
                "This level usually fails on ordering. Sort by priority descending, "
                "then alphabetically for ties."
            )
        if current_level >= 4:
            return (
                "Double-check audit behavior: history should keep timestamps across restore, "
                "while only the rule set rolls back."
            )
        return (
            "Looks like the same failure repeated. Verify missing-field handling and operator dispatch."
        )

    if signal.kind == "backtrack":
        return (
            "No problem. Rebuild one small helper first, then connect it back. "
            "For grouped rules, think first-match-wins per group."
        )

    if signal.kind == "level_wall":
        return (
            "You have been on this level for a while. "
            "Want a focused hint on the exact failing assertion?"
        )

    if signal.kind == "explicit_ask":
        return (
            "Start with one failing test and implement only what that assertion needs. "
            "Then rerun and iterate."
        )

    return "Keep going. If you want, I can suggest the next smallest implementation step."

