"""Tool access policy by collaboration mode."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

from .modes import Mode


class ToolAction(str, Enum):
    READ_FILE = "read_file"
    READ_DESCRIPTION = "read_description"
    LOOKUP_CONCEPT = "lookup_concept"
    APPLY_PATCH = "apply_patch"
    EXECUTE_TESTS = "execute_tests"
    GET_CURRENT_CODE = "get_current_code"
    GET_RUN_HISTORY = "get_run_history"


class ToolPolicyViolation(PermissionError):
    """Raised when a tool call is attempted in a disallowed mode."""


class ToolPolicy:
    SHARED_ACTIONS: FrozenSet[ToolAction] = frozenset(
        {
            ToolAction.READ_FILE,
            ToolAction.READ_DESCRIPTION,
            ToolAction.LOOKUP_CONCEPT,
        }
    )
    BOT_ONLY_ACTIONS: FrozenSet[ToolAction] = frozenset(
        {
            ToolAction.APPLY_PATCH,
            ToolAction.EXECUTE_TESTS,
        }
    )
    HUMAN_ONLY_ACTIONS: FrozenSet[ToolAction] = frozenset(
        {
            ToolAction.GET_CURRENT_CODE,
            ToolAction.GET_RUN_HISTORY,
        }
    )

    @classmethod
    def allowed_actions(cls, mode: Mode) -> FrozenSet[ToolAction]:
        if mode == Mode.BOT_DRIVES:
            return cls.SHARED_ACTIONS | cls.BOT_ONLY_ACTIONS
        return cls.SHARED_ACTIONS | cls.HUMAN_ONLY_ACTIONS

    @classmethod
    def assert_allowed(cls, mode: Mode, action: ToolAction) -> None:
        if action not in cls.allowed_actions(mode):
            raise ToolPolicyViolation(
                f"Action '{action.value}' is disabled while in mode '{mode.value}'."
            )

