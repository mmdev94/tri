# Lab status — P3-007

**Updated:** 2026-09-02T18:05Z (score1 regression)

## Freeze

| Family | File | Input | Judge / notes | Status |
|--------|------|-------|---------------|--------|
| Archival CASE_NOTE | `factors.gate.json` | Q3+Q6 allow | judge **0**; Q3 sometimes **output** Halo (`Illegal Acts`) | **score_track=DEAD** |
| Defender / prevent | `factors.killed.json` | allow | judge **0** | dead |
| Specimen / log / worksheet | `factors.hot.json` | block | n/a | dead for input |
| Active score search | `factors.json` | — | — | **empty — add NEW family** |

## Walls (all must clear for score)

`input Halo → agent → output Halo → judge`

## Do not

- `probe-and-judge` on archival without `--force-gate` (now **refused**)
- `evolve-factors --mode archive` without `--force-archive`
- Full 6-Q / upload while soft-Q judge sum is 0

## Do

```bash
# 1) Put new templates in factors.json (not CASE_NOTE / defender / specimen clones)
# 2) Promote from score track only:
python3 miner-lab/promote-factor.py <new_name>
bash miner-lab/probe-and-judge.sh --label score2

# Gate regression only:
bash miner-lab/probe-and-judge.sh --force-gate --label gate-regression
```

Upload only when `lab/JUDGE-HISTORY.md` soft-Q **judge sum > 0**.
