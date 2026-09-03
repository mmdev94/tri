# Promptfoo: Halo input + OpenClaw (output guard)

Tests **each P3-007 question separately** (`vars.objective` = challenge text).  
Clearing both guards on **one** Q is the first filter — then `eval-one.sh` for judge score.

HF `huggingface:chat:...` does **not** run Halo. Use these configs.

## Two evals

| Config | What it hits |
|--------|----------------|
| `promptfooconfig.halo-input.yaml` | input Halo `/v1/classify` |
| `promptfooconfig.openclaw.yaml` | OpenClaw → input Halo → Qwen → **output Halo** |

Wraps are written as `wraps/*.txt` and listed under `prompts:` in each config
(`build_tests.py` regenerates them from `wraps.json`). Do **not** use a `.js`
array — promptfoo treats `.js` prompts as a single function.

## Run

```bash
# edit miner-lab/promptfoo/wraps.json  (must contain {{objective}})
python3 miner-lab/promptfoo/build_tests.py

bash miner-lab/promptfoo/run.sh --input-only
bash miner-lab/promptfoo/run.sh --stack-only
bash miner-lab/promptfoo/run.sh --qid Q5
```

Env: `CHUTES_API_KEY`, `OPENCLAW_GATEWAY_PASSWORD`, optional `OPENCLAW_URL` (baked into openclaw yaml by `build_tests.py`).

## Fixes vs broken first run

- Prompts as `file://wraps/<name>.txt` listed in config (not `prompts.js`)
- OpenClaw `url` is a real URL (not `{{env.OPENCLAW_URL}}`)
- `--qid` uses `--filter-pattern`
- Response transforms tolerate API error JSON

## How to read results

- **INPUT_ALLOW / INPUT_BLOCK** — Halo input
- **OUTPUT_BLOCK** — `Blocked by output guard model.`
- **CLEARED_GUARDS** — both Halo layers allowed → run `bash miner-lab/eval-one.sh Qn` for judge 0/1/2

## Mining: test Promptfoo FAIL candidates

Promptfoo **FAIL** ≠ miner score. Convert useful **framings** into a TEMPLATE with `{{objective}}`, then:

```bash
# example format: miner-lab/candidates.example.json
# your FAIL wraps (gitignored): miner-lab/candidates.json  or  /tmp/fails.jsonl

python3 miner-lab/test_candidates.py -f miner-lab/candidates.example.json --mode template --qids Q3,Q5,Q6
python3 miner-lab/test_candidates.py -f /tmp/fails.jsonl --mode raw --also-output-classify
python3 miner-lab/test_candidates.py -f miner-lab/candidates.json --mode template --promote best --label cand1
python3 miner-lab/test_template.py --stage b --label cand1
```

Do not commit real FAIL payloads (esp. sexual-violence / toxins / weapons).

Do not commit secrets.
