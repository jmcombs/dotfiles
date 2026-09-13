from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from pi_vulcan.events import RunMetrics, metrics_from_events, parse_jsonl
from pi_vulcan.paths import SANDBOX_DIR
from pi_vulcan.score import Grade, grade_workspace
from pi_vulcan.tasks import Task, copy_repo


@dataclass(frozen=True)
class TaskRun:
    task_id: str
    passed: bool
    functional: float
    wall_s: float
    timed_out: bool
    metrics: RunMetrics
    grade: Grade
    sandbox: Path
    jsonl_path: Path
    stderr_path: Path


def build_pi_command(
    *,
    provider: str,
    model: str,
    thinking: str,
    prompt: str,
    session_dir: Path,
) -> list[str]:
    return [
        "pi",
        "-p",
        "--mode",
        "json",
        "--provider",
        provider,
        "--model",
        model,
        "--api-key",
        "local",
        "--thinking",
        thinking,
        "-t",
        "read,bash,edit,write",
        "--no-skills",
        "--no-prompt-templates",
        "--approve",
        "--session-dir",
        str(session_dir),
        "--session-id",
        "task",
        prompt,
    ]


def run_pi(
    task: Task,
    *,
    provider: str,
    model: str,
    thinking: str,
    timeout_s: int,
    env: dict[str, str] | None = None,
) -> TaskRun:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix=f"{task.id}-", dir=SANDBOX_DIR))
    copy_repo(task, sandbox)
    session_dir = sandbox / ".pi-session"
    session_dir.mkdir()
    jsonl_path = sandbox / "pi.jsonl"
    stderr_path = sandbox / "pi.stderr"
    cmd = build_pi_command(
        provider=provider,
        model=model,
        thinking=thinking,
        prompt=task.prompt(),
        session_dir=session_dir,
    )
    merged_env = {**os.environ, **(env or {})}
    t0 = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=sandbox,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=merged_env,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = (
            exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
    wall_s = time.perf_counter() - t0
    jsonl_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    metrics = metrics_from_events(parse_jsonl(stdout))
    grade = grade_workspace(task, sandbox)
    return TaskRun(
        task_id=task.id,
        passed=grade.passed and not timed_out,
        functional=grade.functional,
        wall_s=wall_s,
        timed_out=timed_out,
        metrics=metrics,
        grade=grade,
        sandbox=sandbox,
        jsonl_path=jsonl_path,
        stderr_path=stderr_path,
    )
