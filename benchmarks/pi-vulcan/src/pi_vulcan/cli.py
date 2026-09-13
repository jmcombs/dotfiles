from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from pi_vulcan import __version__
from pi_vulcan.oracle import assert_task_oracle
from pi_vulcan.paths import RESULTS_DIR
from pi_vulcan.router import (
    load_model,
    model_loaded,
    normalize_router_base,
    router_up,
    start_launchd,
    wait_for_router,
)
from pi_vulcan.runner import run_pi
from pi_vulcan.tasks import list_tasks

app = typer.Typer(no_args_is_help=True, add_completion=False)
DEFAULT_MODEL = "qwen3.8-27b"


def _router_base() -> str:
    return normalize_router_base(
        os.environ.get("LLAMA_ROUTER_BASE") or os.environ.get("LLAMA_BASE_URL")
    )


@app.command("list")
def list_cmd() -> None:
    """List vendored tasks."""
    for task in list_tasks():
        grader = "tests" if task.fail_to_pass or task.pass_to_pass else "verifier"
        typer.echo(f"{task.id:<24} {task.difficulty:<8} {grader}")


@app.command("self-test")
def self_test_cmd() -> None:
    """Prove hidden tests fail on the stub and pass on the gold patch."""
    work_root = Path("/tmp/pi-vulcan-self-test")
    if work_root.exists():
        shutil.rmtree(work_root)
    failed = 0
    for task in list_tasks():
        work = work_root / task.id
        try:
            assert_task_oracle(task, work)
        except Exception as exc:
            typer.echo(f"FAIL {task.id}: {exc}")
            failed += 1
        else:
            typer.echo(f"PASS {task.id}")
    shutil.rmtree(work_root, ignore_errors=True)
    if failed:
        raise typer.Exit(1)
    typer.echo("self-test ok")


@app.command("run")
def run_cmd(
    model: Annotated[str, typer.Option(help="Router model alias")] = DEFAULT_MODEL,
    provider: Annotated[str, typer.Option()] = "local-llama",
    thinking: Annotated[str, typer.Option()] = "high",
    task: Annotated[
        str | None,
        typer.Option(help="Comma-separated task ids (default: all vendored)"),
    ] = None,
    timeout: Annotated[int, typer.Option(help="Seconds per task")] = 900,
    start_server: Annotated[
        bool,
        typer.Option(
            "--start-server",
            help="Kickstart Steward's llama.cpp launchd job",
        ),
    ] = False,
    keep_sandboxes: Annotated[bool, typer.Option("--keep-sandboxes")] = False,
) -> None:
    """Run vendored tasks through headless pi and grade with hidden tests."""
    wanted = {part.strip() for part in task.split(",")} if task else None
    tasks = [item for item in list_tasks() if wanted is None or item.id in wanted]
    if wanted is not None:
        missing = wanted - {item.id for item in tasks}
        if missing:
            typer.echo(f"unknown tasks: {', '.join(sorted(missing))}", err=True)
            raise typer.Exit(2)
    if not tasks:
        typer.echo("no tasks selected", err=True)
        raise typer.Exit(2)

    base = _router_base()
    typer.echo(f"Router:  {base}")
    typer.echo(f"Model:   {provider}/{model}  thinking={thinking}")
    if not router_up(base):
        if not start_server:
            typer.echo(
                f"llama.cpp router is not reachable at {base}.\n"
                "  Start it: /steward_dashboard  OR  pi-vulcan run --start-server",
                err=True,
            )
            raise typer.Exit(2)
        typer.echo("Starting com.llama.testbed via launchctl kickstart")
        start_launchd()
        wait_for_router(base)
    else:
        wait_for_router(base, timeout_s=5.0)

    if not model_loaded(base, model):
        typer.echo(f"Loading {model} …")
        load_model(base, model)
    typer.echo(f"Loaded:  {model}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    rows: list[dict] = []
    typer.echo(
        f"{'task':<24}{'pass':<6}{'func':>6}{'wall':>8}"
        f"{'turns':>7}{'tools':>7}{'err':>5}{'tok':>8}"
    )
    for item in tasks:
        result = run_pi(
            item,
            provider=provider,
            model=model,
            thinking=thinking,
            timeout_s=timeout,
        )
        flag = "PASS" if result.passed else ("TIME" if result.timed_out else "fail")
        typer.echo(
            f"{item.id:<24}{flag:<6}{result.functional:6.2f}"
            f"{result.wall_s:8.1f}{result.metrics.turns:7d}"
            f"{result.metrics.tool_calls:7d}{result.metrics.tool_errors:5d}"
            f"{result.metrics.tokens:8d}"
        )
        rows.append(
            {
                "task": item.id,
                "passed": result.passed,
                "functional": result.functional,
                "wall_s": round(result.wall_s, 1),
                "timed_out": result.timed_out,
                "turns": result.metrics.turns,
                "tool_calls": result.metrics.tool_calls,
                "tool_errors": result.metrics.tool_errors,
                "tokens": result.metrics.tokens,
                "tool_counts": result.metrics.tool_counts,
                "sandbox": str(result.sandbox),
                "jsonl": str(result.jsonl_path),
            }
        )
        if not keep_sandboxes:
            shutil.rmtree(result.sandbox, ignore_errors=True)

    report = {
        "version": __version__,
        "timestamp": stamp,
        "router": base,
        "provider": provider,
        "model": model,
        "thinking": thinking,
        "results": rows,
    }
    out = RESULTS_DIR / f"{model}-{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    npass = sum(1 for row in rows if row["passed"])
    typer.echo(f"{npass}/{len(rows)} passed  → {out}")
    raise typer.Exit(0 if npass == len(rows) else 1)
