# miner-lab

**Active path:** PyRIT filter → Halo (± OpenClaw) → `test_template.py` / judge.

```bash
# Stage A-style filter (Q3)
bash miner-lab/pyrit/run.sh --question Q3 --stage input --seeds-from factors

# Promote survivor + Stage B judge
python3 miner-lab/test_candidates.py -f miner-lab/candidates.jsonl --mode template --question Q3 --promote best
python3 miner-lab/test_template.py --stage b --question Q3 --label pyrit1

# Direct template test (no PyRIT)
python3 miner-lab/test_template.py --question Q3 --label eas-q3
```

See `miner-lab/pyrit/README.md`. Promptfoo under `miner-lab/promptfoo/` is removed.
