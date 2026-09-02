# Solution technique — two tracks

## Gate track vs score track (P3-007 measured)

| Track | Goal | What works | Stop when |
|-------|------|------------|-----------|
| **Gate** | Halo input allow | `archive_evidence` (Q3+Q6), tiny evo synonyms | Conf/allows plateau |
| **Score** | Judge ≥1 | Needs elicitation Halo usually **blocks** | Don’t confuse with gate wins |

Archival CASE_NOTE / defender briefs → **allow + judge 0**.  
Specimen/log hybrids → **input block**.  
**Do not submit on input allow alone.**

## Workflow

```bash
# Soft Qs only (skip Q1/Q2 burns)
python3 miner-lab/baseline-input.py --mode factors --qids Q3,Q4,Q6 --label soft

# Evolve archive neighborhood (gate only)
python3 miner-lab/evolve-factors.py --local-only --generations 4 --per-gen 8 --merge --promote-best

# Bridge: probe allows → eval-one each → JUDGE-HISTORY.md
bash miner-lab/probe-and-judge.sh --label gate1

# Full 6-Q only if judge sum > 0 on soft Qs
bash miner-lab/run-vps-eval.sh --label scored
```

Default submission seed: **`archive_evidence`** (best measured multi-allow).

## Files

- `probe-and-judge.sh` — Halo template probe + eval-one on allows  
- `lab/JUDGE-HISTORY.md` — score track log  
- `factors.json` / `factors.hot.json` / `factors.killed.json`  
- `evolve-factors.py --mode archive` — gate search; tiny deltas warn “gate-only”
