# miner-lab

**One command** — soft scaffolds from bare objective → Halo → judge:

```bash
python3 miner-lab/test.py                         # lowest-risk Q
python3 miner-lab/test.py --question Q3 --n 12 --promote
python3 miner-lab/test.py --stage a --n 8         # Halo only
python3 miner-lab/test.py --auto-all
```

- Soft frames embed `{{objective}}` mid-message; empty/429/502 retries + `--pause` between gens.
- `--promote` only writes `submission.json` when **judge > 0**.
- Needs `CHUTES_API_KEY`; judge needs OpenClaw.
