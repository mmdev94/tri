# PyRIT miner-lab (replaces Promptfoo)

Generate / mutate TEMPLATEs with [PyRIT](https://github.com/microsoft/PyRIT), then filter against the **real SN23 stack**.

| Stage | What | Pass means |
|-------|------|------------|
| **attack** | PyRIT LLM converters + multi-turn (Crescendo/PAIR/RedTeam) | new `{{objective}}` scaffolds |
| **input** | Halo input classify | expanded prompt **allow** |
| **stack** | OpenClaw (Halo in → chat → Halo out) | not output-blocked |
| **score** | `test_template.py` Stage B / `eval-one.sh` | judge 0/1/2 |

**Attacker LLM** = Chutes `llm.chutes.ai` (no Halo) — generates / scores attacks.  
**Objective target** = OpenClaw (full guards).  
HF-direct is optional sandbox only.

## Setup

```bash
python3 -m venv miner-lab/pyrit/.venv
miner-lab/pyrit/.venv/bin/pip install -r miner-lab/pyrit/requirements.txt
```

Env (`.env`): `CHUTES_API_KEY`, `OPENCLAW_GATEWAY_PASSWORD`, optional:

- `CHUTES_ATTACK_MODEL` / `EVOLVE_LLM_MODEL` (default `Qwen/Qwen3.8-27B-TEE`)
- `CHUTES_LLM_URL` (default `https://llm.chutes.ai/v1`)
- `OPENCLAW_URL` (default `http://127.0.0.1:18789`)

## Advanced attacks (start here if you are not a red-teamer)

```bash
# LLM rewrites of your scaffolds (Variation + Persuasion + Tone) → Halo filter
bash miner-lab/pyrit/run.sh attack --mode llm --question Q3 --seeds-from factors

# Multi-turn Crescendo vs OpenClaw (needs claw up), templatize user turns → Halo
bash miner-lab/pyrit/run.sh attack --mode crescendo --question Q3 --max-turns 5

# PAIR (tree search — slower/costlier)
bash miner-lab/pyrit/run.sh attack --mode pair --question Q3 --tree-width 2 --tree-depth 3

# LLM mutation + Crescendo
bash miner-lab/pyrit/run.sh attack --mode all --questions Q3,Q6 --label atk1
```

Then score:

```bash
python3 miner-lab/test_candidates.py -f miner-lab/candidates.jsonl --mode template --question Q3 --promote best
python3 miner-lab/test_template.py --stage b --question Q3 --label atk1
```

## Simple filter (no attack generation)

```bash
bash miner-lab/pyrit/run.sh filter --question Q3 --stage input --seeds-from factors
bash miner-lab/pyrit/run.sh filter --questions Q3,Q5 --stage stack --also-output-classify
```

Dumb obfuscation (`--convert leet,rot13`) usually **hurts** Halo allow — prefer `--mode llm` attacks.

## Layout

- `run_attacks.py` — crescendo / PAIR / redteam / LLM converters
- `run_filter.py` — Halo ± OpenClaw filter on seeds
- `llm_targets.py` — OpenClaw + Chutes attacker targets
- `templatize.py` — expanded prompt → `{{objective}}` TEMPLATE
- `convert_templates.py` — deterministic converters (leet/…)
- `SKILL.md` — Cursor agent notes
