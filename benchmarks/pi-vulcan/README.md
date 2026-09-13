# pi-vulcan

**Layout preset: Lean.**

Headless [pi](https://pi.dev) runner for a small [VulcanBench](https://github.com/morganlinton/VulcanBench) task subset. It measures **pi's agentic loop** against local llama.cpp, not Vulcan's own agent.

Each task is an `issue.md` plus a starting `repo/`. Hidden tests are overlaid **after** pi exits and never shown to the model. Grade is fail-to-pass / pass-to-pass, same as Vulcan.

Vendored tasks (Apache-2.0, see `NOTICE`):

| id | difficulty | why it is here |
|---|---|---|
| `hello-world` | trivial | wire-up smoke |
| `py-ttl-cache-expiry` | easy | localized bug fix |
| `py-topo-sort-cycle` | medium | Vulcan's own first real-run example |

This is **not** `llama-eval`, `llama-humaneval`, or `llama-agenteval`.

Headless `pi -p` cannot use the interactive `llama.cpp` extension provider
(it is unknown until `/llama` refreshes the catalog). The runner talks to the
router through a `local-llama` entry in `~/.pi/agent/models.json`
(`openai-completions` at `http://127.0.0.1:8080/v1`).

## Run

```bash
cd benchmarks/pi-vulcan
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pi-vulcan self-test
.venv/bin/pi-vulcan run --start-server --provider local-llama --model qwen3.8-27b
```

`--start-server` kickstarts Steward's existing launchd job (`com.llama.testbed`). It does not change launch argv. Experimental llama.cpp flags belong in `models.ini` until you hand them to Steward.

## Scorecard

```
task                      pass  functional  wall_s  turns  tools  err  tokens
hello-world               PASS  1.00          42.1      2      3    0    4100
```

JSON goes to `~/.cache/pi-vulcan/results/`.
