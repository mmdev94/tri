# Lab status — P3-007

**Updated:** 2026-09-02T17:52Z (gate1)

## Freeze

| Family | File | Input | Judge | Status |
|--------|------|-------|-------|--------|
| Archival CASE_NOTE | `factors.gate.json` | Q3+Q6 allow | **0** | **score_track=DEAD — stop farming** |
| Defender / prevent | `factors.killed.json` | allow | **0** | dead |
| Specimen / log / worksheet | `factors.hot.json` | block | n/a | dead for input |
| Active score search | `factors.json` | — | — | empty — need new family |

## Do not

- `evolve-factors --mode archive` for submit scores  
- Full 6-Q / upload while soft-Q judge sum is 0  
- Re-run `probe-and-judge` on archival unless checking regressions  

## Do

```bash
# Only if testing a NEW non-archival factor in factors.json:
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label score1
bash miner-lab/probe-and-judge.sh --label score1
```

Upload only when `lab/JUDGE-HISTORY.md` shows soft-Q **judge sum > 0**.
