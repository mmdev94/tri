# Miner-lab

**P3-007:** archival / defender / specimen families are frozen (see `lab/STATUS.md`).

```bash
cat miner-lab/lab/STATUS.md

# New score-track factors go in factors.json (currently empty on purpose)
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label score1
bash miner-lab/probe-and-judge.sh --label score1
```

Gate-only: `--factors-file miner-lab/factors.gate.json`  
Archive evolve: requires `--force-archive`  
Promote from gate: requires `--allow-gate`
