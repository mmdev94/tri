# Miner-lab — systematic TEMPLATE mining

**Vision:** Halo measure → hybrid wraps (not pure defender) → evolve with early death → eval-one → submit.

## Quick start

```bash
bash miner-lab/run-lab.sh p3007
python3 miner-lab/evolve-factors.py --generations 2 --per-gen 4 --merge --promote-best
cat miner-lab/lab/LATEST-EVOLVE.md

bash miner-lab/eval-one.sh Q6 --label hybrid1
bash miner-lab/eval-one.sh Q4 --label hybrid1
```

Pure `defender_overview` **allows input but judge=0** — retired to `factors.killed.json`.

## Layout

| Path | Purpose |
|------|---------|
| `factors.json` | Active hybrids |
| `factors.killed.json` | Retired / negative examples |
| `evolve-factors.py` | LLM/local mutate + Halo early death |
| `baseline-input.py` | Input classify |
| `promote-factor.py` | Factor → submission |
| `eval-one.sh` | One-Q full stack |
| `run-lab.sh` / `run-vps-eval.sh` | Lab pass / full 6-Q |

## Upload

Only after local **allows + judge > 0** on at least one Q.

Details: `TECHNIQUE.md`.
