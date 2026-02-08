"""Struggle detector for human_drives mode."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StruggleSignal:
    kind: str
    timestamp: float
    context: Dict[str, object] = field(default_factory=dict)


class StruggleDetector:
    def __init__(
        self,
        idle_threshold_seconds: int = 30,
        level_wall_seconds: int = 300,
        backtrack_ratio: float = 0.2,
        nudge_cooldown: int = 60,
    ) -> None:
        self.idle_threshold_seconds = idle_threshold_seconds
        self.level_wall_seconds = level_wall_seconds
        self.backtrack_ratio = backtrack_ratio
        self.nudge_cooldown = nudge_cooldown

        self.last_edit_time: Optional[float] = None
        self.run_results: List[tuple[int, str, int]] = []
        self.code_snapshots: List[str] = []
        self.level_start_time: Dict[int, float] = {}
        self._last_signal_time: float = -math.inf

    @staticmethod
    def _now(now: Optional[float]) -> float:
        return time.time() if now is None else now

    def _emit(self, kind: str, now: float, **context: object) -> Optional[StruggleSignal]:
        if now - self._last_signal_time < self.nudge_cooldown:
            return None
        self._last_signal_time = now
        return StruggleSignal(kind=kind, timestamp=now, context=context)

    def on_code_update(self, code: str, now: Optional[float] = None) -> Optional[StruggleSignal]:
        ts = self._now(now)
        signal = None
        if self.code_snapshots:
            previous = self.code_snapshots[-1]
            threshold = int(len(previous) * (1 - self.backtrack_ratio))
            if len(code) < threshold:
                signal = self._emit(
                    "backtrack",
                    ts,
                    previous_size=len(previous),
                    current_size=len(code),
                )
        self.code_snapshots.append(code)
        self.last_edit_time = ts
        return signal

    def on_run_result(
        self,
        exit_code: int,
        stderr: str,
        stage_index: int,
        now: Optional[float] = None,
    ) -> Optional[StruggleSignal]:
        ts = self._now(now)
        digest = hashlib.md5(stderr.encode("utf-8")).hexdigest()
        self.run_results.append((exit_code, digest, stage_index))
        if (
            len(self.run_results) >= 2
            and self.run_results[-1][:2] == self.run_results[-2][:2]
            and self.run_results[-1][0] != 0
        ):
            return self._emit(
                "repeated_failure",
                ts,
                stage_index=stage_index,
                exit_code=exit_code,
            )
        return None

    def on_level_start(self, level: int, now: Optional[float] = None) -> None:
        self.level_start_time[level] = self._now(now)

    def on_user_message(self, message: str, now: Optional[float] = None) -> Optional[StruggleSignal]:
        ts = self._now(now)
        normalized = message.lower()
        help_markers = ("help", "stuck", "hint", "what should i do", "not sure")
        if any(marker in normalized for marker in help_markers):
            return self._emit("explicit_ask", ts, message=message)
        return None

    def check_idle(
        self,
        *,
        tests_still_failing: bool,
        now: Optional[float] = None,
    ) -> Optional[StruggleSignal]:
        ts = self._now(now)
        if not tests_still_failing or self.last_edit_time is None:
            return None
        if ts - self.last_edit_time >= self.idle_threshold_seconds:
            return self._emit(
                "long_pause",
                ts,
                seconds=int(ts - self.last_edit_time),
            )
        return None

    def check_level_wall(self, current_level: int, now: Optional[float] = None) -> Optional[StruggleSignal]:
        ts = self._now(now)
        started = self.level_start_time.get(current_level)
        if started is None:
            return None
        if ts - started >= self.level_wall_seconds:
            return self._emit(
                "level_wall",
                ts,
                level=current_level,
                seconds=int(ts - started),
            )
        return None

