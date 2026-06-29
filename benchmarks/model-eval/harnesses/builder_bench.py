#!/usr/bin/env python3
"""Builder-seat bake-off. Hold orchestrator=gpt-oss and verifier=Ornith constant;
swap ONLY the builder model. Score the metrics that matter for the builder seat:

  - outcome:        did the phase end correct (hidden gate passes)?
  - one-shot:       builder spawns == 1 (no rebuild churn)
  - hallucination:  builder spawn with exitCode!=0 "no edits"/"already complete" on a stub
  - churn:          total builder spawns, summed builder duration, turns
  - verify rounds:  how many verify passes were needed

The builder model is swapped by editing builder.md frontmatter between batches.
"""
import json, glob, re, shutil, subprocess, time, importlib.util
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_builder"
BUILDER_MD = Path("/Users/jmcombs/.dotfiles/pi/.pi/agent/agents/builder.md")
ORCH = ("llama-gptoss", "gpt-oss-20b", "low")
FIXTURES = ["roman", "lru", "bowling"]
TIMEOUT = 1200

spec = importlib.util.spec_from_file_location("vb", str(Path(__file__).parent/"verifier_bench.py"))
vb = importlib.util.module_from_spec(spec); spec.loader.exec_module(vb)

# builder candidates: label -> "provider/model-id"
BUILDERS = {
    "devstral-24b":  "llama-devstral/devstral-small-2-24b",
    "qwen3.6-27b":   "llama-qwen/qwen3.6-27b-coding-optimized",
    # cloud (added once key is set):
    # "glm-5.2":     "openrouter/z-ai/glm-5.2",
    # "deepseek-v4": "openrouter/deepseek/deepseek-v4",
}

ORCH_PROMPT = Path.home()/".pi/agent/prompts/orchestrator-phase-loop.md"

def set_builder_model(model):
    t = BUILDER_MD.read_text()
    BUILDER_MD.write_text(re.sub(r'^model:.*$', f'model: {model}', t, flags=re.M))

def prep(fx):
    sb = SAND / fx
    if sb.exists(): shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for it in (BASE/fx).iterdir():
        if it.name == ".reference.ts": continue
        (shutil.copytree if it.is_dir() else shutil.copy2)(it, sb/it.name)
    subprocess.run(["git","init","-q"], cwd=sb, check=False)
    # commit the stub so the verifier's clean-tree precondition can pass after builder commits
    subprocess.run(["git","add","-A"], cwd=sb, check=False)
    subprocess.run(["git","-c","user.email=b@b","-c","user.name=b","commit","-q","-m","scaffold"], cwd=sb, check=False)
    return sb, (sb/"test"/f"{fx}.test.ts").read_text()

def run_phase(sb):
    prompt = ORCH_PROMPT.read_text()
    cmd = ["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
           "--session-id","orch","--provider",ORCH[0],"--model",ORCH[1],
           "--thinking",ORCH[2],"-t","subagent",prompt]
    t0=time.time()
    try: subprocess.run(cmd,cwd=sb,capture_output=True,text=True,timeout=TIMEOUT)
    except subprocess.TimeoutExpired: pass
    return time.time()-t0

def builder_metrics(sb):
    metas=sorted(glob.glob(str(sb/".pisession/subagent-artifacts/*builder*meta.json")))
    spawns=len(metas); halluc=0; dur=0; turns=0
    for m in metas:
        j=json.load(open(m)); dur+=j.get("durationMs",0)/1000
        turns+=j.get("usage",{}).get("turns",0)
        err=(j.get("error") or "").lower()
        if j.get("exitCode")!=0 and ("no edits" in err or "without making" in err or "already complete" in err):
            halluc+=1
    vspawns=len(glob.glob(str(sb/".pisession/subagent-artifacts/*verifier*meta.json")))
    return spawns, halluc, dur, turns, vspawns

def score(fx, sb, ptest):
    (sb/"test"/f"{fx}.test.ts").write_text(ptest)  # anti-tamper
    r=subprocess.run(["node","--test",f"test/{fx}.test.ts"],cwd=sb,capture_output=True,text=True,timeout=120)
    return r.returncode==0

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    summary={}
    orig=BUILDER_MD.read_text()
    try:
        for label, model in BUILDERS.items():
            set_builder_model(model)
            print(f"\n===== BUILDER = {label} ({model}) =====")
            rows=[]
            for fx in FIXTURES:
                sb, ptest = prep(fx)
                wall=run_phase(sb)
                spawns,halluc,bdur,turns,vspawns=builder_metrics(sb)
                passed=score(fx,sb,ptest)
                rows.append((fx,passed,spawns,halluc,bdur,turns,vspawns,wall))
                print(f"  {fx:<8} {'PASS' if passed else 'FAIL'}  builder_spawns={spawns} halluc={halluc} "
                      f"bdur={bdur:.0f}s turns={turns} verifies={vspawns} wall={wall:.0f}s")
            summary[label]=rows
    finally:
        BUILDER_MD.write_text(orig)  # restore
        print("\n[restored builder.md]")

    print("\n"+"="*78)
    print(f"  {'builder':<14}{'pass':>6}{'oneshot':>9}{'halluc':>8}{'avg_turns':>11}{'avg_bdur':>10}")
    print("  "+"-"*70)
    for label,rows in summary.items():
        n=len(rows); npass=sum(1 for r in rows if r[1]); oneshot=sum(1 for r in rows if r[2]==1)
        halluc=sum(r[3] for r in rows); at=sum(r[5] for r in rows)/n; ad=sum(r[4] for r in rows)/n
        print(f"  {label:<14}{npass}/{n:<4}{oneshot}/{n:<7}{halluc:>8}{at:>11.1f}{ad:>9.0f}s")
    print("="*78)
    print("  pass=correct outcome | oneshot=built right first try | halluc=claimed done w/o edits")

if __name__=="__main__":
    main()
