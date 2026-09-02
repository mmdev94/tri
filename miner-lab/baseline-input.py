#!/usr/bin/env python3
"""
Baseline / factor probe for Halo *input* only.

Do NOT run full OpenClaw evals until at least one Q shows input allow.

Usage (repo root, CHUTES_API_KEY in .env):
  python3 miner-lab/baseline-input.py
  python3 miner-lab/baseline-input.py --mode bare
  python3 miner-lab/baseline-input.py --mode template --submission miner-lab/submission.json
  python3 miner-lab/baseline-input.py --mode factors
  python3 miner-lab/baseline-input.py --qid Q3 --mode bare,template
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = LAB / "challenges" / "P3-007-questions.json"
FALLBACK_QUESTIONS = ROOT / "tri-check" / "data" / "questions.json"
FACTORS_PATH = LAB / "factors.json"
LAB_DIR = LAB / "lab"
CLASSIFY_URL = os.environ.get(
    "HALO_CLASSIFY_URL", "https://astroboi-halo-guard.chutes.ai/v1/classify"
).rstrip("/")
CLASSIFY_MODEL = os.environ.get("HALO_CLASSIFY_MODEL", "halo-guard")


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def resolve_questions(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    # Prefer newest challenges/*-questions.json by mtime
    cands = sorted((LAB / "challenges").glob("*-questions.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if cands:
        return cands[0]
    if DEFAULT_QUESTIONS.is_file():
        return DEFAULT_QUESTIONS
    return FALLBACK_QUESTIONS


def load_questions(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    return list(rows)


def expand(template: str, objective: str) -> str:
    return re.sub(r"\{\{\s*objective\s*\}\}", objective, template, count=1, flags=re.I)


def classify(query: str, api_key: str) -> dict:
    body = json.dumps({"model": CLASSIFY_MODEL, "query": query, "role": "input"}).encode()
    req = urllib.request.Request(
        CLASSIFY_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "miner-lab-baseline/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def summarize(resp: dict) -> dict:
    status = (resp.get("status") or resp.get("safety_label") or resp.get("safety") or "").upper()
    if isinstance(status, str):
        status_u = status.upper()
    else:
        status_u = str(status)
    # normalize
    if status_u in ("HARMFUL", "UNSAFE") or str(resp.get("safety_label", "")).lower() == "unsafe":
        verdict = "block"
    elif status_u in ("HARMLESS", "SAFE") or str(resp.get("safety_label", "")).lower() == "safe":
        verdict = "allow"
    else:
        # tier / label heuristics
        tier = str(resp.get("tier") or resp.get("risk_level") or "").lower()
        if tier == "unsafe":
            verdict = "block"
        elif tier in ("safe", "controversial", "sensitive"):
            verdict = "allow"
        else:
            verdict = "unknown"
    return {
        "verdict": verdict,
        "status": resp.get("status"),
        "safety_label": resp.get("safety_label") or resp.get("tier") or resp.get("safety"),
        "category": resp.get("category"),
        "confidence": resp.get("confidence") or resp.get("risk_prob") or resp.get("score"),
        "attack_overlay": resp.get("attack_overlay"),
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")

    ap = argparse.ArgumentParser(description="Halo input baseline / factor probes")
    ap.add_argument("--questions", default=None)
    ap.add_argument("--submission", default=str(LAB / "submission.json"))
    ap.add_argument(
        "--mode",
        default="bare,template",
        help="Comma list: bare | template | factors",
    )
    ap.add_argument("--qid", default=None, help="Only one question id, e.g. Q3")
    ap.add_argument(
        "--qids",
        default=None,
        help="Comma list of question ids, e.g. Q3,Q4,Q6 (overrides --qid)",
    )
    ap.add_argument(
        "--factors-file",
        default=None,
        help="Factors JSON (default: factors.json; use factors.gate.json for frozen gate set)",
    )
    ap.add_argument("--label", default="", help="Tag written into lab artifact name")
    ap.add_argument("--dry-run", action="store_true", help="Print queries only, no API")
    args = ap.parse_args()

    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not args.dry_run and not api_key:
        print("ERROR: CHUTES_API_KEY missing (.env)", file=sys.stderr)
        return 2

    qpath = resolve_questions(args.questions)
    questions = load_questions(qpath)
    if args.qids:
        want = {x.strip() for x in args.qids.split(",") if x.strip()}
        questions = [q for q in questions if (q.get("question_id") or q.get("id")) in want]
        if not questions:
            print(f"ERROR: no questions matched {want} in {qpath}", file=sys.stderr)
            return 2
    elif args.qid:
        questions = [q for q in questions if (q.get("question_id") or q.get("id")) == args.qid]
        if not questions:
            print(f"ERROR: no question {args.qid} in {qpath}", file=sys.stderr)
            return 2

    modes = [m.strip() for m in args.mode.split(",") if m.strip()]
    template = ""
    if "template" in modes:
        sub = json.loads(Path(args.submission).read_text(encoding="utf-8"))
        template = sub.get("prompt") or ""
        if "{{objective}}" not in template and "{{ objective }}" not in template.lower():
            print("WARN: submission prompt missing {{objective}}", file=sys.stderr)

    factors: dict[str, str] = {}
    if "factors" in modes:
        fpath = Path(args.factors_file) if args.factors_file else FACTORS_PATH
        if not fpath.is_file():
            print(f"ERROR: {fpath} missing", file=sys.stderr)
            return 2
        raw = json.loads(fpath.read_text(encoding="utf-8"))
        factors = {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str)}
        if not factors:
            print(
                f"WARN: {fpath.name} has no active string factors (score track empty / frozen).\n"
                f"  Gate set: --factors-file miner-lab/factors.gate.json\n"
                f"  See miner-lab/lab/STATUS.md",
                file=sys.stderr,
            )
            if fpath.resolve() == FACTORS_PATH.resolve():
                gate = LAB / "factors.gate.json"
                if gate.is_file():
                    print("HINT: refusing empty score factors — pass --factors-file explicitly for gate.", file=sys.stderr)
                    return 3
        meta = raw.get("_meta") if isinstance(raw.get("_meta"), dict) else {}
        if meta.get("score_track") == "dead" or meta.get("track") == "gate":
            print(f"NOTE: probing GATE set ({fpath.name}) — score_track frozen dead.", file=sys.stderr)
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"-{args.label}" if args.label else ""
    out_path = LAB_DIR / f"baseline-{ts}{tag}.json"

    rows: list[dict] = []
    print(f"questions={qpath.name}  classify={CLASSIFY_URL}  model={CLASSIFY_MODEL}")
    print(f"modes={modes}  n_q={len(questions)}")
    print("-" * 72)

    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        cat = q.get("category") or ""
        jobs: list[tuple[str, str]] = []
        if "bare" in modes:
            jobs.append(("bare", obj))
        if "template" in modes and template:
            jobs.append(("template", expand(template, obj)))
        if "factors" in modes:
            for name, tmpl in factors.items():
                if name.startswith("_"):
                    continue
                jobs.append((f"factor:{name}", expand(tmpl, obj)))

        for name, query in jobs:
            meta = {
                "question_id": qid,
                "category": cat,
                "variant": name,
                "query_len": len(query),
                "objective_preview": obj[:80],
            }
            if args.dry_run:
                print(f"{qid:4} {name:20} len={len(query)}  (dry-run)")
                rows.append({**meta, "verdict": "dry-run"})
                continue
            try:
                raw = classify(query, api_key)
                summ = summarize(raw)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")[:300]
                summ = {"verdict": "error", "status": e.code, "error": body}
                raw = {}
            except Exception as e:  # noqa: BLE001
                summ = {"verdict": "error", "error": str(e)}
                raw = {}

            row = {**meta, **summ}
            # keep compact raw fields useful for notebooks
            if raw:
                row["raw_status"] = raw.get("status")
                row["raw_category"] = raw.get("category")
                row["tier_probs"] = raw.get("tier_probs")
            rows.append(row)
            conf = summ.get("confidence")
            conf_s = f"{conf:.4f}" if isinstance(conf, (int, float)) else str(conf)
            print(
                f"{qid:4} {name:20} {summ.get('verdict'):6}  "
                f"cat={summ.get('category') or '-'}  conf={conf_s}  overlay={summ.get('attack_overlay')}"
            )

    payload = {
        "utc": ts,
        "classify_url": CLASSIFY_URL,
        "classify_model": CLASSIFY_MODEL,
        "questions_path": str(qpath),
        "submission": args.submission if "template" in modes else None,
        "modes": modes,
        "results": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Markdown table for sharing
    md_path = LAB_DIR / "LATEST-BASELINE.md"
    lines = [
        f"# Input Halo baseline (`{ts}{tag}`)",
        "",
        f"- Classify: `{CLASSIFY_URL}` · model `{CLASSIFY_MODEL}`",
        f"- Questions: `{qpath.name}`",
        f"- Modes: `{', '.join(modes)}`",
        "",
        "| Q | Variant | Verdict | Category | Conf | Overlay |",
        "|---|---------|---------|----------|------|---------|",
    ]
    allows = 0
    for r in rows:
        if r.get("verdict") == "allow":
            allows += 1
        conf = r.get("confidence")
        conf_s = f"{conf:.4f}" if isinstance(conf, (int, float)) else str(conf or "")
        lines.append(
            f"| {r.get('question_id')} | {r.get('variant')} | {r.get('verdict')} | "
            f"{r.get('category') or ''} | {conf_s} | {r.get('attack_overlay') or ''} |"
        )
    lines += ["", f"**Allows:** {allows} / {len(rows)}", "", f"_Raw: `{out_path.name}`_", ""]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Append history row
    hist = LAB_DIR / "BASELINE-HISTORY.md"
    if not hist.exists():
        hist.write_text(
            "# Input baseline history\n\n| UTC | Label | Allows | Total | File |\n|-----|-------|--------|-------|------|\n",
            encoding="utf-8",
        )
    with hist.open("a", encoding="utf-8") as f:
        f.write(f"| {ts} | {args.label or '-'} | {allows} | {len(rows)} | `{out_path.name}` |\n")

    print("-" * 72)
    print(f"Wrote {out_path}")
    print(f"Wrote {md_path}  allows={allows}/{len(rows)}")
    return 0 if allows or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
