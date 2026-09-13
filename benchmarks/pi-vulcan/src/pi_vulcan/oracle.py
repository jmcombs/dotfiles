from __future__ import annotations

from pathlib import Path

from pi_vulcan.score import apply_gold_patch, grade_workspace
from pi_vulcan.tasks import Task, copy_repo


def assert_task_oracle(task: Task, work: Path) -> None:
    """Hidden tests must fail on the stub repo and pass after the gold patch."""
    copy_repo(task, work)
    before = grade_workspace(task, work)
    if before.passed:
        raise AssertionError(f"{task.id}: stub unexpectedly passes hidden tests")
    if task.gold_patch is not None:
        apply_gold_patch(task, work)
        after = grade_workspace(task, work)
        if not after.passed:
            failed = [r.name for r in after.fail_to_pass if not r.passed]
            failed += [r.name for r in after.pass_to_pass if not r.passed]
            raise AssertionError(f"{task.id}: gold patch did not pass ({failed})")
        return
    if task.id == "hello-world":
        (work / "hello.py").write_text(
            'print("hello from vulcanbench")\n', encoding="utf-8"
        )
        after = grade_workspace(task, work)
        if not after.passed:
            raise AssertionError(
                f"{task.id}: reference hello.py did not pass: {after.details}"
            )
        return
    raise AssertionError(f"{task.id}: no gold patch or hello-world oracle")
