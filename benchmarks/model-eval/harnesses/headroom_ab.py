#!/usr/bin/env python3
"""Headroom A/B: same large-context bug-fix task on Qwen3.6-27B, proxy OFF
(passthrough) vs ON (compression). Measures wall-clock, total prefill (input)
tokens summed across turns, accuracy (test passes), and turns.

Proxy on/off is the ONLY variable. Direct builder-style pi call (no orchestrator)
to isolate Headroom's effect on one agent's large-context multi-turn session.
"""
import json, glob, os, shutil, subprocess, time
from pathlib import Path

ROOT = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/headroom-ab")
FIX = ROOT/"fixture"
PROXY_HEALTH = "http://127.0.0.1:8787/health"
TASK = ("Implement Phase 1 of PLAN.md in this repo. Read src/lib.ts, run "
        "`node --test test/lib.test.ts` to find the failing case, fix the single "
        "buggy function so every compute_NNN(a,b) returns a+b, then re-run the test "
        "to confirm it passes. Then stop.")

def proxy_up():
    try:
        import urllib.request; urllib.request.urlopen(PROXY_HEALTH, timeout=2); return True
    except Exception: return False

def set_proxy(on):
    if on and not proxy_up():
        subprocess.Popen(["/Users/jmcombs/.headroom-venv/bin/headroom","proxy","--port","8787"],
                         stdout=open("/tmp/hr-proxy.log","w"), stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(30):
            if proxy_up(): break
            time.sleep(1)
    if not on and proxy_up():
        subprocess.run(["pkill","-f","headroom proxy"], check=False); time.sleep(2)

def run(mode):
    sb = ROOT/f"run-{mode}"
    if sb.exists(): shutil.rmtree(sb)
    shutil.copytree(FIX, sb)
    subprocess.run(["git","init","-q"], cwd=sb, check=False)
    set_proxy(mode=="on")
    print(f"  [{mode}] proxy_up={proxy_up()}")
    cmd=["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),"--session-id","t",
         "--provider","llama-qwen","--model","qwen3.6-27b-coding-optimized","--thinking","low",
         "-t","read,edit,write,bash", TASK]
    t0=time.time()
    try: subprocess.run(cmd,cwd=sb,stdout=open(sb/"out.json","w"),stderr=subprocess.DEVNULL,timeout=2400)
    except subprocess.TimeoutExpired: pass
    wall=time.time()-t0
    # sum input (prefill) tokens + turns from session
    sess=glob.glob(str(sb/".pisession/*t*.jsonl")) or glob.glob(str(sb/".pisession/*.jsonl"))
    in_tok=0; out_tok=0; turns=0; hr_calls=0
    if sess:
        for l in open(sess[0]):
            l=l.strip()
            if not l: continue
            try: e=json.loads(l)
            except: continue
            if e.get("type")=="message":
                m=e.get("message",{})
                if m.get("role")=="assistant":
                    turns+=1; u=m.get("usage",{}) or {}
                    in_tok+=u.get("input",0) or 0; out_tok+=u.get("output",0) or 0
                    for c in m.get("content",[]):
                        if isinstance(c,dict) and c.get("type")=="toolCall" and c.get("name")=="headroom_retrieve": hr_calls+=1
    # accuracy: restore pristine test, run
    shutil.copy2(FIX/"test/lib.test.ts", sb/"test/lib.test.ts")
    try: passed=subprocess.run(["node","--test","test/lib.test.ts"],cwd=sb,capture_output=True,text=True,timeout=120).returncode==0
    except Exception: passed=False
    return dict(mode=mode, passed=passed, wall=round(wall), turns=turns,
                input_tokens=in_tok, output_tokens=out_tok, retrieve_calls=hr_calls)

def main():
    rows=[]
    for mode in ("off","on"):     # baseline first, then compression
        print(f"\n=== MODE: {mode} ===")
        r=run(mode); rows.append(r)
        print(f"  passed={r['passed']} wall={r['wall']}s turns={r['turns']} "
              f"input_tok={r['input_tokens']} output_tok={r['output_tokens']} retrieve={r['retrieve_calls']}")
    set_proxy(True)  # restore proxy running (user's original state)
    print("\n"+"="*72)
    print(f"  {'mode':<8}{'passed':>8}{'wall':>8}{'turns':>7}{'input_tok':>11}{'output_tok':>12}")
    print("  "+"-"*64)
    for r in rows:
        print(f"  {r['mode']:<8}{str(r['passed']):>8}{r['wall']:>7}s{r['turns']:>7}{r['input_tokens']:>11}{r['output_tokens']:>12}")
    print("="*72)
    if len(rows)==2:
        off,on=rows[0],rows[1]
        dt=(off['wall']-on['wall'])/off['wall']*100 if off['wall'] else 0
        di=(off['input_tokens']-on['input_tokens'])/off['input_tokens']*100 if off['input_tokens'] else 0
        print(f"  ON vs OFF: wall {dt:+.0f}%  | prefill tokens {di:+.0f}%  | "
              f"accuracy {'preserved' if off['passed']==on['passed'] else 'CHANGED'}")
        print(f"  (positive % = ON used less; negative = ON used more)")

if __name__=="__main__": main()
