#!/usr/bin/env python3
"""Hardened builder-seat bake-off.

Fixes from the contaminated v1 run:
  - Resource: loads ONLY the 3 models needed (gpt-oss orch + ornith verifier +
    the one builder under test) at ctx 32768. No 4-model swap-thrash. Cloud
    builders need no local builder server.
  - Incremental save: result JSON written after EVERY fixture (kill-safe).
  - Unique sandbox per (builder, fixture): no cross-batch overwrite.
  - Idle-watchdog: pi spawned in its own process group; if no model CPU + no
    session growth for STALL_LIMIT, the whole pi subtree is killpg'd and the
    fixture marked TIMEOUT (clean row, not corruption).
  - Dispatch-fail detection: 0 real subagent tool calls -> 'dispatch-fail'.
"""
import json, glob, os, re, shutil, signal, subprocess, time
from datetime import datetime
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/ts-phase-bench")
SAND = BASE / "_builder2"
RESULTS = BASE / "_builder2_results.json"
BUILDER_MD = Path("/Users/jmcombs/.dotfiles/pi/.pi/agent/agents/builder.md")
ORCH_PROMPT = Path.home()/".pi/agent/prompts/orchestrator-phase-loop.md"
MODELS_DIR = Path("/Users/jmcombs/.local/share/llama/models")
LLAMA = "/opt/homebrew/bin/llama-server"
CTX = "32768"
FIXTURES = ["roman", "lru", "bowling"]
HARD_TIMEOUT = 1800     # absolute cap per fixture (full build+verify+remediate loop)
STALL_LIMIT = 240       # kill if orch-out.json stops growing + models idle this long
POLL = 10

import importlib.util
_spec = importlib.util.spec_from_file_location("vb", str(Path(__file__).parent/"verifier_bench.py"))
vb = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(vb)

# ---- server specs (flags mirror the production plists, ctx reduced) ----
COMMON = ["--batch-size","4096","--fit","off","--flash-attn","on",
          "--cache-type-k","q8_0","--cache-type-v","q8_0","--parallel","1","--host","127.0.0.1"]
SERVERS = {
  "gptoss":   dict(port=11440, gguf="gpt-oss-20b-MXFP4.gguf", alias="gpt-oss-20b",
                   extra=["--jinja","--reasoning-format","auto"]),
  "ornith":   dict(port=11439, gguf="ornith-1.0-35b-Q8_0.gguf", alias="ornith-1.0-35b-moe",
                   extra=["--temp","0.6","--top-k","20","--top-p","0.95"]),
  "devstral": dict(port=11437, gguf="Devstral-Small-2-24B-Instruct-2512-Q8_0.gguf",
                   alias="devstral-small-2-24b", extra=[]),
  "qwen":     dict(port=11434, gguf="Qwen3.6-27B-Q8_0.gguf", alias="qwen3.6-27b-coding-optimized",
                   extra=["--spec-type","draft-mtp","--spec-draft-n-max","2"]),
  "qwen36moe": dict(port=11441, gguf="Qwen3.6-35B-A3B-Q8_0.gguf", alias="qwen3.6-35b-a3b",
                    extra=[]),
}
LOCAL_BUILDER_SERVERS = ("devstral","qwen","qwen36moe")

# builder candidates: label -> dict(provider/model + which local server (or None=cloud))
BUILDERS = {
  "qwen3.6-35b-a3b": dict(model="llama-qwen36moe/qwen3.6-35b-a3b", server="qwen36moe"),
  "gpt-oss-20b":     dict(model="llama-gptoss/gpt-oss-20b", server="gptoss"),
  "qwen3.6-27b":     dict(model="llama-qwen/qwen3.6-27b-coding-optimized", server="qwen"),
  "glm-5.2":         dict(model="openrouter/z-ai/glm-5.2", server=None),
  "kimi-k2.6":       dict(model="openrouter/moonshotai/kimi-k2.6", server=None),
}

def port_up(port):
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2)
        return True
    except Exception:
        return False

