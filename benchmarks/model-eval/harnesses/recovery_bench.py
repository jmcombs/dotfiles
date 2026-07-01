#!/usr/bin/env python3
"""Full-loop recovery bench. Seed a known-broken build, then run the real
verify -> remediation -> builder-fix -> re-verify cycle and confirm it recovers
within 3 rounds. Seeding the broken state isolates the RECOVERY mechanism."""
import json, shutil, subprocess, time
from pathlib import Path
import importlib.util

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_recovery"
VERIFIER = ("llama-ornith35b", "ornith-1.0-35b-moe", "high")
BUILDER  = ("llama-devstral", "devstral-small-2-24b", "off")
MAX_ROUNDS = 3

# reuse the planted defects from the verifier bench
spec = importlib.util.spec_from_file_location("vb", str(Path(__file__).parent/"verifier_bench.py"))
vb = importlib.util.module_from_spec(spec); spec.loader.exec_module(vb)

VERIFY_TASK = vb.VERIFY_TASK

def gate_exit(sb, fx):
    return subprocess.run(["node","--test",f"test/{fx}.test.ts"], cwd=sb,
                          capture_output=True, text=True, timeout=120).returncode

def seed(fx, defect_src):
    sb = SAND / fx
    if sb.exists(): shutil.rmtree(sb)
    src_dir = BASE / fx; sb.mkdir(parents=True)
    for item in src_dir.iterdir():
        if item.name == ".reference.ts": continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, sb / item.name)
    (sb/"src"/f"{fx}.ts").write_text(defect_src)
    subprocess.run(["git","init","-q"], cwd=sb, check=False)
    return sb

def pi(sb, sid, model, thinking, tools, task, timeout=900):
    cmd=["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
         "--session-id",sid,"--provider",model[0],"--model",model[1],
         "--thinking",thinking,"-t",tools,task]
    try:
        p=subprocess.run(cmd,cwd=sb,capture_output=True,text=True,timeout=timeout)
        return p.stdout or ""
    except subprocess.TimeoutExpired as e:
        raw=getattr(e,"stdout","") or ""
        return raw.decode("utf-8","replace") if isinstance(raw,(bytes,bytearray)) else raw

def final_assistant_text(out):
    txt=""
    for l in out.splitlines():
        l=l.strip()
        if not l: continue
        try: e=json.loads(l)
        except: continue
        if e.get("type")=="agent_end":
            for m in e.get("messages",[]):
                if m.get("role")=="assistant":
                    t="".join(c.get("text","") for c in m.get("content",[]) if isinstance(c,dict) and c.get("type")=="text")
                    if t.strip(): txt=t
    return txt

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    print(f"Recovery loop: verifier={VERIFIER[1]} / builder={BUILDER[1]}\n")
    rows=[]
    for fx,(correct,defect,desc) in vb.DEFECTS.items():
        sb=seed(fx,defect)
        print(f"[{fx}] seeded broken build ({desc}); gate_exit={gate_exit(sb,fx)} (broken)")
        builds=0; recovered=False; t0=time.time()
        for rnd in range(1, MAX_ROUNDS+1):
            vout=pi(sb,f"verify{rnd}",VERIFIER,VERIFIER[2],"read,bash,edit",VERIFY_TASK)
            ticked = "- [x]" in (sb/"PLAN.md").read_text()
            passes = gate_exit(sb,fx)==0
            print(f"  round {rnd}: verifier {'PASS' if ticked else 'FAIL'} (gate {'pass' if passes else 'fail'})")
            if ticked and passes:
                recovered=True; break
            # else remediate: hand verifier's findings to the builder
            remediation=final_assistant_text(vout)[:1500]
            btask=("You are the BUILDER. The verifier FAILED Phase 1 of PLAN.md. Fix the "
                   "implementation so the gate passes; do NOT modify the test file. Then re-run "
                   "the gate to confirm. Verifier findings:\n"+remediation)
            pi(sb,f"build{rnd}",BUILDER,BUILDER[2],"read,edit,write,bash",btask)
            builds+=1
        wall=time.time()-t0
        rows.append((fx,recovered,builds,gate_exit(sb,fx)==0,wall))
        print(f"  -> {'RECOVERED' if recovered else 'NOT recovered'} after {builds} fix round(s), {wall:.0f}s\n")
    print("="*68)
    print(f"  {'fixture':<10}{'recovered':>11}{'fix_rounds':>12}{'final_gate':>12}{'wall':>8}")
    print("  "+"-"*60)
    for fx,rec,builds,fg,wall in rows:
        print(f"  {fx:<10}{('YES' if rec else 'NO'):>11}{builds:>12}{('pass' if fg else 'FAIL'):>12}{wall:>7.0f}s")
    print("  "+"-"*60)
    print(f"  recovered: {sum(1 for r in rows if r[1])}/{len(rows)}")
    print("="*68)

if __name__=="__main__":
    main()
