"""Agent core orchestrating modes, struggle detection, and tools."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from .backend_client import AssessmentBackendClient, BackendClientError
from .concept_lookup import ConceptLookup
from .hints import hint_for_signal
from .modes import Mode, ModeStateMachine
from .notion_logger import SessionJournal
from .policy import ToolAction, ToolPolicy
from .struggle_detector import StruggleDetector, StruggleSignal
from .workspace import QuestionWorkspace


class PairProgrammingVoiceBot:
    def __init__(
        self,
        *,
        workspace: QuestionWorkspace,
        question_name: str,
        backend_client: Optional[AssessmentBackendClient] = None,
        mode_state: Optional[ModeStateMachine] = None,
        struggle_detector: Optional[StruggleDetector] = None,
        concept_lookup: Optional[ConceptLookup] = None,
    ) -> None:
        self.workspace = workspace
        self.question_name = question_name
        self.backend_client = backend_client
        self.mode_state = mode_state or ModeStateMachine()
        self.struggle_detector = struggle_detector or StruggleDetector()
        self.concept_lookup = concept_lookup or ConceptLookup()
        self.run_history: List[Dict[str, object]] = []
        self.journal = SessionJournal(question_name=question_name)

    @property
    def mode(self) -> Mode:
        return self.mode_state.mode

    def set_mode(self, mode: Mode, trigger: str = "manual") -> None:
        transition = self.mode_state.set_mode(mode, trigger=trigger)
        if transition is not None:
            self.journal.log_mode_switch(
                previous=transition.previous.value,
                current=transition.current.value,
                trigger=transition.trigger,
                timestamp=time.time(),
            )

    def handle_voice_input(self, utterance: str, current_level: int) -> List[str]:
        responses: List[str] = []
        transition = self.mode_state.apply_voice_command(utterance)
        if transition:
            self.journal.log_mode_switch(
                previous=transition.previous.value,
                current=transition.current.value,
                trigger=transition.trigger,
                timestamp=time.time(),
            )
            if transition.current == Mode.BOT_DRIVES:
                responses.append("Taking over now. I will edit code and run tests.")
            else:
                responses.append("Your turn. I will watch quietly and help if you get stuck.")
            return responses

        if self.mode == Mode.HUMAN_DRIVES:
            signal = self.struggle_detector.on_user_message(utterance)
            if signal is not None:
                responses.append(self._respond_to_signal(signal, current_level))
        return responses

    def observe_code_update(
        self,
        code: str,
        *,
        current_level: int,
        now: Optional[float] = None,
    ) -> Optional[str]:
        if self.mode != Mode.HUMAN_DRIVES:
            return None
        signal = self.struggle_detector.on_code_update(code, now=now)
        if signal is None:
            return None
        return self._respond_to_signal(signal, current_level)

    def observe_run_result(
        self,
        *,
        exit_code: int,
        stderr: str,
        stage_index: int,
        visible_passed: int = 0,
        visible_total: int = 0,
        now: Optional[float] = None,
    ) -> Optional[str]:
        self.run_history.append(
            {
                "exit_code": exit_code,
                "stderr": stderr,
                "stage_index": stage_index,
                "visible_passed": visible_passed,
                "visible_total": visible_total,
            }
        )
        self.journal.log_test_result(stage_index, visible_passed, visible_total)

        if self.mode != Mode.HUMAN_DRIVES:
            return None
        signal = self.struggle_detector.on_run_result(
            exit_code=exit_code,
            stderr=stderr,
            stage_index=stage_index,
            now=now,
        )
        if signal is None:
            return None
        return self._respond_to_signal(signal, current_level=stage_index + 1)

    def periodic_check(
        self,
        *,
        current_level: int,
        tests_still_failing: bool,
        now: Optional[float] = None,
    ) -> Optional[str]:
        if self.mode != Mode.HUMAN_DRIVES:
            return None

        signal = self.struggle_detector.check_idle(
            tests_still_failing=tests_still_failing,
            now=now,
        )
        if signal is None:
            signal = self.struggle_detector.check_level_wall(
                current_level=current_level,
                now=now,
            )
        if signal is None:
            return None
        return self._respond_to_signal(signal, current_level=current_level)

    def read_file(self, path: str) -> str:
        ToolPolicy.assert_allowed(self.mode, ToolAction.READ_FILE)
        return self.workspace.read_file(path)

    def read_description(self, level: int = 1) -> str:
        ToolPolicy.assert_allowed(self.mode, ToolAction.READ_DESCRIPTION)
        return self.workspace.read_description(level=level)

    def lookup_concept(self, query: str) -> str:
        ToolPolicy.assert_allowed(self.mode, ToolAction.LOOKUP_CONCEPT)
        summary = self.concept_lookup.lookup(query)
        self.journal.log_lookup(query, summary)
        return summary

    def apply_patch(self, file_path: str, old_text: str, new_text: str) -> str:
        ToolPolicy.assert_allowed(self.mode, ToolAction.APPLY_PATCH)
        return self.workspace.apply_patch(file_path, old_text, new_text)

    def execute_tests(self, session_id: str, files: Dict[str, str]) -> Dict:
        ToolPolicy.assert_allowed(self.mode, ToolAction.EXECUTE_TESTS)
        if self.backend_client is None:
            raise BackendClientError("No assessment backend configured.")
        result = self.backend_client.execute_tests(session_id, self.question_name, files)
        return result

    def summarize_test_result(self, result: Dict) -> str:
        stage = result.get("stage", {})
        visible = result.get("visible", {})
        current_index = int(stage.get("current_index", 0))
        current_passed = bool(stage.get("current_passed", False))
        unlocked_next = bool(stage.get("unlocked_next", False))
        if current_passed:
            if unlocked_next:
                return (
                    f"Level {current_index + 1} passed. "
                    f"Unlocking Level {current_index + 2}."
                )
            return "All levels complete."
        return (
            f"Level {current_index + 1}: "
            f"{visible.get('passed', 0)}/{visible.get('total', 0)} visible tests passing."
        )

    def get_current_code(self, file_path: str = "ruleengine.py") -> str:
        ToolPolicy.assert_allowed(self.mode, ToolAction.GET_CURRENT_CODE)
        return self.workspace.get_current_code(file_path)

    def get_run_history(self) -> List[Dict[str, object]]:
        ToolPolicy.assert_allowed(self.mode, ToolAction.GET_RUN_HISTORY)
        return list(self.run_history)

    def save_session_journal(self, output_path: str) -> None:
        self.journal.set_final_code(self.workspace.get_current_code("ruleengine.py"))
        self.journal.save(output_path)

    def _respond_to_signal(self, signal: StruggleSignal, current_level: int) -> str:
        self.journal.log_struggle(signal.kind, signal.timestamp, signal.context)
        return hint_for_signal(signal, current_level=current_level)

