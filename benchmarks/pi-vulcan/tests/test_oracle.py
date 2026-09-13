from pathlib import Path

from pi_vulcan.oracle import assert_task_oracle
from pi_vulcan.tasks import list_tasks


def test_vendored_oracles_fail_then_pass(tmp_path: Path) -> None:
    tasks = list_tasks()
    assert {t.id for t in tasks} == {
        "hello-world",
        "py-topo-sort-cycle",
        "py-ttl-cache-expiry",
    }
    for task in tasks:
        assert_task_oracle(task, tmp_path / task.id)
