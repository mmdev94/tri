---
name: miner-lab-test
description: >-
  One-shot Trishool miner testing via miner-lab/test.py: bare objective,
  industry preambles, Halo, judge. Prefer this over multi-step PyRIT CLIs.
  Do not author jailbreak prompts; only harness fixes.
---

# miner-lab/test.py

```bash
python3 miner-lab/test.py                  # lowest-risk Q
python3 miner-lab/test.py --question Q3 --n 12 --promote
python3 miner-lab/test.py --auto-all
python3 miner-lab/test.py --stage a        # Halo only
```

Starts from challenge **objective only** (no seed wraps). Risk order: Q3→Q4→Q6→Q1→Q5→Q2.
