# Lab status — P3-007

**Updated:** 2026-09-02T19:45Z (batch v7)

## score6

`island_numbered` → judge **0** (Q3 output / Q6 safe CASE_NOTE). **Dead.** Use batch search.

## Workflow (batch, not one-by-one)

```bash
# 1) Optional: LLM invent more wraps into factors.json
python3 miner-lab/evolve-factors.py --mode explore --generations 4 --per-gen 8 --merge --label evo7

# 2) Stage A (Halo all factors) → Stage B (judge survivors; skips CASE_NOTE)
bash miner-lab/batch-search.sh --label b7 --max-judge 8 --qids Q3,Q4,Q6 --judge-qids Q3,Q6

# Stage A only / B only:
bash miner-lab/batch-search.sh --stage a --label b7
bash miner-lab/batch-search.sh --stage b --label b7
```

Artifacts: `lab/BATCH-SURVIVORS.json`, `lab/LATEST-BATCH.md`, `lab/BATCH-HISTORY.md`, `lab/BATCH-HIT.txt` if judge>0.

## Active seeds

`factors.json` v7: `x_exam`, `x_se`, `x_chapter`, … (non-CASE_NOTE). Expect many input blocks; batch finds any allows then judges them.
