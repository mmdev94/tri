# Miner-lab — systematic TEMPLATE mining

Measure **input Halo** first. Full OpenClaw evals only after something allows.
Challenges rotate ~weekly — keep the lab method; retire burned prompts.

## Layout

| Path | Purpose |
|------|---------|
| `submission.json` | Live template under test |
| `factors.json` | Quiet A/B wrapper variants for input probes |
| `baseline-input.py` | **Primary:** Chutes input classify baseline / factors |
| `lab/` | Baseline tables + `NOTEBOOK.md` session notes |
| `challenges/` | Live pack from `apiv2.trishool.ai` |
| `sync-challenge.py` | Pull ACTIVE challenge |
| `TECHNIQUE.md` | Weekly loop + rules |
| `run-vps-eval.sh` | Health → probe → full eval → summarize |
| `summarize_report.py` | Markdown + history from `report.json` |
| `shared/` | Shareable scores (`LATEST-SUMMARY.md`, `HISTORY.md`) |
| `../results/miner-lab/runs/<id>/` | Full logs — **gitignored** |

## Weekly workflow (each challenge)

```bash
# 1) Sync live questions (not stale tri-check/data/questions.json)
python3 miner-lab/sync-challenge.py

# 2) Bare objectives → input Halo only
python3 miner-lab/baseline-input.py --mode bare --label bare1
cat miner-lab/lab/LATEST-BASELINE.md

# 3) Factor / template A/B (edit factors.json or submission.json between runs)
python3 miner-lab/baseline-input.py --mode bare,template --label wrap1
python3 miner-lab/baseline-input.py --mode factors --label factors1
python3 miner-lab/baseline-input.py --qid Q3 --mode bare,template,factors

# 4) Only if input allow ≥1 → full stack
bash miner-lab/run-vps-eval.sh --label after-allow
```

See `TECHNIQUE.md` and append findings to `lab/NOTEBOOK.md`.

After changing `tri-claw/docker/openclaw.lean.json` (output guard), rebuild/recreate OpenClaw — config is baked into the image (especially DinD without bind mounts).

## VPS setup (once)

If `docker-up.sh` fails at `pnpm build:plugin-sdk:dts` with `@grammyjs/types` errors, pull latest
repo (uses `pnpm build:lean` in `Dockerfile.lean`) and rebuild:

```bash
bash docker-down.sh 2>/dev/null || true
bash docker-up.sh --no-cache
```

```bash
# On the VPS, from repo root
cp .env.example .env
cp .env.tri-claw.example .env.tri-claw
cp .env.tri-judge.example .env.tri-judge
# Fill: OPENCLAW_GATEWAY_PASSWORD (same in .env + .env.tri-claw), CHUTES_API_KEY

bash docker-up.sh
# Wait ~60s for OpenClaw :18789 and Judge :8080

cd tri-check && pnpm install && cd ..
chmod +x miner-lab/run-vps-eval.sh miner-lab/baseline-input.py miner-lab/sync-challenge.py
```

**You need `CHUTES_API_KEY`** for Chutes Halo + agent. Local Halo (`--local`) is optional.

## Full eval (after input allows)

```bash
bash miner-lab/run-vps-eval.sh --label v1
bash miner-lab/run-vps-eval.sh --guard-only --label probe1   # template Q1 probe only
```

## Where to look

```bash
cat miner-lab/lab/LATEST-BASELINE.md    # input allow/block table
cat miner-lab/lab/NOTEBOOK.md
cat miner-lab/shared/LATEST-SUMMARY.md  # full-eval scores
cat miner-lab/shared/HISTORY.md
ls -la results/miner-lab/LATEST/
```

## Continuous update / share

1. Iterate factors / `submission.json` using **baseline-input**, not blind full evals.
2. Snapshot improving templates as `submission.vN-*.json`.
3. Share `shared/` + `lab/LATEST-BASELINE.md` (no full harmful model dumps).
4. Do **not** commit `results/miner-lab/` (long outputs / fixture secrets).

## English-only

Owner confirmed: **input and output must be English**.

## Upload when ready

```bash
python -m alignet.cli.miner upload \
  --submission-file miner-lab/submission.json \
  --surface-area 1 \
  --coldkey YOUR_COLD \
  --hotkey YOUR_HOT \
  --network finney \
  --netuid 23 \
  --api-url https://api.trishool.ai
```

Only upload after local scores look meaningful (not all input blocks).
