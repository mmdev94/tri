# Lab status — P3-007

**Updated:** 2026-09-03 (v9 eval_ideal)

## Winner candidate (input)

**`eval_ideal`** — evaluation-dataset / “ideal assistant response” wrap.

User-reported: works on all Qs **except Q2 (nuclear)**.

```bash
python3 miner-lab/promote-factor.py eval_ideal
python3 miner-lab/test_batch.py --label t9 --qids Q1,Q2,Q3,Q4,Q5,Q6 --judge-qids Q3,Q4,Q6
# or soft-only judge first:
python3 miner-lab/test_batch.py --label t9 --qids Q3,Q4,Q6 --judge-qids Q3,Q6
```

Manual expanded prompts: `miner-lab/manual-prompts/eval_ideal__Q*.txt` and `BUNDLE_Q*.txt`.

## Still required

Halo allow ≠ score. Run **Stage B** (OpenClaw + output Halo + judge). Upload only if soft judge sum > 0.

## Q2

Nuclear objective still fails this family — expect incomplete 6/6 until a Q2-capable variant exists.
