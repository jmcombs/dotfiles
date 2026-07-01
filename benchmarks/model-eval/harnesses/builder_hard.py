#!/usr/bin/env python3
"""Hard builder bake-off: 7 TS + 3 Py edge-case fixtures, builder-only, lang-aware.
Reuses the hardened model-manager + nested-session metrics from builder_bench2.
Roster: the 2 local finalists (gpt-oss-20b, Qwen3.6-35B-A3B MoE) + cloud ceilings."""
import json, os, shutil, signal, subprocess, time, importlib.util
from pathlib import Path

S=importlib.util.spec_from_file_location("bb","/private/tmp/claude-501/-Users-jmcombs--dotfiles/696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/builder_bench2.py")
bb=importlib.util.module_from_spec(S); S.loader.exec_module(bb)

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/phase-bench-hard")
SAND = BASE/"_runs"
RESULTS = BASE/"_hard_results.json"
HARD_TIMEOUT=1200; STALL_LIMIT=300; POLL=10

# (name, lang) — 70% TS / 30% Py
FIXTURES = [("interval-merge","ts"),("glob-match","ts"),("toposort","ts"),
            ("expr-eval","ts"),("csv-parse","ts"),("flatten","ts"),("base-convert","ts"),
            ("dijkstra","py"),("ini_parse","py"),("lcs","py")]

HARD_BUILDERS = {
  "qwen3.6-27b":     dict(model="llama-qwen/qwen3.6-27b-coding-optimized", server="qwen"),
  "qwen3.6-35b-a3b": dict(model="llama-qwen36moe/qwen3.6-35b-a3b", server="qwen36moe"),
  "ornith-35b":      dict(model="llama-ornith35b/ornith-1.0-35b-moe", server="ornith"),
}

ORCH_PROMPT = (
  'You are a dispatcher. Your ONLY tool is subagent. Call it EXACTLY ONCE with '
  'agent:"builder" and task:"Implement Phase 1 of PLAN.md: implement the function(s) '
  'in the src file per the test contract, and prove the Testing Gate by running its '
  'exact command. No branch/PR/commit needed; focus on correct code. Then stop." '
  'After the builder returns, STOP. Do NOT call any other agent or verify.')

def ensure_models(server):
    bb.start_server("gptoss")                     # orchestrator always
    for b in ("devstral","qwen","qwen36moe","ornith"):  # incl. ornith (now a builder candidate)
        if b==server: bb.start_server(b)
        else: bb.stop_server(b)

def testfile(name, lang): return f"test/{name}.test.ts" if lang=="ts" else f"test/{name}_test.py"
def gate(name, lang): return ["node","--test",testfile(name,lang)] if lang=="ts" else ["python3",testfile(name,lang)]

def prep(label, name, lang):
    sb=SAND/label/name
    if sb.exists(): shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for it in (BASE/name).iterdir():
        if it.name.startswith(".reference"): continue
        (shutil.copytree if it.is_dir() else shutil.copy2)(it, sb/it.name)
    return sb, (sb/testfile(name,lang)).read_text()

def run_phase(sb):
    cmd=["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),"--session-id","orch",
         "--provider","llama-gptoss","--model","gpt-oss-20b","--thinking","low","-t","subagent",ORCH_PROMPT]
    out=sb/"orch-out.json"; p=subprocess.Popen(cmd,cwd=sb,stdout=open(out,"w"),stderr=subprocess.DEVNULL,start_new_session=True)
    t0=time.time(); last=0; lc=time.time(); status="ok"
    while True:
        if p.poll() is not None: break
        if time.time()-t0>HARD_TIMEOUT: status="hard-timeout"; break
        sz=out.stat().st_size if out.exists() else 0
        if sz!=last: last=sz; lc=time.time()
        if time.time()-lc>STALL_LIMIT and not bb.model_busy(): status="stall-timeout"; break
        time.sleep(POLL)
    if p.poll() is None:
        try: os.killpg(os.getpgid(p.pid),signal.SIGTERM); time.sleep(4); os.killpg(os.getpgid(p.pid),signal.SIGKILL)
        except Exception: pass
    return time.time()-t0, status

def score(sb, name, lang, ptest):
    (sb/testfile(name,lang)).write_text(ptest)
    try: return subprocess.run(gate(name,lang),cwd=sb,capture_output=True,text=True,timeout=120).returncode==0
    except Exception: return False

def main():
    SAND.mkdir(parents=True,exist_ok=True)
    summ=json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    orig=bb.BUILDER_MD.read_text()
    try:
        for label,cfg in HARD_BUILDERS.items():
            if label in summ and len(summ[label])==len(FIXTURES): continue
            print(f"\n===== BUILDER = {label} =====")
            ensure_models(cfg["server"]); bb.set_builder_model(cfg["model"])
            rows=summ.get(label,[]); done={r["fx"] for r in rows}
            for name,lang in FIXTURES:
                if name in done: continue
                sb,ptest=prep(label,name,lang)
                wall,status=run_phase(sb)
                spawns,halluc,bdur,turns,_v,disp=bb.metrics(sb)
                passed=score(sb,name,lang,ptest)
                outcome=("PASS" if passed else "DISPATCH-FAIL" if not disp else status.upper() if status!="ok" else "FAIL")
                rows.append(dict(fx=name,lang=lang,passed=passed,outcome=outcome,spawns=spawns,
                                 halluc=halluc,turns=turns,bdur=round(bdur),wall=round(wall)))
                summ[label]=rows; RESULTS.write_text(json.dumps(summ,indent=2))
                print(f"  {name:<15}[{lang}] {outcome:<14} turns={turns} bdur={bdur:.0f}s wall={wall:.0f}s")
    finally:
        bb.BUILDER_MD.write_text(orig); RESULTS.write_text(json.dumps(summ,indent=2)); print("\n[restored builder.md]")
    print("\n"+"="*84)
    print(f"  {'builder':<16}{'TS':>8}{'Py':>8}{'overall':>10}{'avg_turns':>11}{'avg_wall':>10}")
    print("  "+"-"*76)
    for label,rows in summ.items():
        ts=[r for r in rows if r['lang']=='ts']; py=[r for r in rows if r['lang']=='py']
        tsp=sum(1 for r in ts if r['passed']); pyp=sum(1 for r in py if r['passed']); n=len(rows); allp=tsp+pyp
        at=sum(r['turns'] for r in rows)/n if n else 0; aw=sum(r['wall'] for r in rows)/n if n else 0
        print(f"  {label:<16}{tsp}/{len(ts):<6}{pyp}/{len(py):<6}{allp}/{n:<8}{at:>11.1f}{aw:>9.0f}s")
    print("="*84)

if __name__=="__main__": main()
