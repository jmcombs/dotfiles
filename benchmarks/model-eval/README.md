# Model-evaluation harnesses (pi phase-loop seat selection)

Reusable benchmark harnesses + fixtures used to choose the local models for the
pi phase-loop agent system (orchestrator / builder / verifier). Captured here as
a record of methodology and for re-running as models change.

> **Caveat:** these were built iteratively during a long session. Several scripts
> contain **hard-coded absolute scratch paths** and assume specific llama.cpp
> servers / pi providers. Treat them as a documented methodology + starting point,
> not turn-key CLIs — adjust `BASE`/paths and the model registry before re-running.

## Harnesses (`harnesses/`)

| Script | Measures |
|---|---|
| `builder_codequal.py` | Builder-only bake-off: orchestrator delegates once → score code vs hidden gate. pass@1, one-shot, hallucination, churn. |
| `builder_hard.py` | Same, on the harder 7 TS + 3 Py fixtures; language-aware scoring. |
| `builder_bench2.py` | Hardened model-manager + nested-session metrics (imported by the above). Loads only the needed models per batch (no swap thrash); idle-watchdog; incremental save. |
| `verifier_bench.py` | Verifier defect-catch: plant correct + defective solutions, score catches / false-merges / false-fails. |
| `verifier_ab.py` | Verifier thinking-level A/B (high vs medium) on defect-catch + timing. |
| `recovery_bench.py` | Full-loop recovery: seed a broken build → verify(FAIL) → builder-fix → re-verify. |
| `headroom_ab.py` / `headroom_ab_n.py` | Headroom compression proxy A/B (proxy off vs on) on a large-context task: wall, prefill tokens, accuracy. N-trial interleaved version. |
| `gen_hard_fixtures.py` | Generates + validates the 10 hard fixtures (stub fails, reference passes). |
| `run_ts_bench.py` | Early full orchestrator→builder→verifier loop over the easy fixtures. |
| `inspect_pi.py` | Parse a pi headless JSONL event stream. |
| `mlx_metrics.py` | Parse llama-humaneval result JSON (median/aggregate decode tok/s). |
| `builder_bench.py` | First-gen builder bake-off (superseded by `builder_codequal.py`). |

## Fixtures (`fixtures/`)

Each fixture: a stub `src/`, a hidden-test `test/`, a `PLAN.md` (phase + Testing
Gate), and a `.reference` solution used only to validate the oracle.

- `easy-ts/` — roman, lru, bowling (saturated: all models pass).
- `hard/` — 7 TS (interval-merge, glob-match DP, toposort+cycle, expr-eval,
  csv-parse, flatten, base-convert) + 3 Py (dijkstra, ini_parse, lcs).

## Headline findings

- **Orchestrator = gpt-oss-20b**, **locked to `subagent`-only** — given any
  execution tool it self-solves/thrashes instead of delegating; tool-stripped it
  dispatches reliably (~95%). gemma4 wouldn't tool-call at all.
- **Builder** — Ornith-35B, Qwen3.6-35B-A3B MoE, GLM-5.2, Kimi-K2.6 all hit
  ~100% correct even on hard fixtures; they separate only on **speed**. Dense
  Qwen3.6-27B matches on accuracy but is ~2.6× slower (dropped). Local 35B-class
  models are frontier-competitive — cloud not needed for this seat.
- **Verifier** — Ornith @ high: 3/3 defect-catch, 0 false-merges. Thinking
  high vs medium: equal catch + 0 false-merge, equal speed → keep high (more
  rule-adherent). Must be a **different** model than the builder for independence.
- **Headroom proxy** — net-negative for the local llama.cpp loop: ~70% slower
  end-to-end (compression rewrites history → busts the KV prefix cache + adds
  latency), accuracy unchanged. Built for cloud APIs, not local prefix-cached
  inference.
