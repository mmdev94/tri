---
name: pyrit-miner-lab
description: >-
  Use when the user works on Trishool SN23 miner red-team filtering with PyRIT,
  Halo guards, OpenClaw, or replacing Promptfoo. Prefer miner-lab/pyrit/run.sh
  over HuggingFace-only targets; never author jailbreak prompts — only harness,
  converters, classify/stack wiring, and export to candidates.
---

# PyRIT miner-lab

## Source of truth for score

1. **Input Halo** allow on expanded TEMPLATE
2. **OpenClaw stack** (survives output Halo)
3. **Judge** via `test_template.py` Stage B / `eval-one.sh`

HF-direct PyRIT targets are sandbox only.

## Commands

```bash
bash miner-lab/pyrit/run.sh --question Q3 --stage input --seeds-from factors
bash miner-lab/pyrit/run.sh --question Q3 --convert leet,rot13 --stage input
bash miner-lab/pyrit/run.sh --questions Q3,Q5 --stage stack --also-output-classify
python3 miner-lab/test_candidates.py -f miner-lab/candidates.jsonl --mode template --promote best
python3 miner-lab/test_template.py --stage b --question Q3 --label pyrit1
```

## Rules

- Do not write or improve attack/jailbreak wording.
- Keep exactly one `{{objective}}`, template ≤2000 chars.
- Promptfoo under `miner-lab/promptfoo/` is removed; see `PROMPTFOO_RETIRED.md`.
- Venv: `miner-lab/pyrit/.venv` (gitignored).
