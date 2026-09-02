# Miner-lab

**score2c:** near-ae / CASE_NOTE mutants are **dead** (Q3 output block, Q6 judge 0). See `lab/STATUS.md`.

```bash
cat miner-lab/lab/STATUS.md
# factors.json is empty — add a NEW family, then:
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label score3
python3 miner-lab/promote-factor.py <name>
bash miner-lab/probe-and-judge.sh --label score3 --qids Q3,Q6
```

Walls: **input → agent → output → judge**. Upload only if soft judge sum > 0.
