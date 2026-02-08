import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import (
    CPU_LIMIT,
    DOCKER_IMAGE,
    MEMORY_LIMIT,
    PIDS_LIMIT,
    TIMEOUT_SECONDS,
    TMPFS_SIZE,
)
from .questions import Stage, load_question_config, materialize_question


class ExecutionError(Exception):
    pass


def parse_unittest_output(output: str) -> Tuple[int, int]:
    """
    Roughly parse unittest stdout to extract total and passed test counts.
    """
    total = 0
    failures = 0
    errors = 0
    ran_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    if ran_match:
        total = int(ran_match.group(1))
    fail_match = re.search(r"FAILED\s+\(([^)]+)\)", output)
    if fail_match:
        parts = [p.strip() for p in fail_match.group(1).split(",")]
        for part in parts:
            if part.startswith("failures="):
                failures = int(part.split("=")[1])
            elif part.startswith("errors="):
                errors = int(part.split("=")[1])
    passed = max(0, total - failures - errors)
    return passed, total


def docker_command(workdir: Path, command: Tuple[str, ...]) -> Tuple[int, str, str]:
    """
    Run a command inside a resource-constrained Docker container.
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        CPU_LIMIT,
        "--memory",
        MEMORY_LIMIT,
        "--pids-limit",
        PIDS_LIMIT,
        "--tmpfs",
        f"/tmp:rw,size={TMPFS_SIZE}",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-v",
        f"{workdir}:/workspace:ro",
        "-w",
        "/workspace",
        DOCKER_IMAGE,
        *command,
    ]
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            text=True,
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        raise ExecutionError(f"Execution timed out after {TIMEOUT_SECONDS}s: {exc}") from exc
    except FileNotFoundError as exc:
        raise ExecutionError("Docker is not installed or not on PATH") from exc
    except Exception as exc:
        raise ExecutionError(f"Execution failed: {exc}") from exc


def run_suite(workdir: Path, target: str) -> Dict[str, Optional[int]]:
    code, out, err = docker_command(workdir, ("python", target))
    passed, total = parse_unittest_output(out + "\n" + err)
    return {
        "exit_code": code,
        "output": out + err,
        "passed": passed,
        "total": total,
    }


def run_stage_tests(workdir: Path, stage: Stage) -> Dict[str, object]:
    visible_pass = 0
    visible_total = 0
    hidden_pass = 0
    hidden_total = 0
    visible_outputs: List[str] = []
    all_exited_zero = True

    for test_file in stage.visible_tests:
        result = run_suite(workdir, test_file)
        visible_pass += result["passed"] or 0
        visible_total += result["total"] or 0
        visible_outputs.append(result["output"])
        if result.get("exit_code", 0) != 0:
            all_exited_zero = False

    for test_file in stage.hidden_tests:
        result = run_suite(workdir, test_file)
        hidden_pass += result["passed"] or 0
        hidden_total += result["total"] or 0
        if result.get("exit_code", 0) != 0:
            all_exited_zero = False

    stage_passed = (visible_pass == visible_total) and (hidden_pass == hidden_total) and all_exited_zero
    return {
        "visible_pass": visible_pass,
        "visible_total": visible_total,
        "hidden_pass": hidden_pass,
        "hidden_total": hidden_total,
        "output": "\n".join([o for o in visible_outputs if o]),
        "passed": stage_passed,
    }


def run_code(question_name: str, user_files: Dict[str, str], stage_index: int) -> Dict[str, object]:
    """
    Materialize a temp workspace, run tests through the provided stage_index (inclusive),
    and return structured results with stage progression info.
    """
    cfg = load_question_config(question_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        cfg, _ = materialize_question(question_name, workdir, user_files)

        max_stage = min(stage_index, len(cfg.stages) - 1)
        visible_pass_total = 0
        visible_total_total = 0
        hidden_pass_total = 0
        hidden_total_total = 0

        stage_results: List[Dict[str, object]] = []
        for idx, stage in enumerate(cfg.stages[: max_stage + 1]):
            result = run_stage_tests(workdir, stage)
            stage_results.append(result)
            visible_pass_total += result["visible_pass"]
            visible_total_total += result["visible_total"]
            hidden_pass_total += result["hidden_pass"]
            hidden_total_total += result["hidden_total"]

        current_stage_passed = stage_results[-1]["passed"] if stage_results else False
        all_passed_so_far = all(r["passed"] for r in stage_results) if stage_results else False
        unlocked_next = all_passed_so_far and (max_stage + 1 < len(cfg.stages))

        # Score is based on stage progression: each completed stage is worth (100 / total_stages)%
        total_stages = len(cfg.stages)
        stages_passed = sum(1 for r in stage_results if r["passed"])
        final_score = (stages_passed / total_stages) * 100.0 if total_stages > 0 else 0.0

        return {
            "visible": {
                "passed": stage_results[-1]["visible_pass"] if stage_results else 0,
                "total": stage_results[-1]["visible_total"] if stage_results else 0,
                "output": stage_results[-1]["output"] if stage_results else "",
            },
            "hidden": {
                "passed": stage_results[-1]["hidden_pass"] if stage_results else 0,
                "total": stage_results[-1]["hidden_total"] if stage_results else 0,
            },
            "final_score": final_score,
            "stage": {
                "current_index": max_stage,
                "total_stages": len(cfg.stages),
                "current_passed": current_stage_passed,
                "unlocked_next": unlocked_next,
                "name": cfg.stages[max_stage].name if cfg.stages else "",
            },
        }
