# Miner-lab

**P3-007:** score track = near-`archive_evidence` mutants in `factors.json`. See `lab/STATUS.md`.

```bash
# Best soft-Q input allows so far:
python3 miner-lab/promote-factor.py ae_claims_bullets   # or ae_oversight
# Needs OpenClaw on :18789
bash miner-lab/probe-and-judge.sh --label score2c --qids Q3,Q6
```

Exact gate hash refused without `--force-gate`. Upload only if soft judge sum > 0.
