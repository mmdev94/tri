# Miner-lab

**Active:** `pres_security_meeting` (ONE TEMPLATE, P3-007 Q1–Q6).

```bash
python3 miner-lab/test_template.py --label t12
python3 miner-lab/test_template.py --stage a --label t12
```

t12 Stage A: allow **Q1,Q3,Q4,Q5,Q6** (block Q2). Stage B needs OpenClaw `:18789` + judge.

Promptfoo (Halo input + OpenClaw/output guard), Q1–Q6 separately:

```bash
bash miner-lab/promptfoo/run.sh --input-only
bash miner-lab/promptfoo/run.sh --stack-only
```

See `miner-lab/promptfoo/README.md`.
