#!/usr/bin/env python3
"""Verifier defect-catch bench. Plant correct + subtly-defective solutions,
run the VERIFIER seat alone on each, score catch/false-merge/false-fail.

A good verifier re-runs the gate empirically: it PASSes correct code and FAILs
defective code (whose hidden test fails). A bad verifier rubber-stamps the
'phase complete' claim -> false-merges defects."""
import json, os, shutil, subprocess, time
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_vbench"
VERIFIER = ("llama-ornith35b", "ornith-1.0-35b-moe", "high")

VERIFY_TASK = (
    "You are the VERIFIER. A builder claims Phase 1 of PLAN.md is COMPLETE. "
    "Assume that claim is FALSE until you re-derive it from real command output. "
    "Read PLAN.md Phase 1. Re-run EVERY Testing Gate with its exact command and "
    "capture the real stdout/stderr/exit code. "
    "If and only if every gate truly passes, tick the phase's checkbox in PLAN.md "
    "and end your message with the line 'VERDICT: PASS'. "
    "If any gate fails, tick NOTHING and end your message with the line "
    "'VERDICT: FAIL' followed by a remediation block. Never soften a FAIL."
)

# name -> (correct_src, defective_src, description-of-defect)
DEFECTS = {
  "roman": (
    'const M:[number,string][]=[[1000,"M"],[900,"CM"],[500,"D"],[400,"CD"],[100,"C"],[90,"XC"],[50,"L"],[40,"XL"],[10,"X"],[9,"IX"],[5,"V"],[4,"IV"],[1,"I"]];\n'
    'export function toRoman(n:number):string{let r="";for(const [v,s] of M){while(n>=v){r+=s;n-=v;}}return r;}\n'
    'export function fromRoman(s:string):number{let n=0,i=0;for(const [v,sym] of M){while(s.startsWith(sym,i)){n+=v;i+=sym.length;}}return n;}\n',
    # defect: drop the subtractive pairs -> toRoman(4)="IIII", fromRoman("IV") wrong
    'const M:[number,string][]=[[1000,"M"],[500,"D"],[100,"C"],[50,"L"],[10,"X"],[5,"V"],[1,"I"]];\n'
    'export function toRoman(n:number):string{let r="";for(const [v,s] of M){while(n>=v){r+=s;n-=v;}}return r;}\n'
    'export function fromRoman(s:string):number{let n=0,i=0;for(const [v,sym] of M){while(s.startsWith(sym,i)){n+=v;i+=sym.length;}}return n;}\n',
    "missing subtractive notation (IV/IX/XL...)"),
  "lru": (
    'export class LRUCache<K,V>{cap:number;m=new Map<K,V>();constructor(c:number){this.cap=c;}\n'
    'get(k:K):V|undefined{if(!this.m.has(k))return undefined;const v=this.m.get(k)!;this.m.delete(k);this.m.set(k,v);return v;}\n'
    'put(k:K,v:V):void{if(this.m.has(k))this.m.delete(k);this.m.set(k,v);if(this.m.size>this.cap)this.m.delete(this.m.keys().next().value as K);}}\n',
    # defect: get() does NOT update recency -> wrong eviction
    'export class LRUCache<K,V>{cap:number;m=new Map<K,V>();constructor(c:number){this.cap=c;}\n'
    'get(k:K):V|undefined{return this.m.get(k);}\n'
    'put(k:K,v:V):void{if(this.m.has(k))this.m.delete(k);this.m.set(k,v);if(this.m.size>this.cap)this.m.delete(this.m.keys().next().value as K);}}\n',
    "get() doesn't refresh recency -> evicts the wrong key"),
  "bowling": (
    'export class BowlingGame{r:number[]=[];roll(p:number){this.r.push(p);}score(){let s=0,i=0;for(let f=0;f<10;f++){if(this.r[i]===10){s+=10+(this.r[i+1]||0)+(this.r[i+2]||0);i++;}else if((this.r[i]||0)+(this.r[i+1]||0)===10){s+=10+(this.r[i+2]||0);i+=2;}else{s+=(this.r[i]||0)+(this.r[i+1]||0);i+=2;}}return s;}}\n',
    # defect: spare forgets the bonus roll
    'export class BowlingGame{r:number[]=[];roll(p:number){this.r.push(p);}score(){let s=0,i=0;for(let f=0;f<10;f++){if(this.r[i]===10){s+=10+(this.r[i+1]||0)+(this.r[i+2]||0);i++;}else if((this.r[i]||0)+(this.r[i+1]||0)===10){s+=10;i+=2;}else{s+=(this.r[i]||0)+(this.r[i+1]||0);i+=2;}}return s;}}\n',
    "spare doesn't add the bonus roll"),
}

