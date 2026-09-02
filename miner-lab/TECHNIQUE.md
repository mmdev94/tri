# Lab technique — P3-007

## Batch loop

```bash
python3 miner-lab/evolve-factors.py --mode explore --generations 4 --per-gen 8 --merge --label evoN
bash miner-lab/batch-search.sh --label bN --max-judge 8
```

Evolve fitness = **Halo input only**. Judge fitness = Stage B. Do not promote from evolve alone.

## Walls

| Family | Input | Judge |
|--------|-------|-------|
| CASE_NOTE / island_* | soft allow | **0** (dead) |
| fulfill-style x_* | usually block | n/a until allow |

## Files

| File | Role |
|------|------|
| `factors.json` | Active explore seeds |
| `batch-search.sh` | Stage A→B |
| `evolve-factors.py --mode explore` | LLM invent wraps |
| `factors.killed.json` | Dead (ae_*, island_*) |
