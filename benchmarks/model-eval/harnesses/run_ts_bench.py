#!/usr/bin/env python3
"""Run the proven pi phase-loop workflow against TS fixtures; score outcome + speed.

Workflow under test: orchestrator (Ornith, locked read,subagent, low thinking)
-> builder subagent (per builder.md) -> fresh verifier subagent (per verifier.md),
looping until PASS or 3 rounds. We score the FINAL outcome independently by
re-running each fixture's hidden gate, plus wall-clock and rounds-to-pass.
"""
import json, os, shutil, subprocess, time, sys
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_runs"
ORCH_PROMPT = Path.home() / ".pi/agent/prompts/orchestrator-phase-loop.md"
FIXTURES = ["roman", "lru", "bowling"]
ORCH = ("llama-gptoss", "gpt-oss-20b", "low")   # orchestrator bake-off: gpt-oss-20b
TIMEOUT = 1200   # 20 min/fixture; bounds a builder hang (e.g. Devstral on bowling)

def prep(fx):
    src = BASE / fx
    sb = SAND / fx
    if sb.exists():
        shutil.rmtree(sb)
    sb.mkdir(parents=True)
    # copy everything EXCEPT the reference solution (anti-cheat)
    for item in src.iterdir():
        if item.name == ".reference.ts":
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, sb / item.name)
    subprocess.run(["git", "init", "-q"], cwd=sb, check=False)
    pristine_test = (sb / "test" / f"{fx}.test.ts").read_text()
    return sb, pristine_test

def run(fx, sb):
    prompt = ORCH_PROMPT.read_text()
    cmd = ["pi", "-p", "--mode", "json",
           "--session-dir", str(sb / ".pisession"), "--session-id", "orch",
           "--provider", ORCH[0], "--model", ORCH[1], "--thinking", ORCH[2],
           "-t", "subagent", prompt]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=sb, capture_output=True, text=True, timeout=TIMEOUT)
        out, timed = (p.stdout or ""), False
    except subprocess.TimeoutExpired as e:
        raw = getattr(e, "stdout", "") or ""
        out = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
        timed = True
    wall = time.time() - t0
    (sb / "orch-out.json").write_text(out)
    return out, wall, timed

def rounds(out):
    b = v = 0
    for l in out.splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("type") == "tool_execution_start" and e.get("toolName") == "subagent":
            a = json.dumps(e.get("args", {})).lower()
            if '"agent": "builder"' in a or '"builder"' in a:
                b += 1
            if '"verifier"' in a:
                v += 1
    return b, v

def score(fx, sb, pristine_test):
    (sb / "test" / f"{fx}.test.ts").write_text(pristine_test)   # anti-tamper restore
    r = subprocess.run(["node", "--test", f"test/{fx}.test.ts"],
                       cwd=sb, capture_output=True, text=True, timeout=120)
    return r.returncode == 0

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"Workflow: orch={ORCH[1]}(low) / builder=builder.md / verifier=verifier.md")
    print(f"Fixtures: {', '.join(FIXTURES)}\n")
    for fx in FIXTURES:
        print(f"[{fx}] running phase loop ... ", end="", flush=True)
        sb, ptest = prep(fx)
        out, wall, timed = run(fx, sb)
        b, v = rounds(out)
        try:
            passed = score(fx, sb, ptest)
        except Exception as ex:
            passed = False
            print(f"(score err {ex}) ", end="")
        rows.append((fx, passed, timed, wall, b, v))
        flag = "TIMEOUT " if timed else ""
        print(f"{flag}{'PASS' if passed else 'FAIL'}  {wall:5.0f}s  "
              f"builds={b} verifies={v}")
    print("\n" + "=" * 72)
    print(f"  {'fixture':<10}{'outcome':>9}{'wall':>8}{'builds':>8}{'verifies':>10}")
    print("  " + "-" * 64)
    npass = 0
    for fx, passed, timed, wall, b, v in rows:
        npass += passed
        verdict = "TIMEOUT" if timed else ("PASS" if passed else "FAIL")
        print(f"  {fx:<10}{verdict:>9}{wall:>7.0f}s{b:>8}{v:>10}")
    print("  " + "-" * 64)
    print(f"  accuracy: {npass}/{len(rows)} phases passed   "
          f"total wall: {sum(r[3] for r in rows):.0f}s")
    print("=" * 72)

if __name__ == "__main__":
    main()
