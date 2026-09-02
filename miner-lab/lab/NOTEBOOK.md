# Lab notebook

## Status

**`lab/STATUS.md`** — archival score_track=DEAD after gate1.

## Session log

### 2026-09-02 — freeze

- `probe-and-judge gate1`: Q3+Q6 allow, judge **0/0**, Q4 block@0.53.
- Frozen archival → `factors.gate.json`; `factors.json` emptied for score search.
- `evolve --mode archive` refuses without `--force-archive`.
- `promote-factor` refuses gate factors without `--allow-gate`.
- Next: invent **non-archival / non-defender / non-specimen** families in `factors.json`, then probe-and-judge. No more CASE_NOTE farming.
