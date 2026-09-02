# Miner-lab — systematic TEMPLATE mining

**Vision:** measure Halo input first → promote quiet wraps → one-Q eval → full eval → submit.  
Challenges rotate ~weekly; keep the method, retire burned prompts.

## Quick start (VPS)

```bash
bash miner-lab/run-lab.sh p3007
cat miner-lab/lab/LATEST-BASELINE.md

# If a factor allows (or conf drops a lot):
python3 miner-lab/promote-factor.py archive_short --snapshot
bash miner-lab/eval-one.sh Q6 --label try1

# Only later:
bash miner-lab/run-vps-eval.sh --label after-allow
```

## Layout

| Path | Purpose |
|------|---------|
| `run-lab.sh` | Sync + bare + factors + soft-Q checks |
| `baseline-input.py` | Input Halo classify (bare / template / factors) |
| `factors.json` | Wrapper variants (`{{objective}}` once each) |
| `promote-factor.py` | Copy a factor → `submission.json` |
| `eval-one.sh` | Full OpenClaw+Judge for **one** Q |
| `run-vps-eval.sh` | Full 6-Q pipeline |
| `submission.json` | Live template (default = measured `archive_short`) |
| `lab/` | Baselines + `NOTEBOOK.md` |
| `challenges/` | Synced from `apiv2.trishool.ai` |
| `shared/` | Shareable full-eval scores |

## VPS setup (once)

```bash
# env: OPENCLAW_GATEWAY_PASSWORD, CHUTES_API_KEY
bash docker-up.sh   # or DinD: run images without bind mounts
cd tri-check && pnpm install && cd ..
chmod +x miner-lab/*.sh miner-lab/*.py
```

After changing `tri-claw/docker/openclaw.lean.json`, rebuild/recreate OpenClaw (config baked in).

## English-only

Input and output must be English (owner-confirmed).

## Upload

```bash
python -m alignet.cli.miner upload \
  --submission-file miner-lab/submission.json \
  --surface-area 1 \
  --coldkey YOUR_COLD --hotkey YOUR_HOT \
  --network finney --netuid 23 \
  --api-url https://api.trishool.ai
```

Upload only after local allows + meaningful judge scores — not after all input blocks.

Details: `TECHNIQUE.md`.
