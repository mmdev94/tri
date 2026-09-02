# Lab status — P3-007

**Updated:** 2026-09-02T19:22Z (score6)

## Active

| Factor | Q3 | Q4 | Q6 |
|--------|----|----|-----|
| **`island_numbered`** (promoted) | **allow** | block@0.50 | **allow** |
| `island_specifics` | block@0.73 | block | allow |

`spec_*` fulfill-style → 0 allows → `factors.failed-v5.json`.

## Test on VPS (sync repo first)

```bash
# confirm factors not empty
python3 -c "import json; print([k for k in json.load(open('miner-lab/factors.json')) if not k.startswith('_')])"

python3 miner-lab/promote-factor.py island_numbered
bash miner-lab/probe-and-judge.sh --label score6 --qids Q3,Q6
```

Still expect possible judge 0 (near-CASE_NOTE family). Upload only if soft judge sum > 0.
