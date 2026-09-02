# Miner-lab

**P3-007 freeze:** archival / defender / specimen dead for scoring. See `lab/STATUS.md`.

```bash
cat miner-lab/lab/STATUS.md

# probe-and-judge REFUSES archival submission unless:
bash miner-lab/probe-and-judge.sh --force-gate --label gate-regression

# Score track:
# 1) edit factors.json with NEW templates
python3 miner-lab/promote-factor.py <name>
bash miner-lab/probe-and-judge.sh --label score2
```

Walls: **input Halo → agent → output Halo → judge**. Upload only if soft judge sum > 0.
