# Miner-lab

Two tracks: **gate** (Halo allow) ≠ **score** (judge ≥1).

```bash
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label soft
python3 miner-lab/evolve-factors.py --local-only --generations 4 --per-gen 8 --merge --promote-best
bash miner-lab/probe-and-judge.sh --label gate1   # eval-one every soft-Q allow
cat miner-lab/lab/JUDGE-HISTORY.md
```

Only full-eval / upload after soft-Q **judge sum > 0**.

See `TECHNIQUE.md`.
