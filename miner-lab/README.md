# miner-lab

**Active path:** PyRIT **attack** → Halo filter → `test_template.py` / judge.

```bash
# You are not a red-teamer — let PyRIT mutate/attack, then filter:
bash miner-lab/pyrit/run.sh attack --mode llm --question Q3 --seeds-from factors
bash miner-lab/pyrit/run.sh attack --mode crescendo --question Q3 --max-turns 5

python3 miner-lab/test_candidates.py -f miner-lab/candidates.jsonl --mode template --question Q3 --promote best
python3 miner-lab/test_template.py --stage b --question Q3 --label atk1
```

Docs: `miner-lab/pyrit/README.md`. Promptfoo removed (`PROMPTFOO_RETIRED.md`).
