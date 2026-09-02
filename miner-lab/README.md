# Miner-lab

**Batch search (recommended):**

```bash
python3 miner-lab/evolve-factors.py --mode explore --generations 4 --per-gen 8 --merge --label evo7
bash miner-lab/batch-search.sh --label b7 --max-judge 8
```

- Stage A = Halo on all `factors.json`  
- Stage B = `probe-and-judge` on survivors (skips CASE_NOTE by default)  
- Upload only if `lab/BATCH-HIT.txt` appears (judge sum > 0)

See `lab/STATUS.md`.
