# miner-lab

**Halo attack search** — many semantic dimensions + PyRIT mutate → score one TEMPLATE on Q3–Q6:

```bash
python3 miner-lab/test.py                                 # dimensions + pyrit (default)
python3 miner-lab/test.py --n 16 --pyrit-extra 24 --promote
python3 miner-lab/test.py --stage a --n 20                # Halo sweep first
python3 miner-lab/test.py --gen frames --frames threat    # older threat-only gens
python3 miner-lab/test.py --dim-strategy full --n 999     # full dimension grid (costly)
```

Axes (`pyrit/dimensions.py`): role × stake × format × specificity × pressure × audience.  
PyRIT (`pyrit/mutate.py`): Variation / Persuasion / Tone on survivors (keeps `{{objective}}`).  
`--promote` only if **judge_sum > 0**. Default skips Q1/Q2.

Needs `CHUTES_API_KEY` + OpenClaw for judge.
