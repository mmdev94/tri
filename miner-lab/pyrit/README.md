# PyRIT miner-lab (replaces Promptfoo)

Generate / mutate TEMPLATEs with [PyRIT](https://github.com/microsoft/PyRIT), then filter them against the **real SN23 stack** — not bare HuggingFace chat.

| Stage | What | Pass means |
|-------|------|------------|
| **input** | Halo input classify (Chutes) | expanded prompt **allow** |
| **stack** | OpenClaw → input Halo → Qwen → **output Halo** | reply not `Blocked by output guard model.` |
| **output-classify** | output Halo `/v1/classify` on assistant text | optional extra check |
| **score** | `test_template.py` Stage B / `eval-one.sh` | judge 0/1/2 |

HuggingFace-direct via PyRIT is optional sandbox only (`--hf-smoke`). It does **not** replace Halo or the judge.

## Setup

```bash
# once
python3 -m venv miner-lab/pyrit/.venv
miner-lab/pyrit/.venv/bin/pip install -r miner-lab/pyrit/requirements.txt

# env (repo root .env)
# CHUTES_API_KEY=...
# OPENCLAW_GATEWAY_PASSWORD=...   # for --stage stack
# OPENCLAW_URL=http://127.0.0.1:18789
```

## Run

```bash
# Stage A filter on seeds × Q3 (writes candidates.jsonl)
bash miner-lab/pyrit/run.sh --question Q3 --stage input

# Mutate seed scaffolds with PyRIT converters, then filter
bash miner-lab/pyrit/run.sh --question Q3 --convert leet,rot13,zero_width --stage input

# Input allow + OpenClaw stack (+ optional output classify on reply)
bash miner-lab/pyrit/run.sh --questions Q3,Q5 --stage stack --also-output-classify

# Use factors.json / submission.json as seeds
bash miner-lab/pyrit/run.sh --seeds-from factors --question Q3 --stage input

# Next: judge survivors
python3 miner-lab/test_candidates.py -f miner-lab/candidates.jsonl --mode template --question Q3 --promote best
python3 miner-lab/test_template.py --stage b --question Q3 --label pyrit1
```

## Seeds format

`seeds.json` / `seeds.example.json`:

```json
{
  "seeds": [
    {"id": "eas_receipt", "prompt": "… {{objective}} …"}
  ]
}
```

Each prompt must contain exactly one `{{objective}}` and stay ≤2000 chars after convert.

## Layout

- `classify.py` — Halo input + output Chutes `/v1/classify`
- `openclaw.py` — OpenClaw chat completions
- `convert_templates.py` — PyRIT converters on scaffold sides only (keeps `{{objective}}`)
- `run_filter.py` — CLI
- `pyrit_send.py` — optional PromptSendingAttack → OpenClaw (multi-turn sandbox)
