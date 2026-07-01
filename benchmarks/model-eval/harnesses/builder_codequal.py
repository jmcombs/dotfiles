#!/usr/bin/env python3
"""Builder code-quality bake-off (builder-only, no verifier loop).

Measures the actual builder-seat question: which model writes correct code as a
builder. Orchestrator (gpt-oss) delegates to the builder ONCE; we then score the
resulting code against the hidden gate. No verify loop -> no git-discipline noise,
no remediation churn. Reuses the hardened infra from builder_bench2 (model-manager,
fixed nested-session metrics, orch-out.json watchdog, incremental save).
"""
import json, glob, os, re, shutil, signal, subprocess, time, importlib.util
from pathlib import Path

BB = importlib.util.spec_from_file_location("bb", str(Path(__file__).parent/"builder_bench2.py"))
bb = importlib.util.module_from_spec(BB); BB.loader.exec_module(bb)

BASE = bb.BASE
SAND = BASE / "_codequal"
RESULTS = BASE / "_codequal_results.json"
FIXTURES = ["roman", "lru", "bowling"]
HARD_TIMEOUT = 900
STALL_LIMIT = 240
POLL = 10

ORCH_PROMPT = (
  'You are a dispatcher. Your ONLY tool is subagent. Call it EXACTLY ONCE with '
  'agent:"builder" and task:"Implement Phase 1 of PLAN.md: do its Actionable TODOs '
  'and prove its Testing Gate by running the exact command. No branch/PR/commit is '
  'needed in this environment; focus on correct code. Then stop." '
  'After the builder returns its report, STOP immediately. Do NOT call any other '
  'agent, do NOT verify, do NOT call builder again.')

def ensure_models_builderonly(builder_server):
    bb.start_server("gptoss")             # orchestrator (also serves gpt-oss-as-builder)
    bb.stop_server("ornith")              # no verifier needed
    # local builder servers: start the needed one, stop the rest (gptoss handled above)
    for b in bb.LOCAL_BUILDER_SERVERS:
        if b == builder_server: bb.start_server(b)
        else: bb.stop_server(b)

def prep(label, fx):
    sb = SAND / label / fx
    if sb.exists(): shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for it in (BASE/fx).iterdir():
        if it.name == ".reference.ts": continue
        (shutil.copytree if it.is_dir() else shutil.copy2)(it, sb/it.name)
    return sb, (sb/"test"/f"{fx}.test.ts").read_text()

def run_phase(sb):
    cmd = ["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
           "--session-id","orch","--provider","llama-gptoss","--model","gpt-oss-20b",
           "--thinking","low","-t","subagent", ORCH_PROMPT]
    out_path = sb/"orch-out.json"
    p = subprocess.Popen(cmd, cwd=sb, stdout=open(out_path,"w"),
                         stderr=subprocess.DEVNULL, start_new_session=True)
    t0=time.time(); last=0; last_change=time.time(); status="ok"
    while True:
        if p.poll() is not None: break
        if time.time()-t0 > HARD_TIMEOUT: status="hard-timeout"; break
        sz = out_path.stat().st_size if out_path.exists() else 0
        if sz != last: last=sz; last_change=time.time()
        if (time.time()-last_change > STALL_LIMIT) and not bb.model_busy():
            status="stall-timeout"; break
        time.sleep(POLL)
    if p.poll() is None:
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM); time.sleep(4)
        except Exception: pass
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
    return time.time()-t0, status

def score(fx, sb, ptest):
    (sb/"test"/f"{fx}.test.ts").write_text(ptest)
    try:
        r=subprocess.run(["node","--test",f"test/{fx}.test.ts"],cwd=sb,
                         capture_output=True,text=True,timeout=120)
        return r.returncode==0
    except Exception: return False

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    summary = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    orig = bb.BUILDER_MD.read_text()
    try:
        for label, cfg in bb.BUILDERS.items():
            if label in summary and len(summary[label])==len(FIXTURES): continue
            print(f"\n===== BUILDER = {label} ({cfg['model']}) =====")
            ensure_models_builderonly(cfg["server"])
            bb.set_builder_model(cfg["model"])
            rows = summary.get(label, []); done={r["fx"] for r in rows}
            for fx in FIXTURES:
                if fx in done: continue
                sb, ptest = prep(label, fx)
                wall, status = run_phase(sb)
                spawns,halluc,bdur,turns,_v,dispatched = bb.metrics(sb)
                passed = score(fx, sb, ptest)
                outcome = ("PASS" if passed else
                           "DISPATCH-FAIL" if not dispatched else
                           status.upper() if status!="ok" else "FAIL")
                row=dict(fx=fx,passed=passed,outcome=outcome,spawns=spawns,halluc=halluc,
                         turns=turns,bdur=round(bdur),wall=round(wall),
                         dispatched=dispatched,status=status)
                rows.append(row); summary[label]=rows
                RESULTS.write_text(json.dumps(summary,indent=2))
                print(f"  {fx:<8} {outcome:<14} spawns={spawns} halluc={halluc} "
                      f"turns={turns} bdur={bdur:.0f}s wall={wall:.0f}s")
    finally:
        bb.BUILDER_MD.write_text(orig)
        RESULTS.write_text(json.dumps(summary,indent=2))
        print("\n[restored builder.md; saved]")
    print("\n"+"="*76)
    print(f"  {'builder':<14}{'pass@1':>8}{'oneshot':>9}{'halluc':>8}{'avg_turns':>11}{'avg_wall':>10}")
    print("  "+"-"*68)
    for label,rows in summary.items():
        n=len(rows)
        if not n: continue
        npass=sum(1 for r in rows if r["passed"])
        one=sum(1 for r in rows if r["passed"] and r["spawns"]==1)
        hal=sum(r["halluc"] for r in rows)
        at=sum(r["turns"] for r in rows)/n; aw=sum(r["wall"] for r in rows)/n
        print(f"  {label:<14}{npass}/{n:<6}{one}/{n:<7}{hal:>8}{at:>11.1f}{aw:>9.0f}s")
    print("="*76)
    print("  pass@1=code passes hidden gate | oneshot=passed in 1 builder spawn | halluc=no-op spawns")

if __name__=="__main__":
    main()
