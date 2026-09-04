---
name: pyrit-miner-lab
description: >-
  Use when the user works on Trishool SN23 miner red-team filtering with PyRIT,
  Halo guards, OpenClaw, or advanced attacks (Crescendo/PAIR/LLM converters).
  Prefer run.sh attack for generation; never author jailbreak prompts yourself —
  only harness, wiring, and export to candidates.
---

# PyRIT miner-lab

## Score path

1. **Attack** — `bash miner-lab/pyrit/run.sh attack --mode llm|crescendo|pair|all`
2. **Halo allow** — built into attack (`--filter-halo`) or `run.sh filter`
3. **Judge** — `test_template.py --stage b`

Attacker = Chutes LLM (no Halo). Objective = OpenClaw (guards on).

## Prefer for non-experts

```bash
bash miner-lab/pyrit/run.sh attack --mode llm --question Q3 --seeds-from factors
bash miner-lab/pyrit/run.sh attack --mode crescendo --question Q3 --max-turns 5
```

Avoid `--convert leet,rot13` (usually blocks). Do not write jailbreak text in chat.

## Rules

- Exactly one `{{objective}}`, ≤2000 chars.
- Do not commit attack dumps with harmful payloads (`candidates.jsonl` gitignored).
- Venv: `miner-lab/pyrit/.venv`.