def start_server(key):
    s = SERVERS[key]
    if port_up(s["port"]): return
    cmd = [LLAMA,"--model",str(MODELS_DIR/s["gguf"]),"--alias",s["alias"],
           "--ctx-size",CTX,*COMMON,*s["extra"],"--port",str(s["port"])]
    log = open(f"/tmp/bench-{key}.log","w")
    subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    for _ in range(120):
        if port_up(s["port"]): print(f"    [server {key} up :{s['port']}]"); return
        time.sleep(1)
    raise RuntimeError(f"server {key} failed to start")

def stop_server(key):
    s = SERVERS[key]
    subprocess.run(["pkill","-f",f"llama-server.*{s['alias']}"], check=False)

def ensure_models(builder_server):
    """Keep gpt-oss + ornith; load builder_server; stop other local builders."""
    start_server("gptoss"); start_server("ornith")
    for b in ("devstral","qwen"):
        if b == builder_server: start_server(b)
        else: stop_server(b)

def set_builder_model(model):
    t = BUILDER_MD.read_text()
    BUILDER_MD.write_text(re.sub(r'^model:.*$', f'model: {model}', t, flags=re.M))

def prep(builder_label, fx):
    sb = SAND / builder_label / fx
    if sb.exists(): shutil.rmtree(sb)
    sb.mkdir(parents=True)
    for it in (BASE/fx).iterdir():
        if it.name == ".reference.ts": continue
        (shutil.copytree if it.is_dir() else shutil.copy2)(it, sb/it.name)
    subprocess.run(["git","init","-q"], cwd=sb, check=False)
    subprocess.run(["git","add","-A"], cwd=sb, check=False)
    subprocess.run(["git","-c","user.email=b@b","-c","user.name=b","commit","-q","-m","scaffold"], cwd=sb, check=False)
    return sb, (sb/"test"/f"{fx}.test.ts").read_text()

def orch_session(sb):
    f = glob.glob(str(sb/".pisession/*orch*.jsonl"))
    return f[0] if f else None

def model_busy():
    out = subprocess.run(["ps","-Ao","%cpu,command"], capture_output=True, text=True).stdout
    return any(float(l.split()[0])>20 for l in out.splitlines()
              if "llama-server" in l and l.split()[0].replace('.','').isdigit())

def run_phase(sb):
    """Spawn pi in its own process group; watchdog kills the subtree on stall."""
    cmd = ["pi","-p","--mode","json","--session-dir",str(sb/".pisession"),
           "--session-id","orch","--provider","llama-gptoss","--model","gpt-oss-20b",
           "--thinking","low","-t","subagent", ORCH_PROMPT.read_text()]
    out_path = sb/"orch-out.json"
    log = open(out_path,"w")
    p = subprocess.Popen(cmd, cwd=sb, stdout=log, stderr=subprocess.DEVNULL, start_new_session=True)
    t0=time.time(); last_size=0; last_change=time.time(); status="ok"
    while True:
        rc = p.poll()
        if rc is not None: break
        if time.time()-t0 > HARD_TIMEOUT: status="hard-timeout"; break
        # liveness = the pi stdout stream (orch-out.json) growing; it streams ALL
        # parent+child activity, unlike the static top-level session file.
        size = out_path.stat().st_size if out_path.exists() else 0
        if size != last_size: last_size=size; last_change=time.time()
        if (time.time()-last_change > STALL_LIMIT) and not model_busy():
            status="stall-timeout"; break
        time.sleep(POLL)
    if p.poll() is None:
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM); time.sleep(5)
        except Exception: pass
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
    return time.time()-t0, status

def _child_sessions(sb):
    """pi-subagents nests each spawn at <sess>/<orch>/<runid>/run-N/session.jsonl.
    Return list of (runid, path)."""
    out=[]
    for f in glob.glob(str(sb/".pisession/**/session.jsonl"), recursive=True):
        rid = Path(f).parents[1].name   # run-N -> runid
        out.append((rid, f))
    return out

