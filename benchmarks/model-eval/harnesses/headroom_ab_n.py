#!/usr/bin/env python3
"""Headroom A/B, N interleaved trials. Same large-context bug-fix task on
Qwen3.6-27B, proxy OFF (passthrough) vs ON (compression). Interleaved off,on,off,on
to cancel thermal/time drift. Averages out agent turn-count variance.
Metrics per run: wall, turns, input(prefill) tokens, output tokens, pass, retrieve."""
import json, glob, os, shutil, statistics, subprocess, time
from pathlib import Path

ROOT = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/headroom-ab")
FIX = ROOT/"fixture"
RESULTS = ROOT/"ab_n_results.json"
TRIALS = 5
TASK = ("Implement Phase 1 of PLAN.md in this repo. Read src/lib.ts, run "
        "`node --test test/lib.test.ts` to find the failing case, fix the single "
        "buggy function so every compute_NNN(a,b) returns a+b, then re-run the test "
        "to confirm it passes. Then stop.")

def proxy_up():
    try:
        import urllib.request; urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=2); return True
    except Exception: return False

def set_proxy(on):
    if on and not proxy_up():
        subprocess.Popen(["/Users/jmcombs/.headroom-venv/bin/headroom","proxy","--port","8787"],
                         stdout=open("/tmp/hr-proxy.log","w"), stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(40):
            if proxy_up(): break
            time.sleep(1)
    elif not on and proxy_up():
        subprocess.run(["pkill","-f","headroom proxy"], check=False); time.sleep(2)

def run(mode, trial):
    sb = ROOT/f"n-{mode}-{trial}"
    if sb.exists(): shutil.rmtree(sb)
    shutil.copytree(FIX, sb); subprocess.run(["git","init","-q"],cwd=sb,check=False)
    set_proxy(mode=="on")
    cmd=["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),"--session-id","t",
         "--provider","llama-qwen","--model","qwen3.6-27b-coding-optimized","--thinking","low",
         "-t","read,edit,write,bash", TASK]
    t0=time.time()
    try: subprocess.run(cmd,cwd=sb,stdout=open(sb/"out.json","w"),stderr=subprocess.DEVNULL,timeout=2400)
    except subprocess.TimeoutExpired: pass
    wall=time.time()-t0
    sess=glob.glob(str(sb/".pisession/*.jsonl"))
    intok=outtok=turns=hr=0
    if sess:
        for l in open(sess[0]):
            l=l.strip()
            if not l: continue
            try: e=json.loads(l)
            except: continue
            if e.get("type")=="message" and (e.get("message") or {}).get("role")=="assistant":
                turns+=1; u=e["message"].get("usage",{}) or {}
                intok+=u.get("input",0) or 0; outtok+=u.get("output",0) or 0
                for c in e["message"].get("content",[]):
                    if isinstance(c,dict) and c.get("type")=="toolCall" and c.get("name")=="headroom_retrieve": hr+=1
    shutil.copy2(FIX/"test/lib.test.ts", sb/"test/lib.test.ts")
    try: passed=subprocess.run(["node","--test","test/lib.test.ts"],cwd=sb,capture_output=True,text=True,timeout=120).returncode==0
    except Exception: passed=False
    shutil.rmtree(sb, ignore_errors=True)  # tidy (keep results json)
    return dict(mode=mode,trial=trial,passed=passed,wall=round(wall),turns=turns,intok=intok,outtok=outtok,retrieve=hr)

def main():
    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    done = {(r["mode"],r["trial"]) for r in res}
    for t in range(1, TRIALS+1):
        for mode in ("off","on"):          # interleave off,on each trial
            if (mode,t) in done: continue
            print(f"  trial {t} [{mode}] ... ", end="", flush=True)
            r=run(mode,t); res.append(r); RESULTS.write_text(json.dumps(res,indent=2))
            print(f"pass={r['passed']} wall={r['wall']}s turns={r['turns']} intok={r['intok']} out={r['outtok']} retr={r['retrieve']}")
    set_proxy(True)  # restore proxy running
    # stats
    def stats(mode,key):
        v=[r[key] for r in res if r["mode"]==mode]
        return (statistics.median(v), statistics.mean(v), min(v), max(v)) if v else (0,0,0,0)
    print("\n"+"="*84)
    print(f"  {'mode':<6}{'n':>3}{'pass':>6}{'wall_med':>10}{'wall_mean':>11}{'turns_med':>11}{'intok_med':>11}{'out_med':>9}")
    print("  "+"-"*76)
    for mode in ("off","on"):
        rows=[r for r in res if r["mode"]==mode]; n=len(rows); p=sum(1 for r in rows if r["passed"])
        wm,wa,_,_=stats(mode,"wall"); tm,_,_,_=stats(mode,"turns"); im,_,_,_=stats(mode,"intok"); om,_,_,_=stats(mode,"outtok")
        print(f"  {mode:<6}{n:>3}{p}/{n:<4}{wm:>9.0f}s{wa:>10.0f}s{tm:>11.0f}{im:>11.0f}{om:>9.0f}")
    print("="*84)
    om=statistics.median([r["wall"] for r in res if r["mode"]=="off"])
    nm=statistics.median([r["wall"] for r in res if r["mode"]=="on"])
    print(f"  VERDICT (median wall): ON {'-' if nm>om else '+'}{abs(nm-om)/om*100:.0f}% vs OFF "
          f"-> Headroom is {'SLOWER (bad for this workload)' if nm>om*1.05 else 'FASTER (good)' if nm<om*0.95 else 'NEUTRAL'}")
    offp=all(r['passed'] for r in res if r['mode']=='off'); onp=all(r['passed'] for r in res if r['mode']=='on')
    print(f"  accuracy: off {'all pass' if offp else 'SOME FAIL'} | on {'all pass' if onp else 'SOME FAIL'}")

if __name__=="__main__": main()
