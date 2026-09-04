# miner-lab

**One flow** (`test.py`): **ATTACK → FILTER (Halo) → EVAL (judge)** → promote.

```bash
# Fresh search (dimensions + optional PyRIT)
python3 miner-lab/test.py --n 32 --seed 1 --pyrit-extra 0 --min-allows-judge 3 --promote

# Improve complementary winners (d15×d29 style): crossover + mutate → Halo → judge
python3 miner-lab/test.py \
  --from miner-lab/lab/test-20260904T173843Z-t.json \
  --attack crossover --n 12 --pyrit-extra 16 --min-allows-judge 3 --promote

# Mutate winners only (no hybrid LLM)
python3 miner-lab/test.py --from miner-lab/lab/test-….json --attack mutate --pyrit-extra 24 --promote

# Re-score saved templates as-is
python3 miner-lab/test.py --from miner-lab/lab/test-….json --attack none --reuse-halo --min-allows-judge 4

# Halo-only sweep
python3 miner-lab/test.py --stage a --n 32 --seed 1 --pyrit-extra 0
```

| Phase | What |
|-------|------|
| **ATTACK** | `dimensions` / `frames` / `crossover` / `mutate` / `none` |
| **FILTER** | Halo on every template; checkpoint `lab/test-CHECKPOINT-<label>.json` |
| **EVAL** | Judge only `n_allow >= --min-allows-judge` |

With `--from`, default `--attack` is **crossover** (picks complementary parents by prior `judge_hits`).  
Without `--from`, default is **dimensions**.

Artifacts: `lab/gens-*.jsonl`, checkpoint, `lab/test-*-<label>.json`, `candidates.jsonl`.  
`--promote` only if **judge_sum > 0** (prefers wider Q hit coverage).

Needs `CHUTES_API_KEY` + OpenClaw for judge.
