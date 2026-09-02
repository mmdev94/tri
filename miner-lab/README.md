# Miner-lab — systematic TEMPLATE mining

**Vision:** quiet archive/mid wraps → evolve with early death → promote only if better → eval-one.

## Quick start

```bash
bash miner-lab/run-lab.sh p3007

python3 miner-lab/evolve-factors.py --local-only --generations 4 --per-gen 8 --merge --promote-best
# Promote is skipped unless fit beats baseline (no more archive_short loops).

python3 miner-lab/baseline-input.py --mode template --qid Q6 --label check
bash miner-lab/eval-one.sh Q6 --label mid1   # only if allow
```

LLM mutate: `python3 miner-lab/evolve-factors.py --generations 3 --per-gen 6 --merge --promote-best`  
(handles `content: null`; `enable_thinking: false`)

## Layout

| Path | Purpose |
|------|---------|
| `factors.json` | Quiet archive + mid |
| `factors.hot.json` | Specimen hybrids (`--mode explore`) |
| `factors.killed.json` | Defender / grammar / v3 |
| `evolve-factors.py` | Archive micro-evolve + early death |
| `baseline-input.py` / `eval-one.sh` / `run-lab.sh` | Measure / one-Q / weekly pass |

Details: `TECHNIQUE.md`.
