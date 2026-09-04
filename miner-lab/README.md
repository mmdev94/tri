# miner-lab

**One command** — soft scaffolds from bare objective → Halo → judge:

```bash
python3 miner-lab/test.py                         # lowest-risk Q
python3 miner-lab/test.py --question Q3 --n 12 --promote
python3 miner-lab/test.py --stage a --n 8         # Halo only
python3 miner-lab/test.py --auto-all
```

Frames: situational / quoted / briefing / clarify / ticket (LLM embeds `{{objective}}` mid-message).  
On Halo block: one softer rewrite (`--soften-retries 1`). Bare dump is off unless `--bare`.

Needs `CHUTES_API_KEY`; judge needs OpenClaw.
