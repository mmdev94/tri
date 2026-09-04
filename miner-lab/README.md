# miner-lab

**One flow** (`test.py`): generate → save gens → Halo → filter → judge → promote.

```bash
# Full pipeline (default Q3–Q6). Checkpoints after each template.
python3 miner-lab/test.py --n 32 --seed 1 --pyrit-extra 0 --min-allows-judge 3 --promote

# Halo-only sweep first (cheaper)
python3 miner-lab/test.py --stage a --n 32 --seed 1 --pyrit-extra 0

# Resume / judge saved winners (no re-generate; optional --reuse-halo skips re-Halo)
python3 miner-lab/test.py --from miner-lab/lab/test-CHECKPOINT-t.json --reuse-halo --min-allows-judge 4 --promote
python3 miner-lab/test.py --from miner-lab/lab/gens-….jsonl --stage all

python3 miner-lab/test.py --gen frames --frames threat    # older threat-only gens
python3 miner-lab/test.py --dim-strategy full --n 999     # full dimension grid (costly)
```

Artifacts: `lab/gens-*.jsonl` (right after generate), `lab/test-CHECKPOINT-<label>.json` (live), `lab/test-*-<label>.json` + `candidates.jsonl` (final).

Axes (`pyrit/dimensions.py`): role × stake × format × specificity × pressure × audience.  
PyRIT (`pyrit/mutate.py`): Variation / Persuasion / Tone (keeps `{{objective}}`).  
`--promote` only if **judge_sum > 0**. Default skips Q1/Q2.

Needs `CHUTES_API_KEY` + OpenClaw for judge.
