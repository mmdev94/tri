# Promptfoo: Halo input + OpenClaw (output guard)

Tests **each P3-007 question separately** (Q1–Q6 objectives included as `vars.objective`).  
A wrap that **clears both guards** on **one** Q is the first filter — not a judge score.

HF `huggingface:chat:...` only hits a chat model. **It does not run Halo.**  
Use these configs instead.

## Two evals

| Config | What it hits |
|--------|----------------|
| `promptfooconfig.halo-input.yaml` | `astroboi-halo-guard` `/v1/classify` `role=input` |
| `promptfooconfig.openclaw.yaml` | OpenClaw `:18789` → input Halo → Qwen → **output Halo** |

Output guard only runs if **input allows** and the model generates.

## Run

```bash
# add wraps in miner-lab/promptfoo/wraps.json  (must contain {{objective}})
python3 miner-lab/promptfoo/build_tests.py

bash miner-lab/promptfoo/run.sh --input-only
bash miner-lab/promptfoo/run.sh --stack-only   # needs OpenClaw
bash miner-lab/promptfoo/run.sh --qid Q5
```

Env (already in `.env` / `.env.tri-claw`): `CHUTES_API_KEY`, `OPENCLAW_GATEWAY_PASSWORD`, optional `OPENCLAW_URL`.

## How to read results

- **INPUT_ALLOW** (halo-input pass) = classify did not block that wrap×Q.
- **INPUT_BLOCK** on OpenClaw = never reached output guard.
- **OUTPUT_BLOCK** = `Blocked by output guard model.` (latched).
- **CLEARED_GUARDS** = both Halo layers allowed. Still run `eval-one.sh Qn` for **judge 0/1/2**.

Do not paste API tokens into YAML. Do not commit `.env`.
