from pathlib import Path

from pi_vulcan.paths import TASKS_DIR
from pi_vulcan.runner import build_pi_command
from pi_vulcan.tasks import list_tasks, load_task


def test_prompt_does_not_include_hidden_tests() -> None:
    for task in list_tasks():
        prompt = task.prompt()
        assert "fail_to_pass" not in prompt
        assert "gold_patch" not in prompt
        hidden = task.directory / "tests"
        if hidden.is_dir():
            for path in hidden.rglob("*.py"):
                assert path.read_text(encoding="utf-8") not in prompt


def test_pi_command_is_headless_json_and_stripped() -> None:
    cmd = build_pi_command(
        provider="local-llama",
        model="qwen3.8-27b",
        thinking="high",
        prompt="do the task",
        session_dir=Path("/tmp/sess"),
    )
    assert cmd[:4] == ["pi", "-p", "--mode", "json"]
    assert "--no-extensions" not in cmd
    assert "--offline" not in cmd
    assert cmd[cmd.index("--api-key") + 1] == "local"
    assert "read,bash,edit,write" in cmd
    assert cmd[-1] == "do the task"


def test_load_hello_world() -> None:
    task = load_task(TASKS_DIR / "hello-world")
    assert task.verifier is not None
    assert not task.fail_to_pass
