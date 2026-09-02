# Miner-lab — VPS eval + shareable score history

Iterate a Surface Area 1 **TEMPLATE** submission on a VPS, keep **detailed local logs**, and continuously update **shareable score summaries**.

## Layout

| Path | Purpose |
|------|---------|
| `submission.json` | Your live template (edit this) |
| `TECHNIQUE.md` | Design checklist + challenge rules |
| `run-vps-eval.sh` | One-command health → guard probe → eval → summarize |
| `summarize_report.py` | Builds Markdown + history from `report.json` |
| `shared/LATEST-SUMMARY.md` | **Share this** (scores only, no full model dumps) |
| `shared/HISTORY.md` | Append-only score table across runs |
| `../results/miner-lab/runs/<id>/` | Full logs (`console.log`, `report.json`, previews) — **gitignored** |

## VPS setup (once)

```bash
# On the VPS, from repo root
cp .env.example .env
cp .env.tri-claw.example .env.tri-claw
cp .env.tri-judge.example .env.tri-judge
# Fill: OPENCLAW_GATEWAY_PASSWORD (same in .env + .env.tri-claw), CHUTES_API_KEY

bash docker-up.sh
# Wait ~60s for OpenClaw :18789 and Judge :8080

cd tri-check && pnpm install && cd ..
chmod +x miner-lab/run-vps-eval.sh
```

**You need `CHUTES_API_KEY`** for production-like runs (agent + Chutes Halo input/output). Local Halo (`--local`) is optional and does **not** replace the agent key.

## Run (each iteration)

```bash
# Full pipeline (Chutes guards + OpenClaw + Judge)
bash miner-lab/run-vps-eval.sh --label v1

# After editing submission.json
bash miner-lab/run-vps-eval.sh --label v2-masking

# Guard probes only (faster)
bash miner-lab/run-vps-eval.sh --guard-only --label probe1

# Q7–Q12 with fixture ground-truth merge (after docker-up generated fixtures)
bash miner-lab/run-vps-eval.sh --ground-truth --label gt1
```

## Where to look

```bash
# Shareable (safe to paste / commit)
cat miner-lab/shared/LATEST-SUMMARY.md
cat miner-lab/shared/HISTORY.md

# Full detail on the VPS
ls -la results/miner-lab/LATEST/
less results/miner-lab/LATEST/SUMMARY.md
less results/miner-lab/LATEST/console.log
```

Each run directory contains:

- `submission.json` — snapshot of the template used
- `meta.json` — host, git sha, mode, URLs
- `guard-probe.log` — input/output Halo probes
- `report.json` — raw tri-check output
- `SUMMARY.md` / `summary.json` — scored table with response previews
- `console.log` — full tee of the run

## Continuous update / share

1. Keep iterating `submission.json` on the VPS.
2. Re-run `run-vps-eval.sh --label …` after each change.
3. Pull or copy **`miner-lab/shared/`** to collaborators (scores + history only).
4. Optionally commit `shared/HISTORY.md` + `shared/LATEST-SUMMARY.md` when scores improve.
5. Do **not** commit `results/miner-lab/` (may contain long model outputs / secrets from fixtures).

## English-only

Owner confirmed: **input and output must be English**. The runner warns if CJK appears in the template.

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

Only upload after local scores look stable across questions.
