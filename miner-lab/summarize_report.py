#!/usr/bin/env python3
"""Summarize a tri-check JSON report into Markdown + history row."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_total(results: list[dict[str, Any]]) -> int:
    total = 0
    for r in results:
        if r.get("skipped") or r.get("error"):
            continue
        s = r.get("judgeScore")
        if isinstance(s, (int, float)):
            total += int(s)
    return total


def classify_block(text: str) -> str:
    t = (text or "").lower()
    if "blocked by input guard" in t:
        return "input_guard_block"
    if "blocked by output guard" in t:
        return "output_guard_block"
    if "blocked by guard model" in t:
        return "guard_block"
    return "ok"


def truncate(s: str, n: int = 240) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def write_full_summary(
    report: dict[str, Any],
    out: Path,
    *,
    run_id: str,
    submission_path: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    summary = report.get("summary") or {}
    results = report.get("results") or []
    total_score = score_total(results)
    max_score = 2 * int(summary.get("evaluated") or 0)

    lines: list[str] = []
    lines.append(f"# Miner-lab run `{run_id}`")
    lines.append("")
    lines.append(f"- **UTC:** {meta.get('utc', '')}")
    lines.append(f"- **Host:** {meta.get('hostname', '')}")
    lines.append(f"- **Submission:** `{submission_path}`")
    lines.append(f"- **Mode:** {meta.get('mode', '')}")
    lines.append(f"- **Git:** {meta.get('git', '')}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Questions | {summary.get('totalQuestions', 0)} |")
    lines.append(f"| Evaluated | {summary.get('evaluated', 0)} |")
    lines.append(f"| Jailbreaks (score=2) | {summary.get('totalJailbreaks', 0)} |")
    lines.append(f"| Errors | {summary.get('totalErrors', 0)} |")
    lines.append(f"| Skipped | {summary.get('totalSkipped', 0)} |")
    lines.append(f"| **Sum score** | **{total_score} / {max_score}** |")
    lines.append("")
    lines.append("## Per question")
    lines.append("")
    lines.append("| ID | Verdict | Score | JB | Block | Response preview | Reasoning preview |")
    lines.append("|----|---------|-------|----|-------|------------------|-------------------|")

    per_rows: list[dict[str, Any]] = []
    for r in results:
        qid = r.get("id", "?")
        if r.get("skipped"):
            verdict = "skipped"
            score = "-"
            jb = "no"
            block = "-"
            resp = truncate(str(r.get("skipReason") or ""))
            reason = ""
        elif r.get("error"):
            verdict = "error"
            score = "-"
            jb = "no"
            block = "-"
            resp = truncate(str(r.get("error") or ""))
            reason = ""
        else:
            verdict = str(r.get("judgeVerdict") or "?")
            score = r.get("judgeScore", "?")
            jb = "yes" if r.get("successfulJailbreak") else "no"
            block = classify_block(str(r.get("openclawResponse") or ""))
            resp = truncate(str(r.get("openclawResponse") or ""), 180)
            reason = truncate(str(r.get("judgeReasoning") or ""), 180)

        lines.append(
            f"| {qid} | {verdict} | {score} | {jb} | {block} | {resp} | {reason} |"
        )
        per_rows.append(
            {
                "id": qid,
                "verdict": verdict,
                "score": score,
                "jailbreak": jb,
                "block": block,
            }
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Full JSON: `report.json`")
    lines.append("- Full console: `console.log`")
    lines.append("- Shareable (scores only): see `miner-lab/shared/`")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    return {
        "run_id": run_id,
        "utc": meta.get("utc"),
        "hostname": meta.get("hostname"),
        "mode": meta.get("mode"),
        "git": meta.get("git"),
        "submission": submission_path,
        "total_score": total_score,
        "max_score": max_score,
        "evaluated": summary.get("evaluated", 0),
        "jailbreaks": summary.get("totalJailbreaks", 0),
        "errors": summary.get("totalErrors", 0),
        "questions": per_rows,
    }


def write_share_summary(row: dict[str, Any], out: Path) -> None:
    lines = [
        f"# Latest miner-lab scores (`{row['run_id']}`)",
        "",
        f"- **UTC:** {row.get('utc')}",
        f"- **Host:** {row.get('hostname')}",
        f"- **Mode:** {row.get('mode')}",
        f"- **Git:** {row.get('git')}",
        f"- **Sum score:** **{row.get('total_score')} / {row.get('max_score')}**",
        f"- **Jailbreaks:** {row.get('jailbreaks')} | **Errors:** {row.get('errors')}",
        "",
        "| ID | Verdict | Score | JB | Block |",
        "|----|---------|-------|----|-------|",
    ]
    for q in row.get("questions") or []:
        lines.append(
            f"| {q.get('id')} | {q.get('verdict')} | {q.get('score')} | {q.get('jailbreak')} | {q.get('block')} |"
        )
    lines.append("")
    lines.append("_Full model responses live under `results/miner-lab/` (gitignored)._")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def append_history_md(row: dict[str, Any], history_md: Path) -> None:
    if not history_md.exists():
        history_md.write_text(
            "# Miner-lab score history\n\n"
            "| UTC | Run | Score | JB | Errors | Mode | Host |\n"
            "|-----|-----|-------|----|--------|------|------|\n",
            encoding="utf-8",
        )
    line = (
        f"| {row.get('utc')} | `{row.get('run_id')}` | "
        f"{row.get('total_score')}/{row.get('max_score')} | "
        f"{row.get('jailbreaks')} | {row.get('errors')} | "
        f"{row.get('mode')} | {row.get('hostname')} |\n"
    )
    with history_md.open("a", encoding="utf-8") as f:
        f.write(line)


def append_history_jsonl(row: dict[str, Any], history_jsonl: Path) -> None:
    with history_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--submission", required=True)
    p.add_argument("--shared-dir", required=True, type=Path)
    p.add_argument("--mode", default="")
    p.add_argument("--hostname", default="")
    p.add_argument("--git", default="")
    args = p.parse_args()

    report = load_report(args.report)
    meta = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": args.hostname or os.uname().nodename,
        "mode": args.mode,
        "git": args.git,
    }

    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.shared_dir.mkdir(parents=True, exist_ok=True)

    row = write_full_summary(
        report,
        args.run_dir / "SUMMARY.md",
        run_id=args.run_id,
        submission_path=args.submission,
        meta=meta,
    )
    (args.run_dir / "summary.json").write_text(
        json.dumps(row, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    write_share_summary(row, args.shared_dir / "LATEST-SUMMARY.md")
    append_history_md(row, args.shared_dir / "HISTORY.md")
    append_history_jsonl(row, args.shared_dir / "history.jsonl")

    print(f"Wrote {args.run_dir / 'SUMMARY.md'}", file=sys.stderr)
    print(f"Updated {args.shared_dir / 'LATEST-SUMMARY.md'}", file=sys.stderr)
    print(
        f"SCORE {row['total_score']}/{row['max_score']} "
        f"jailbreaks={row['jailbreaks']} errors={row['errors']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
