#!/usr/bin/env python3
"""Build promptfoo tests from P3-007 questions + wraps (one row per Q × wrap)."""

from __future__ import annotations

import json
import re
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
QUESTIONS = LAB / "challenges" / "P3-007-questions.json"
FACTORS = LAB / "factors.json"
WRAPS = HERE / "wraps.json"
OUT_TESTS = HERE / "tests.generated.json"
OUT_PROMPTS = HERE / "prompts.generated.yaml"


def load_questions() -> list[dict]:
    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    return list(rows)


def load_wraps() -> dict[str, str]:
    raw = json.loads(WRAPS.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for k, v in raw.items():
        if k.startswith("_") or not isinstance(v, str):
            continue
        if v.strip() == "LOAD_FROM_FACTORS":
            if FACTORS.is_file():
                fac = json.loads(FACTORS.read_text(encoding="utf-8"))
                for fk, fv in fac.items():
                    if fk.startswith("_") or not isinstance(fv, str):
                        continue
                    out[f"factors:{fk}"] = fv
            continue
        out[k] = v
    return out


def main() -> int:
    questions = load_questions()
    wraps = load_wraps()
    if not questions:
        raise SystemExit(f"no questions in {QUESTIONS}")
    if not wraps:
        raise SystemExit(f"no wraps in {WRAPS}")

    prompts: list[dict[str, str]] = []
    for name, tmpl in wraps.items():
        if not re.search(r"\{\{\s*objective\s*\}\}", tmpl, flags=re.I):
            raise SystemExit(f"wrap {name!r} missing {{{{objective}}}}")
        prompts.append({"label": name, "raw": tmpl})

    tests = []
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        tests.append(
            {
                "description": f"{qid} {q.get('category') or ''}".strip(),
                "vars": {
                    "qid": qid,
                    "category": q.get("category") or "",
                    "objective": obj,
                },
                "metadata": {"question_id": qid},
            }
        )

    lines = ["# generated — do not edit", ""]
    for p in prompts:
        lines.append(f"- label: {json.dumps(p['label'])}")
        lines.append(f"  raw: {json.dumps(p['raw'])}")
        lines.append("")
    OUT_PROMPTS.write_text("\n".join(lines), encoding="utf-8")
    OUT_TESTS.write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")
    print(f"wraps={len(prompts)} questions={len(tests)}")
    print(f"wrote {OUT_PROMPTS}")
    print(f"wrote {OUT_TESTS}")
    for p in prompts:
        print(f"  prompt id={p['label']} len={len(p['raw'])}")
    for t in tests:
        print(f"  test {t['vars']['qid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