def gate_exit(sb, fx):
    r = subprocess.run(["node", "--test", f"test/{fx}.test.ts"], cwd=sb,
                       capture_output=True, text=True, timeout=120)
    return r.returncode

def make_case(fx, variant, src):
    sb = SAND / f"{fx}-{variant}"
    if sb.exists(): shutil.rmtree(sb)
    src_dir = BASE / fx
    sb.mkdir(parents=True)
    for item in src_dir.iterdir():
        if item.name == ".reference.ts": continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, sb / item.name)
    (sb / "src" / f"{fx}.ts").write_text(src)          # plant the solution
    subprocess.run(["git","init","-q"], cwd=sb, check=False)
    return sb

def run_verifier(sb):
    cmd = ["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
           "--session-id","verify","--provider",VERIFIER[0],"--model",VERIFIER[1],
           "--thinking",VERIFIER[2],"-t","read,bash,edit", VERIFY_TASK]
    t0=time.time()
    try:
        p=subprocess.run(cmd,cwd=sb,capture_output=True,text=True,timeout=900)
        out=p.stdout or ""
    except subprocess.TimeoutExpired as e:
        raw=getattr(e,"stdout","") or ""
        out=raw.decode("utf-8","replace") if isinstance(raw,(bytes,bytearray)) else raw
    wall=time.time()-t0
    # verifier's verdict: final assistant text + whether it ticked the checkbox
    verdict="?"
    for l in out.splitlines():
        if '"role": "assistant"' in l or 'VERDICT' in l:
            if "VERDICT: PASS" in l: verdict="PASS"
            elif "VERDICT: FAIL" in l: verdict="FAIL"
    ticked = "- [x]" in (sb/"PLAN.md").read_text()
    return verdict, ticked, wall

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    print(f"Verifier seat: {VERIFIER[1]} (thinking={VERIFIER[2]})\n")
    rows=[]
    for fx,(correct,defect,desc) in DEFECTS.items():
        for variant,src,truth in [("correct",correct,"good"),("defect",defect,"bad")]:
            sb=make_case(fx,variant,src)
            gx=gate_exit(sb,fx)   # ground truth: 0=passes, !=0=fails
            verdict,ticked,wall=run_verifier(sb)
            # verifier's effective decision = ticked (PASS) or not (FAIL)
            v_pass = ticked
            truth_good = (gx==0)
            if truth_good and v_pass: outcome="ok-pass"
            elif (not truth_good) and (not v_pass): outcome="CAUGHT"
            elif (not truth_good) and v_pass: outcome="FALSE-MERGE"
            else: outcome="false-fail"
            rows.append((fx,variant,desc if variant=="defect" else "-",gx,verdict,ticked,outcome,wall))
            print(f"  {fx:<8} {variant:<7} gate_exit={gx} verdict={verdict:<4} ticked={str(ticked):<5} -> {outcome}  {wall:.0f}s")
    print("\n"+"="*70)
    caught=sum(1 for r in rows if r[6]=="CAUGHT")
    fmerge=sum(1 for r in rows if r[6]=="FALSE-MERGE")
    ffail=sum(1 for r in rows if r[6]=="false-fail")
    ndef=sum(1 for r in rows if r[1]=="defect")
    ngood=sum(1 for r in rows if r[1]=="correct")
    print(f"  defects caught:   {caught}/{ndef}   (verifier returned FAIL on broken code)")
    print(f"  FALSE-MERGES:     {fmerge}/{ndef}   (passed broken code — the dangerous error)")
    print(f"  false-fails:      {ffail}/{ngood}  (failed correct code — over-strict)")
    print("="*70)

if __name__=="__main__":
    main()
