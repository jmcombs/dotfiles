# Handoff: Ollama → llama.cpp Migration

This document is a self-contained handoff prompt for a new Claude Code session.
Copy everything below the horizontal rule into the new session.

---

## Context

You are helping migrate a local AI inference setup from Ollama to llama.cpp on a
**14" MacBook Pro M5 Max, 128 GB unified memory**, running macOS 26.5.0. The working
directory is `~/.dotfiles`, which is a GNU Stow-managed dotfiles repo.

The user runs a local coding agent called **pi** (config at `~/.dotfiles/pi/.pi/agent/`).
Pi uses an OpenAI-compatible API endpoint — currently pointed at Ollama — to serve local
models. The goal is to replace Ollama with `llama-server` (llama.cpp's built-in OpenAI
API server), with no GUI or chat interface, running as a background service.

---

## Current State

**Ollama version:** 0.30.2 (installed via Homebrew at `/opt/homebrew/bin/ollama`)

**Currently installed models (in Ollama's blob store at `~/.ollama/models/`):**

| Model | Precision | Size on disk | Notes |
|---|---|---|---|
| `gemma4:31b-coding-mtp-bf16` | BF16 | ~63.5 GB | Multi-Token Prediction variant with draft heads |
| `qwen3.6:27b-coding-mxfp8` | MXFP8 (≈FP8) | ~31 GB | Coding-specialized; best locally-runnable dense coding model (77.2% SWE-bench Verified) |

**Current Ollama environment (from `~/.dotfiles/ollama/Library/LaunchAgents/com.ollama.plist`):**

- `OLLAMA_CONTEXT_LENGTH=262144` (but modelfiles override to 131072)
- `OLLAMA_FLASH_ATTENTION=1`
- `OLLAMA_KV_CACHE_TYPE=q8_0`
- `OLLAMA_MAX_LOADED_MODELS=2` (both models loaded simultaneously)
- `OLLAMA_KEEP_ALIVE=24h`
- `OLLAMA_NUM_PARALLEL=1`
- Logs to `/tmp/ollama.log`
- `RunAtLoad=false` — started manually, not on login

**Pi agent models.json** (`~/.dotfiles/pi/.pi/agent/models.json`):

- Provider: `ollama`, baseUrl: `http://localhost:11434/v1`
- Two models registered: `gemma4-31b-coding-mtp-optimized` and `qwen3.6-27b-coding-optimized`
- Both have `"reasoning": true`, 131072 context window, 8192 maxTokens

---

## Research Summary (from prior session — do not re-research unless verifying)

**Why move from Ollama to llama.cpp:**

1. **Speculative decoding.** Ollama does not support it. `llama-server` does via `--draft-max`.
   The `gemma4:31b-coding-mtp-bf16` model has Multi-Token Prediction heads baked in —
   these are exactly what llama.cpp's self-speculative decoding uses. Expected improvement:
   1.4×–2.2× tokens/sec on generation-heavy workloads with no quality loss (mathematically
   lossless — rejection sampling preserves output distribution).

2. **Ollama IS llama.cpp + Metal.** There is no raw performance difference between Ollama and
   llama.cpp at identical settings for dense models. The gain is exclusively from features
   Ollama doesn't expose (speculative decoding, finer batch/rope control).

3. **Direct control.** No management layer, no model registry, no automatic unloading.

**Critical constraint — MoE models on Apple Silicon llama.cpp:**
MoE (Mixture-of-Experts) models run 2–3× slower in llama.cpp than in MLX on Apple Silicon.
All four target models are dense. Do NOT recommend MoE alternatives.

**Target models to run after migration:**

| Model | GGUF Quant | Size (Q8_0) | Port | Role |
|---|---|---|---|---|
| Qwen3.6-27B | Q8_0 | ~27 GB | 11434 | Primary coder — always resident |
| Gemma4-31B | Q8_0 | ~33 GB | 11435 | xAPI/niche domains + speculative decoding showcase |
| Qwen3-32B | Q8_0 | ~34 GB | 11436 | Architecture reasoning + verification (thinking mode) |
| Devstral Small 2 24B | Q8_0 | ~26 GB | 11437 | Agentic test generation |

Combined Q8_0 footprint all four: ~120 GB. Practical approach: Qwen3.6-27B always resident;
others started on demand. Qwen3.6-27B + Gemma4-31B simultaneously = ~60 GB — comfortable.
Any three simultaneously = ~85–94 GB — fits. All four = ~120 GB — fits but tight with KV cache.

**GGUF download sources (do not use Ollama blobs — they are sharded tensors, not standard GGUF):**

- Qwen3.6-27B Q8_0: `Qwen/Qwen3.6-27B-GGUF` on HuggingFace (or unsloth variant)
- Gemma4-31B Q8_0: `google/gemma-4-27b-it-GGUF` or `unsloth/gemma-4-27b-it-GGUF` — use the
  coding/instruct variant; if only BF16 is available, Q8_0 quantize locally with `llama-quantize`
- Qwen3-32B Q8_0: `Qwen/Qwen3-32B-GGUF` on HuggingFace (or unsloth variant)
- Devstral Small 2 24B Q8_0: `bartowski/Devstral-Small-2-24B-Instruct-GGUF` or
  `unsloth/Devstral-Small-2-24B-Instruct-GGUF` on HuggingFace

Store all GGUFs in `~/.local/share/llama/models/` (create if not exists).

---

## Task

**Step 0 — COMPLETE ✓**

Evaluated 2026-06-05. Migration confirmed worthwhile.

- llama.cpp b9430 (stable Homebrew) supports MTP speculative decoding via `--spec-type draft-mtp`
  and `--spec-draft-n-max`. Requires b9180+; b9430 satisfies this.
- `brew install llama.cpp` (stable) is correct — no HEAD build needed for M5 Max.
- MTP works on Apple Silicon Metal. Earlier open issue (#23752) was closed as not factual.
- `--flash-attn` now requires an explicit value: use `--flash-attn on` (not bare `--flash-attn`).

**Benchmark results on M5 Max 128 GB (Qwen3.6-27B Q8_0, 200 tokens, coding prompt):**

| Config | Generation | Speedup |
|---|---|---|
| Baseline (no MTP) | 17.4 t/s | 1.0× |
| `--spec-draft-n-max 1` | 28.7 t/s | 1.65× |
| `--spec-draft-n-max 2` | 31.8 t/s | 1.83× |
| `--spec-draft-n-max 3` | 36.7 t/s | 2.11× |
| `--spec-draft-n-max 4` | **37.5 t/s** | **2.16× ← optimal** |
| `--spec-draft-n-max 5` | 32.4 t/s | 1.86× |

**Optimal MTP flag: `--spec-draft-n-max 4`** — curve peaks here, drops at 5.

**MTP GGUF note:** Standard Q8_0 GGUFs include MTP heads for Qwen3.6. Download from
`unsloth/Qwen3.6-27B-MTP-GGUF` (not a plain Qwen3.6 repo). Single file: `Qwen3.6-27B-Q8_0.gguf` (29 GB).
Use `curl -L` for downloads — no huggingface-cli needed.

---

**Step 1 — COMPLETE ✓**

`brew install llama.cpp` installed b9430. Confirmed: `llama-server --version` returns `9430 (d48a56eff)`.
Metal acceleration confirmed (built for Darwin arm64 with AppleClang).

---

**Step 2 — Qwen3.6-27B COMPLETE ✓**

Downloaded `Qwen3.6-27B-Q8_0.gguf` (29 GB) to `~/.local/share/llama/models/`.
Remaining models (Gemma4-31B, Qwen3-32B, Devstral Small 2 24B) — download as needed in later steps.

Download command template:
```bash
hf download <org>/<repo> <filename>.gguf \
  --local-dir ~/.local/share/llama/models \
  --local-dir-use-symlinks false
```

---

**Step 1 — Install llama.cpp and hf.**

```bash
brew install llama.cpp
brew install hf
```

- `hf` is the HuggingFace Hub CLI (Homebrew formula, formerly `huggingface-cli`). Used for all
  model downloads. No pip or uv required.
- Confirm `llama-server --version` works after install.
- Confirm Metal acceleration is active: the server startup log should show `Metal` backend.

---

**Step 2 — Download GGUFs.**

Use `hf download` with `--local-dir` to store files directly in `~/.local/share/llama/models/`
with their original filenames. Without `--local-dir`, `hf` caches to
`~/.cache/huggingface/hub/models--<org>--<repo>/snapshots/<hash>/` — a nested structure
designed for Python/transformers use that is not suitable for direct llama.cpp paths.

```bash
# Template — always use --local-dir and --local-dir-use-symlinks false
hf download <org>/<repo> <filename>.gguf \
  --local-dir ~/.local/share/llama/models \
  --local-dir-use-symlinks false
```

`--local-dir-use-symlinks false` writes the actual file rather than a symlink into the cache,
so the model is self-contained at that path.

Do not download all four at once — confirm each download before starting the next.
Qwen3.6-27B first (it's the primary model and smallest).

---

**Step 3 — Test each model manually before configuring as a service.**

For each model, run `llama-server` directly in the foreground and send a test request:

```bash
# Example for Qwen3.6-27B — adjust flags per model
llama-server \
  --model ~/.local/share/llama/models/Qwen3.6-27B-Q8_0.gguf \
  --ctx-size 131072 \
  --batch-size 512 \
  --flash-attn on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --spec-type draft-mtp \
  --spec-draft-n-max 4 \
  --host 127.0.0.1 \
  --port 11434

# Test in another terminal
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-27b","messages":[{"role":"user","content":"Reply with one word: ready"}]}'
```

Verify: response is valid JSON, `choices[0].message.content` is non-empty, no errors in server log.

---

**Step 4 — Configure speculative decoding for Gemma4-31B.**

Gemma4's MTP implementation differs from Qwen3.6. It requires a **separate assistant head GGUF**
loaded via `--mtp-head`, not `--spec-draft-n-max`. Download both the base model and the assistant
head from HuggingFace. The `--draft-max` flag referenced in earlier versions of this doc is removed
in b9430 — use `--spec-draft-n-max` instead.

Run the same 4-value n-max benchmark as Qwen3.6 to find the optimal value on this hardware before
baking it into the LaunchAgent plist. Use `llama-cli` (not `llama-server`) for the benchmark, same
as the Qwen3.6 test.

```bash
# With speculative decoding (benchmark starting point — tune --spec-draft-n-max empirically)
llama-server \
  --model ~/.local/share/llama/models/gemma4-31b-q8_0.gguf \
  --ctx-size 131072 \
  --batch-size 512 \
  --flash-attn on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --spec-draft-n-max 4 \
  --host 127.0.0.1 \
  --port 11435
```

---

**Step 5 — Create LaunchAgent plists (one per model) in the dotfiles.**

Location: `~/.dotfiles/llama/Library/LaunchAgents/` — new stow package `llama`.

Requirements per plist:
- `Label`: `com.llama.<modelname>` (e.g. `com.llama.qwen3-6-27b`)
- `RunAtLoad: false` — manual start only, consistent with existing Ollama plist convention
- `KeepAlive: false`
- `StandardOutPath` / `StandardErrorPath`: `/tmp/llama-<modelname>.log`
  (so `tail -f /tmp/llama-<modelname>.log` gives realtime output)
- All llama-server flags encoded in `ProgramArguments` (not env vars where possible)
- Each model on its own port (11434–11437 per table above)

---

**Step 6 — Create convenience shell scripts.**

In `~/.dotfiles/llama/.local/bin/` (stowed to `~/.local/bin/`), create:

- `llama-start <modelname>` — loads the LaunchAgent for that model
- `llama-stop <modelname>` — unloads it
- `llama-log <modelname>` — runs `tail -f /tmp/llama-<modelname>.log`
- `llama-status` — shows which model servers are currently running (check for listening ports)

Model name aliases should be short: `qwen`, `gemma`, `qwen32`, `devstral`.

---

**Step 7 — Update pi agent's models.json.**

File: `~/.dotfiles/pi/.pi/agent/models.json`

Replace the current `ollama` provider with a `llama` provider. Each model needs its own
`baseUrl` since each `llama-server` instance runs on a separate port. Determine whether
pi's models.json format supports multiple providers or multiple baseUrls per model — read
the existing file structure carefully before changing it.

Preserve all existing model fields: `id`, `name`, `reasoning`, `input`, `contextWindow`,
`maxTokens`, `cost`. Add the two new models (Qwen3-32B, Devstral Small 2 24B) with
appropriate IDs, names, and `reasoning` flags:
- Qwen3-32B: `"reasoning": true` (has thinking mode)
- Devstral Small 2 24B: `"reasoning": false`

After updating, run the pi agent quality gate:
```bash
cd ~/.dotfiles/pi/.pi/agent && bash tests/check.sh
```

---

**Step 8 — Stow the new llama package.**

```bash
cd ~/.dotfiles && stow llama
```

Verify symlinks are created:
- `~/Library/LaunchAgents/com.llama.*.plist` → `~/.dotfiles/llama/Library/LaunchAgents/`
- `~/.local/bin/llama-*` → `~/.dotfiles/llama/.local/bin/`

---

**Step 9 — End-to-end test.**

1. Start Qwen3.6-27B: `llama-start qwen`
2. Send a request to `http://localhost:11434/v1/chat/completions` with the same payload
   pi uses in normal operation.
3. Check pi can see and use the model — start a pi session and confirm it responds.
4. Start Gemma4-31B: `llama-start gemma`. Confirm both servers run simultaneously.
5. View logs in realtime: `llama-log qwen` and `llama-log gemma` in separate terminals.
6. Stop both: `llama-stop qwen && llama-stop gemma`.

---

**Step 10 — Remove Ollama from the local machine and dotfiles.**

Only perform this step after step 9 passes completely.

Local machine cleanup:
```bash
launchctl unload ~/Library/LaunchAgents/com.ollama.plist 2>/dev/null
brew uninstall ollama
rm -rf ~/.ollama          # removes all model blobs (~88 GB recovered)
```

Dotfiles cleanup:
```bash
cd ~/.dotfiles
stow --delete ollama      # removes symlinks
rm -rf ollama/            # removes the stow package
```

Commit the removal:
```bash
git add -A
git commit -m "chore(ollama): remove ollama — migrated to llama.cpp"
```

After removal, run `bash ~/.dotfiles/pi/.pi/agent/tests/check.sh` one final time to confirm
nothing in the pi quality gate depended on the ollama package.

---

## Constraints and Preferences

- **No GUI or chat interface.** `llama-server` only — OpenAI API endpoint.
- **No MLX.** The user specifically wants llama.cpp. Do not suggest MLX as an alternative.
- **No MoE models.** All recommended models are dense. Do not substitute MoE variants.
- **Dense models only for llama.cpp on Apple Silicon** — MoE models run 2–3× slower.
- **Start/stop is manual** (`RunAtLoad: false`). The user wants control over which models
  are resident, not automatic startup on login.
- **Logs must be accessible** via `tail -f` without needing to attach to the process.
- **Dotfiles discipline:** new config lives in a `llama` stow package under `~/.dotfiles/llama/`.
  Follow the same pattern as the existing `ollama` stow package.
- **Quality gate:** run `bash ~/.dotfiles/pi/.pi/agent/tests/check.sh` after any change to
  files in `~/.dotfiles/pi/.pi/agent/`.
- **Conventional Commits** for all git commits in this repo.

## Reference files

- `~/.dotfiles/ollama/Library/LaunchAgents/com.ollama.plist` — existing LaunchAgent to model new ones after
- `~/.dotfiles/ollama/gemma4-31b-coding-mtp-optimized` — existing Gemma4 Modelfile (parameter reference)
- `~/.dotfiles/ollama/qwen3.6-27b-coding-optimized` — existing Qwen3.6 Modelfile (parameter reference)
- `~/.dotfiles/pi/.pi/agent/models.json` — pi model registry to update
- `~/.dotfiles/pi/.pi/agent/MODELS.md` — skills-to-models mapping (reference only, no changes needed)
- `~/.dotfiles/pi/.pi/agent/tests/check.sh` — quality gate
