# miner-lab

**One command** (bare objective → industry rewrites → Halo → judge):

```bash
python3 miner-lab/test.py                  # lowest-risk Q only (usually Q3)
python3 miner-lab/test.py --question Q4
python3 miner-lab/test.py --questions Q3,Q4 --n 10 --promote
python3 miner-lab/test.py --auto-all       # all six, low-risk first
python3 miner-lab/test.py --stage a        # Halo only (no OpenClaw)
```

Does **not** use your old seed wraps. Starts from the challenge objective text only.

Needs `CHUTES_API_KEY` in `.env`. Stage B needs OpenClaw. Uses `miner-lab/pyrit/.venv` automatically if present.

Advanced / legacy PyRIT CLIs: `miner-lab/pyrit/README.md`.