def metrics(sb):
    art = sb/".pisession/subagent-artifacts"
    binputs = glob.glob(str(art/"*_builder_*_input.md"))
    vinputs = glob.glob(str(art/"*_verifier_*_input.md"))
    spawns=len(binputs); vspawns=len(vinputs)
    builder_rids = {Path(f).name.split("_")[0] for f in binputs}
    dispatched = (spawns+vspawns) > 0
    halluc=0; turns=0; bdur=0.0
    def _iso(t):
        try: return datetime.fromisoformat(t.replace("Z","+00:00"))
        except Exception: return None
    for rid, sess in _child_sessions(sb):
        if rid not in builder_rids: continue
        try: ev=[json.loads(l) for l in open(sess) if l.strip()]
        except: continue
        edits=0; aturns=0
        for e in ev:
            if e.get("type")!="message": continue
            m=e.get("message",{})
            if m.get("role")=="assistant":
                aturns+=1
                for c in m.get("content",[]):
                    if isinstance(c,dict) and c.get("type")=="toolCall" and c.get("name") in ("edit","write"):
                        edits+=1
        turns+=aturns
        if edits==0: halluc+=1                       # builder claimed done w/o any edit = no-op/hallucination
        ts=[_iso(e["timestamp"]) for e in ev if isinstance(e.get("timestamp"),str)]
        ts=[t for t in ts if t]
        if len(ts)>=2: bdur+=(max(ts)-min(ts)).total_seconds()
    return spawns, halluc, bdur, turns, vspawns, dispatched

def score(fx, sb, ptest):
    (sb/"test"/f"{fx}.test.ts").write_text(ptest)
    try:
        r=subprocess.run(["node","--test",f"test/{fx}.test.ts"],cwd=sb,capture_output=True,text=True,timeout=120)
        return r.returncode==0
    except Exception:
        return False

def save(summary):
    RESULTS.write_text(json.dumps(summary, indent=2))

def main():
    SAND.mkdir(parents=True, exist_ok=True)
    summary = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    orig = BUILDER_MD.read_text()
    try:
        for label, cfg in BUILDERS.items():
            if label in summary and len(summary[label])==len(FIXTURES):
                print(f"\n== {label}: already done, skipping =="); continue
            print(f"\n===== BUILDER = {label} ({cfg['model']}) =====")
            ensure_models(cfg["server"])
            set_builder_model(cfg["model"])
            rows = summary.get(label, [])
            done = {r["fx"] for r in rows}
            for fx in FIXTURES:
                if fx in done: continue
                sb, ptest = prep(label, fx)
                wall, status = run_phase(sb)
                spawns,halluc,bdur,turns,vspawns,dispatched = metrics(sb)
                passed = score(fx, sb, ptest)
                outcome = ("PASS" if passed else
                           "DISPATCH-FAIL" if not dispatched else
                           status.upper() if status!="ok" else "FAIL")
                row=dict(fx=fx,passed=passed,outcome=outcome,spawns=spawns,halluc=halluc,
                         bdur=round(bdur),turns=turns,vspawns=vspawns,dispatched=dispatched,
                         wall=round(wall),status=status)
                rows.append(row); summary[label]=rows; save(summary)
                print(f"  {fx:<8} {outcome:<14} spawns={spawns} halluc={halluc} turns={turns} "
                      f"verifies={vspawns} bdur={bdur:.0f}s wall={wall:.0f}s")
    finally:
        BUILDER_MD.write_text(orig); save(summary)
        print("\n[restored builder.md; results saved]")
    scorecard(summary)

def scorecard(summary):
    print("\n"+"="*82)
    print(f"  {'builder':<14}{'pass':>6}{'oneshot':>9}{'halluc':>8}{'dispatch':>10}{'avg_turns':>11}{'avg_wall':>10}")
    print("  "+"-"*74)
    for label,rows in summary.items():
        n=len(rows);
        if not n: continue
        npass=sum(1 for r in rows if r["passed"]); one=sum(1 for r in rows if r["spawns"]==1 and r["passed"])
        hal=sum(r["halluc"] for r in rows); disp=sum(1 for r in rows if r["dispatched"])
        at=sum(r["turns"] for r in rows)/n; aw=sum(r["wall"] for r in rows)/n
        print(f"  {label:<14}{npass}/{n:<4}{one}/{n:<7}{hal:>8}{disp}/{n:<8}{at:>11.1f}{aw:>9.0f}s")
    print("="*82)

if __name__=="__main__":
    main()
