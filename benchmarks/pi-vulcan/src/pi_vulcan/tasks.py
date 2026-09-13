from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from pi_vulcan.paths import TASKS_DIR


@dataclass(frozen=True)
class TestCmd:
    name: str
    cmd: str


@dataclass(frozen=True)
class Task:
    id: str
    directory: Path
    issue: str
    difficulty: str
    fail_to_pass: tuple[TestCmd, ...]
    pass_to_pass: tuple[TestCmd, ...]
    has_repo: bool
    gold_patch: Path | None
    verifier: Path | None

    def prompt(self) -> str:
        extra = (
            "Implement the fix in this workspace. Do not add or modify test files. "
            "Use the existing project files. Make the tests pass."
        )
        return f"{self.issue.strip()}\n\n---\n{extra}\n"


def _test_cmds(raw: object) -> tuple[TestCmd, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[TestCmd] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        cmd = str(item.get("cmd") or "")
        if name and cmd:
            out.append(TestCmd(name=name, cmd=cmd))
    return tuple(out)


def load_task(task_dir: Path) -> Task:
    meta = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
    tests = meta.get("tests") if isinstance(meta, dict) else None
    tests = tests if isinstance(tests, dict) else {}
    gold = task_dir / "gold_patch.diff"
    verifier = task_dir / "verifier.py"
    repo = task_dir / "repo"
    return Task(
        id=str(meta["id"]),
        directory=task_dir,
        issue=(task_dir / "issue.md").read_text(encoding="utf-8"),
        difficulty=str(meta.get("difficulty") or "unknown"),
        fail_to_pass=_test_cmds(tests.get("fail_to_pass")),
        pass_to_pass=_test_cmds(tests.get("pass_to_pass")),
        has_repo=repo.is_dir(),
        gold_patch=gold if gold.is_file() else None,
        verifier=verifier if verifier.is_file() else None,
    )


def list_tasks(tasks_dir: Path | None = None) -> list[Task]:
    root = tasks_dir or TASKS_DIR
    tasks = [
        load_task(p) for p in sorted(root.iterdir()) if (p / "metadata.json").is_file()
    ]
    if not tasks:
        raise FileNotFoundError(f"no tasks in {root}")
    return tasks


def copy_repo(task: Task, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    src = task.directory / "repo"
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    return dest


def overlay_hidden_tests(task: Task, workspace: Path) -> None:
    tests = task.directory / "tests"
    if not tests.is_dir():
        return
    for path in tests.rglob("*"):
        if path.is_file():
            target = workspace / path.relative_to(tests)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
