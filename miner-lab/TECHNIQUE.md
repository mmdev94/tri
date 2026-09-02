# Lab technique — P3-007 freeze

## Status

See **`lab/STATUS.md`**. Archival gate family is **score_track=DEAD** (gate1: Q3+Q6 allow, judge sum 0).

| Set | File | Use |
|-----|------|-----|
| Score search (active) | `factors.json` | Put **new** families here |
| Gate (frozen) | `factors.gate.json` | Halo allow regressions only |
| Hot / killed | `factors.hot.json` / `factors.killed.json` | Negative examples |

## Commands

```bash
cat miner-lab/lab/STATUS.md
cat miner-lab/lab/JUDGE-HISTORY.md

# Gate re-probe (optional regression) — expects judge 0
python3 miner-lab/baseline-input.py --mode factors --factors-file miner-lab/factors.gate.json --qids Q3,Q4,Q6

# Archive evolve blocked unless:
python3 miner-lab/evolve-factors.py --force-archive --local-only ...

# Score track: add factors to factors.json, then:
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label score1
bash miner-lab/probe-and-judge.sh --label score1

# Upload only if JUDGE-HISTORY soft-Q sum > 0
```

**Do not submit** archival CASE_NOTE wraps. **Do not** farm archive synonyms for score.
