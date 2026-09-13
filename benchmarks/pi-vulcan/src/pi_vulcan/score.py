from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pi_vulcan.tasks import Task, TestCmd, overlay_hidden_tests


@dataclass(frozen=True)
class CmdResult:
    name: str
    cmd: str
    passed: bool
    output: str


@dataclass(frozen=True)
class Grade:
    functional: float
    passed: bool
    fail_to_pass: tuple[CmdResult, ...]
    pass_to_pass: tuple[CmdResult, ...]
    details: tuple[str, ...]


def _normalize_cmd(cmd: str) -> str:
    if cmd.startswith("python "):
        return f"{sys.executable} {cmd[7:]}"
    return cmd


def _run_shell(cmd: str, cwd: Path, timeout_s: int) -> CmdResult:
    proc = subprocess.run(
        _normalize_cmd(cmd),
        cwd=cwd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    output = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    return CmdResult(name=cmd, cmd=cmd, passed=proc.returncode == 0, output=output)


def _run_named(item: TestCmd, cwd: Path, timeout_s: int) -> CmdResult:
    result = _run_shell(item.cmd, cwd, timeout_s)
    return CmdResult(
        name=item.name, cmd=item.cmd, passed=result.passed, output=result.output
    )


def _run_verifier(task: Task, workspace: Path, timeout_s: int) -> Grade:
    assert task.verifier is not None
    proc = subprocess.run(
        [sys.executable, str(task.verifier)],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    details: list[str] = []
    functional = 0.0
    raw = (proc.stdout or "").strip().splitlines()
    if raw:
        try:
            payload = json.loads(raw[-1])
            if isinstance(payload, dict):
                functional = float(payload.get("functional") or 0.0)
                extra = payload.get("details") or []
                if isinstance(extra, list):
                    details = [str(x) for x in extra]
        except (json.JSONDecodeError, TypeError, ValueError):
            details.append((proc.stdout or proc.stderr or "")[-500:])
    if proc.returncode != 0 and functional >= 1.0:
        functional = 0.0
        details.append(f"verifier exit {proc.returncode}")
    passed = functional >= 1.0
    return Grade(
        functional=functional,
        passed=passed,
        fail_to_pass=(),
        pass_to_pass=(),
        details=tuple(details),
    )


def grade_workspace(task: Task, workspace: Path, timeout_s: int = 120) -> Grade:
    overlay_hidden_tests(task, workspace)
    if task.fail_to_pass or task.pass_to_pass:
        ftp = tuple(
            _run_named(item, workspace, timeout_s) for item in task.fail_to_pass
        )
        ptp = tuple(
            _run_named(item, workspace, timeout_s) for item in task.pass_to_pass
        )
        if ptp and any(not item.passed for item in ptp):
            functional = 0.0
        elif ftp:
            functional = sum(1 for item in ftp if item.passed) / len(ftp)
        else:
            functional = 1.0 if all(item.passed for item in ptp) else 0.0
        return Grade(
            functional=functional,
            passed=functional >= 1.0,
            fail_to_pass=ftp,
            pass_to_pass=ptp,
            details=(),
        )
    if task.verifier is not None:
        return _run_verifier(task, workspace, timeout_s)
    raise ValueError(f"task {task.id} has no tests and no verifier")


def apply_gold_patch(task: Task, workspace: Path) -> None:
    if task.gold_patch is None:
        raise ValueError(f"task {task.id} has no gold_patch.diff")
    proc = subprocess.run(
        ["git", "apply", str(task.gold_patch)],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "git apply failed")
