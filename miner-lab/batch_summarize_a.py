#!/usr/bin/env python3
"""Summarize latest baseline-*-{label}-A.json into BATCH-SURVIVORS.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
LAB_DIR = LAB / "lab"


def is_case_note(prompt: str) -> bool:
    low = prompt.lower()
    return (
        "case_note" in low
        or ("archival note" in low and "historical evidence" in low)
        or ("compliance board" in low and "quoted evidence" in low)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--qids", default="Q3,Q4,Q6")
    ap.add_argument("--include-case-note", action="store_true")
    ap.add_argument("--survivors", default=str(LAB_DIR / "BATCH-SURVIVORS.json"))
    ap.add_argument("--md", default=str(LAB_DIR / "LATEST-BATCH.md"))
    args = ap.parse_args()

    factors = {
        k: v
        for k, v in json.loads((LAB / "factors.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_") and isinstance(v, str)
    }
    cands = sorted(
        LAB_DIR.glob(f"baseline-*-{args.label}-A.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cands:
        cands = sorted(LAB_DIR.glob("baseline-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise SystemExit("no baseline json")

    data = json.loads(cands[0].read_text(encoding="utf-8"))
    by: dict[str, dict] = {}
    for r in data.get("results") or []:
        var = r.get("variant") or ""
        if not var.startswith("factor:"):
            continue
        name = var.split(":", 1)[1]
        by.setdefault(name, {"allows": [], "blocks": [], "conf": {}})
        qid = r.get("question_id")
        if r.get("verdict") == "allow":
            by[name]["allows"].append(qid)
        elif r.get("verdict") == "block":
            by[name]["blocks"].append(qid)
            c = r.get("confidence")
            if isinstance(c, (int, float)):
                by[name]["conf"][qid] = float(c)

    survivors = []
    near = []
    for name, info in sorted(by.items()):
        prompt = factors.get(name)
        if not isinstance(prompt, str):
            continue
        allows = info["allows"]
        row = {
            "name": name,
            "allows": allows,
            "n_allow": len(allows),
            "block_conf": info["conf"],
            "case_note": is_case_note(prompt),
            "prompt": prompt,
            "len": len(prompt),
        }
        if allows:
            if row["case_note"] and not args.include_case_note:
                row["stage_b"] = False
                row["skip_reason"] = "case_note_family_known_judge0"
                near.append(row)
            else:
                row["stage_b"] = True
                survivors.append(row)
        else:
            lows = [c for c in info["conf"].values() if c < 0.7]
            if lows:
                row["stage_b"] = False
                row["skip_reason"] = "near_miss_no_allow"
                near.append(row)

    survivors.sort(key=lambda r: (-r["n_allow"], r["name"]))
    payload = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "baseline": cands[0].name,
        "label": args.label,
        "qids": [x.strip() for x in args.qids.split(",") if x.strip()],
        "include_case_note": args.include_case_note,
        "survivors": survivors,
        "skipped_case_note_or_near": near,
    }
    out = Path(args.survivors)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Batch Stage A (`{payload['utc']}` / {args.label})",
        "",
        f"- Baseline: `{cands[0].name}`",
        f"- Survivors for Stage B: **{len(survivors)}** "
        f"(CASE_NOTE skipped={not args.include_case_note})",
        "",
        "| Factor | Allows | Stage B | Note |",
        "|--------|--------|---------|------|",
    ]
    for r in survivors:
        lines.append(f"| {r['name']} | {','.join(r['allows']) or '-'} | yes | |")
    for r in near:
        lines.append(
            f"| {r['name']} | {','.join(r['allows']) or '-'} | no | {r.get('skip_reason', '')} |"
        )
    lines += ["", f"Survivors JSON: `{out}`", ""]
    Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} survivors={len(survivors)} tracked_other={len(near)}")
    print(f"Wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
