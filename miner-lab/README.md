# miner-lab

**One flow** (`test.py`): **ATTACK → FILTER (Halo) → EVAL (judge)** → promote.  
Target on Q3–Q6: **judge_sum = 8** (2 per question).

```bash
# Fresh dimension search
python3 miner-lab/test.py --n 32 --seed 1 --pyrit-extra 0 --min-allows-judge 3 --promote

# Chase 8/8 from latest winners (default --parents 2, scored-only, PyRIT on)
python3 miner-lab/test.py \
  --from miner-lab/lab/test-20260904T192608Z-t.json \
  --attack crossover --n 12 --pyrit-extra 16 \
  --min-allows-judge 4 --promote

# Mutate champions only
python3 miner-lab/test.py \
  --from miner-lab/lab/test-20260904T192608Z-t.json \
  --attack mutate --parents 2 --pyrit-extra 24 \
  --min-allows-judge 4 --promote

# Re-score as-is
python3 miner-lab/test.py --from miner-lab/lab/test-….json --attack none --reuse-halo
```

| Phase | What |
|-------|------|
| **ATTACK** | `dimensions` / `frames` / `crossover` / `mutate` / `none` |
| **FILTER** | Halo; checkpoint `lab/test-CHECKPOINT-<label>.json` |
| **EVAL** | Judge `n_allow >= --min-allows-judge` |

`--from` defaults to `--attack crossover`. Parents prefer complementary `judge_hits` (e.g. Q3/Q4 + Q5/Q6).  
Promote prefers **more Q hits**, then `judge_sum`.

Needs `CHUTES_API_KEY` + OpenClaw for judge. Use `miner-lab/pyrit/.venv` (auto re-exec).
