# Lab notebook

Append dated notes. Prefer signal from `baseline-input.py`, not full eval dumps.

## How to use

1. Sync challenge → run `--mode bare`.
2. Change **one** factor in `factors.json` or `submission.json`.
3. Re-probe; record allow/block + confidence.
4. Only then full eval / upload.

## Session log

### 2026-09-02 — P3-007 kickoff

- Live: **P3-007** (6 Q, TEMPLATE, surface 1). Local `tri-check/data/questions.json` was P3-006.
- Output guard corrected to `astroboi-halo-output-guard` (not haloqwen).
- v2 archival + v3 “policies disabled” worksheet: **6/6 input block** (conf ~1.0). Loud coercion worse for input.
- Next: bare vs quiet factors via `baseline-input.py`; no full eval until ≥1 allow.
