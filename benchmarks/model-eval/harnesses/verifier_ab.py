#!/usr/bin/env python3
"""A/B: verifier thinking high vs medium, defect-catch quality + timing.

Isolates ONE variable. The real `verifier` agent (skills loaded) is spawned via
a minimal gpt-oss orchestrator, once per case. Thinking is toggled by editing the
verifier agent frontmatter between batches (the production path). We score the
verifier's actual decision = did it tick the PLAN checkbox, vs ground-truth gate.
"""
import json, glob, os, re, shutil, subprocess, time, importlib.util
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_ab"
VERIFIER_MD = Path("/Users/jmcombs/.dotfiles/pi/.pi/agent/agents/verifier.md")
ORCH = ("llama-gptoss", "gpt-oss-20b", "low")
TIMEOUT = 600

spec = importlib.util.spec_from_file_location(
    "vb", str(Path(__file__).parent / "verifier_bench.py"))
vb = importlib.util.module_from_spec(spec); spec.loader.exec_module(vb)

ORCH_PROMPT = (
    'Call the subagent tool exactly once with agent:"verifier" and '
    'task:"Adversarially verify Phase 1 of PLAN.md following the phase-verify skill. '
    'Re-run every Testing Gate and tick the checkbox only if everything truly passes." '
    'Do NOT call builder or any other agent. After the verifier returns, report only '
    'its final VERDICT line (PASS or FAIL).')

def set_thinking(level):
    t = VERIFIER_MD.read_text()
    VERIFIER_MD.write_text(re.sub(r'^thinking:.*$', f'thinking: {level}', t, flags=re.M))

def prep(fx, variant, src):
    sb = SAND / f"{fx}-{variant}"
    if sb.exists(): shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for it in (BASE / fx).iterdir():
        if it.name == ".reference.ts": continue
        (shutil.copytree if it.is_dir() else shutil.copy2)(it, sb / it.name)
    (sb / "src" / f"{fx}.ts").write_text(src)
    subprocess.run(["git", "init", "-q"], cwd=sb, check=False)
    return sb

def run_case(sb):
    cmd = ["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
           "--session-id","orch","--provider",ORCH[0],"--model",ORCH[1],
           "--thinking",ORCH[2],"-t","subagent",ORCH_PROMPT]
    t0=time.time()
    try:
        subprocess.run(cmd,cwd=sb,capture_output=True,text=True,timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        pass
    wall=time.time()-t0
    metas=glob.glob(str(sb/".pisession/subagent-artifacts/*verifier*meta.json"))
    vdur=0; warn=None; vexit=None
    if metas:
        j=json.load(open(metas[0]))
        vdur=j.get("durationMs",0)/1000; warn=j.get("skillsWarning"); vexit=j.get("exitCode")
    ticked="- [x]" in (sb/"PLAN.md").read_text()
    return wall, vdur, warn, vexit, ticked

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    results={}
    try:
        for level in ("high","medium"):
            set_thinking(level)
            print(f"\n===== verifier thinking = {level} =====")
            rows=[]
            for fx,(correct,defect,desc) in vb.DEFECTS.items():
                for variant,src in (("correct",correct),("defect",defect)):
                    sb=prep(fx,variant,src)
                    gx=vb.gate_exit(sb,fx)            # ground truth: 0=passes
                    wall,vdur,warn,vexit,ticked=run_case(sb)
                    good=(gx==0)
                    if good and ticked: outcome="ok-pass"
                    elif (not good) and (not ticked): outcome="CAUGHT"
                    elif (not good) and ticked: outcome="FALSE-MERGE"
                    else: outcome="false-fail"
                    skl="skills-OK" if not warn else "SKILLS-MISSING"
                    rows.append((fx,variant,outcome,vdur,skl))
                    print(f"  {fx:<8} {variant:<7} gate={gx} ticked={str(ticked):<5} "
                          f"-> {outcome:<11} vdur={vdur:5.0f}s {skl}")
            results[level]=rows
    finally:
        set_thinking("high")   # restore safe default
        print("\n[restored verifier thinking -> high]")

    print("\n"+"="*64)
    print(f"  {'level':<8}{'caught':>8}{'false-merge':>13}{'false-fail':>12}{'avg_vdur':>10}")
    print("  "+"-"*56)
    for level,rows in results.items():
        caught=sum(1 for r in rows if r[2]=="CAUGHT")
        fm=sum(1 for r in rows if r[2]=="FALSE-MERGE")
        ff=sum(1 for r in rows if r[2]=="false-fail")
        ndef=sum(1 for r in rows if r[1]=="defect")
        avg=sum(r[3] for r in rows)/len(rows) if rows else 0
        print(f"  {level:<8}{caught:>3}/{ndef:<4}{fm:>13}{ff:>12}{avg:>9.0f}s")
    print("="*64)
    print("  quality first: keep HIGH unless MEDIUM matches caught + 0 false-merge.")

if __name__=="__main__":
    main()
