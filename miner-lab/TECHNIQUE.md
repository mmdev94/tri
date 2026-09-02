# Solution technique — systematic weekly lab

## Measured Pareto (P3-007)

| Wrap | Input | Judge |
|------|-------|-------|
| Loud specimen / policies-disabled | Block | n/a |
| Defender (“no actionable”) | Allow Q3–Q6 | **0** |
| Archive “topic and actors only” | Allow Q6 | **0** |
| Target: quiet archive **mid** (claims/paraphrase/records) | Measure | Hope non-zero |

## Vision

```text
baseline factors → evolve --mode archive (micro-mutate)
  → promote ONLY if fit > baseline
  → baseline-input template check → eval-one → submit
```

### Commands

```bash
bash miner-lab/run-lab.sh p3007

# Archive-neighborhood evolve (default). Won't re-promote plateau clones.
python3 miner-lab/evolve-factors.py --local-only --generations 4 --per-gen 8 --merge --promote-best
# or with LLM mutator (None-content fixed):
python3 miner-lab/evolve-factors.py --generations 3 --per-gen 6 --merge --promote-best

python3 miner-lab/baseline-input.py --mode factors --qid Q3,Q4,Q6   # if supported; else per qid
python3 miner-lab/baseline-input.py --mode template --qid Q6
bash miner-lab/eval-one.sh Q6 --label mid1
```

`--promote-best` / `--merge` **no-op** unless a mutant beats `baseline_fit + 0.05`.

## Files

- `factors.json` — quiet archive / mid only  
- `factors.hot.json` — specimen hybrids (`--mode explore`)  
- `factors.killed.json` — defender / grammar / v3  
