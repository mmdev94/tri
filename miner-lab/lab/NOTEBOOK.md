# Lab notebook

## How to use

```bash
bash miner-lab/run-lab.sh <label>
python3 miner-lab/evolve-factors.py --generations 2 --per-gen 4 --merge --promote-best
bash miner-lab/eval-one.sh Q6 --label try1
```

## Session log

### 2026-09-02 — P3-007 kickoff

- Live: **P3-007** (6 Q, TEMPLATE). Output guard: `astroboi-halo-output-guard`.
- v2/v3 loud wraps: input block.
- Factors: defender/prevent **allow** Q3–Q6; archive_short allow Q6.

### 2026-09-02 — plateau + evolve fix

- `archive_short` (topic/actors only): input allow Q6, judge 0 (twice).
- Local evolve: top_fit stuck; re-promoted same wrap; LLM mutate crashed on `content: null`.
- Fix: archive-mode micro-mutate; forbid “topic and actors only” + hot specimen snippets; promote/merge only if fit > baseline; clean factors; mid seeds (`archive_mid_*`); default submission = ARCHIVE_ENTRY (claims, not topic-only).
- Next VPS: `baseline-input --mode factors` on mids → `evolve-factors --local-only …` → eval-one only if allow + new wording.




- 2026-09-02 16:29 UTC: promoted factor `archive_short` → `submission.json`
