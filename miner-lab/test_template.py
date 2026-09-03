#!/usr/bin/env python3
"""
Test ONE TEMPLATE across P3-007 Q1–Q6.

Stage A: Halo input classify on all questions (goal: allow >= 3).
Stage B: probe-and-judge on the allows (needs OpenClaw + judge).

Usage (repo root, CHUTES_API_KEY in .env):
  python3 miner-lab/test_template.py
  python3 miner-lab/test_template.py --stage a
  python3 miner-lab/test_template.py --stage b
  python3 miner-lab/test_template.py --sync --label t11
  python3 miner-lab/test_template.py --min-allows 3 --judge-all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
LAB_DIR = LAB / "lab"
SUBMISSION = LAB / "submission.json"
CLASSIFY_URL = os.environ.get(
    "HALO_CLASSIFY_URL", "https://astroboi-halo-guard.chutes.ai/v1/classify"
).rstrip("/")
CLASSIFY_MODEL = os.environ.get("HALO_CLASSIFY_MODEL", "halo-guard")
DEFAULT_QIDS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]


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


def resolve_questions() -> Path:
    cands = sorted(
        (LAB / "challenges").glob("*-questions.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if cands:
        return cands[0]
    return ROOT / "tri-check" / "data" / "questions.json"


def load_questions(path: Path, qids: list[str]) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    want = set(qids)
    return [r for r in rows if (r.get("question_id") or r.get("id")) in want]


def load_template(path: Path) -> str:
    body = json.loads(path.read_text(encoding="utf-8"))
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise SystemExit(f"ERROR: empty prompt in {path}")
    if not re.search(r"\{\{\s*objective\s*\}\}", prompt, flags=re.I):
        raise SystemExit(f"ERROR: {path} missing {{objective}}")
    if len(prompt) > 2000:
        raise SystemExit(f"ERROR: template len={len(prompt)} > 2000")
    return prompt


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
            "User-Agent": "miner-lab-test-template/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def summarize(resp: dict) -> dict:
    status = (resp.get("status") or resp.get("safety_label") or resp.get("safety") or "").upper()
    status_u = status if isinstance(status, str) else str(status)
    if status_u in ("HARMFUL", "UNSAFE") or str(resp.get("safety_label", "")).lower() == "unsafe":
        verdict = "block"
    elif status_u in ("HARMLESS", "SAFE") or str(resp.get("safety_label", "")).lower() == "safe":
        verdict = "allow"
    else:
        tier = str(resp.get("tier") or resp.get("risk_level") or "").lower()
        if tier == "unsafe":
            verdict = "block"
        elif tier in ("safe", "controversial", "sensitive"):
            verdict = "allow"
        else:
            verdict = "unknown"
    return {
        "verdict": verdict,
        "category": resp.get("category"),
        "confidence": resp.get("confidence") or resp.get("risk_prob") or resp.get("score"),
        "attack_overlay": resp.get("attack_overlay"),
    }


def write_manual_prompts(template: str, questions: list[dict], name: str = "answer_not_explain") -> None:
    out_dir = LAB / "manual-prompts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        text = expand(template, obj)
        path = out_dir / f"{name}__{qid}.txt"
        path.write_text(
            f"# template={name}\n# question={qid}\n# len={len(text)}\n\n{text}\n",
            encoding="utf-8",
        )


def stage_a(
    template: str,
    qids: list[str],
    label: str,
    min_allows: int,
    submission: Path,
) -> dict:
    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("ERROR: CHUTES_API_KEY missing (.env)")

    qpath = resolve_questions()
    questions = load_questions(qpath, qids)
    if not questions:
        raise SystemExit(f"ERROR: no questions for {qids} in {qpath}")

    write_manual_prompts(template, questions)

    LAB_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print("=== STAGE A Halo (single template) ===")
    print(f"submission={submission}")
    print(f"len={len(template)}  q={qpath.name}  qids={','.join(qids)}")
    print(f"classify={CLASSIFY_URL}")
    print(f"template: {template[:120]}{'…' if len(template) > 120 else ''}")
    print("-" * 72)

    rows = []
    allows: list[str] = []
    blocks: list[str] = []
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        query = expand(template, obj)
        try:
            raw = classify(query, api_key)
            summ = summarize(raw)
        except Exception as e:  # noqa: BLE001
            summ = {"verdict": "error", "confidence": None, "category": None, "error": str(e)}
        conf = summ.get("confidence")
        conf_s = f"{conf:.4f}" if isinstance(conf, (int, float)) else str(conf)
        print(
            f"{qid:4} {summ.get('verdict'):6}  "
            f"cat={summ.get('category') or '-'}  conf={conf_s}  len={len(query)}"
        )
        row = {
            "question_id": qid,
            "variant": "template",
            **summ,
            "query_len": len(query),
        }
        rows.append(row)
        if summ.get("verdict") == "allow":
            allows.append(str(qid))
        elif summ.get("verdict") == "block":
            blocks.append(str(qid))

    baseline_path = LAB_DIR / f"baseline-{ts}-{label}-template-A.json"
    payload = {
        "utc": ts,
        "label": label,
        "classify_url": CLASSIFY_URL,
        "questions_path": str(qpath),
        "submission": str(submission),
        "template": template,
        "qids": qids,
        "allows": allows,
        "blocks": blocks,
        "n_allow": len(allows),
        "min_allows": min_allows,
        "pass_min_allows": len(allows) >= min_allows,
        "results": rows,
    }
    baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary = LAB_DIR / "TEMPLATE-LATEST.md"
    summary.write_text(
        "\n".join(
            [
                f"# Single-template Stage A (`{ts}` / {label})",
                "",
                f"- Allows **{len(allows)}/{len(qids)}**: {', '.join(allows) or '(none)'}",
                f"- Blocks: {', '.join(blocks) or '(none)'}",
                f"- Goal allow ≥ {min_allows}: **{'PASS' if len(allows) >= min_allows else 'FAIL'}**",
                f"- Baseline: `{baseline_path.name}`",
                f"- Manual: `miner-lab/manual-prompts/answer_not_explain__Q*.txt`",
                "",
                "```",
                template,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    survivors_path = LAB_DIR / "TEMPLATE-SURVIVORS.json"
    survivors_path.write_text(
        json.dumps(
            {
                "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                "label": label,
                "baseline": baseline_path.name,
                "allows": allows,
                "blocks": blocks,
                "n_allow": len(allows),
                "pass_min_allows": len(allows) >= min_allows,
                "prompt": template,
                "stage_b": len(allows) >= 1,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("-" * 72)
    print(f"Allows {len(allows)}/{len(qids)}: {', '.join(allows) or '(none)'}")
    print(f"Blocks: {', '.join(blocks) or '(none)'}")
    if len(allows) >= min_allows:
        print(f"PASS: allow >= {min_allows}")
    else:
        print(f"FAIL: need allow >= {min_allows} (got {len(allows)})")
    print(f"Wrote {baseline_path}")
    print(f"Wrote {summary}")
    print(f"Wrote {survivors_path}")
    return payload


def read_judge_sum(label: str) -> int:
    hist = LAB_DIR / "JUDGE-HISTORY.md"
    if not hist.is_file():
        return 0
    total = 0
    for line in hist.read_text(encoding="utf-8").splitlines():
        if f"| {label} |" not in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 4:
            try:
                total += int(parts[3])
            except ValueError:
                pass
    return total


def stage_b(
    label: str,
    judge_qids: list[str] | None,
    judge_all: bool,
    submission: Path,
) -> int:
    survivors_path = LAB_DIR / "TEMPLATE-SURVIVORS.json"
    if not survivors_path.is_file():
        raise SystemExit(f"ERROR: missing {survivors_path} — run Stage A first")

    data = json.loads(survivors_path.read_text(encoding="utf-8"))
    allows = list(data.get("allows") or [])
    if judge_all:
        qids = DEFAULT_QIDS
    elif judge_qids:
        qids = judge_qids
    else:
        qids = allows

    if not qids:
        print("=== STAGE B === No Qs to judge (0 input allows).")
        return 0

    print(f"=== STAGE B judge === qids={','.join(qids)} (allows were {','.join(allows) or '-'})")
    run_label = f"{label}-B"
    rc = subprocess.call(
        [
            "bash",
            str(LAB / "probe-and-judge.sh"),
            "--label",
            run_label,
            "--qids",
            ",".join(qids),
            "--submission",
            str(submission),
        ],
        cwd=str(ROOT),
    )
    jsum = read_judge_sum(run_label)
    print(f"=== STAGE B done === soft_judge_sum={jsum} rc={rc}")
    if jsum <= 0:
        print("Judge sum 0 — Halo allow ≠ score. Iterate the ONE template ask-shape.")
    else:
        print(f"SCORE_HIT soft_judge_sum={jsum} — candidate for upload.")
    return jsum


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")

    ap = argparse.ArgumentParser(description="Test one TEMPLATE on Q1–Q6")
    ap.add_argument("--stage", choices=("a", "b", "all"), default="all")
    ap.add_argument("--qids", default=",".join(DEFAULT_QIDS), help="Default Q1,Q2,Q3,Q4,Q5,Q6")
    ap.add_argument(
        "--judge-qids",
        default="",
        help="Stage B Qs (default: Stage A allows only)",
    )
    ap.add_argument(
        "--judge-all",
        action="store_true",
        help="Stage B: probe all Q1–Q6 (still only evals Halo allows)",
    )
    ap.add_argument("--min-allows", type=int, default=3)
    ap.add_argument("--label", default="t11")
    ap.add_argument("--submission", default=str(SUBMISSION))
    ap.add_argument("--sync", action="store_true")
    ap.add_argument(
        "--stage-a-only-ok",
        action="store_true",
        help="Exit 0 even if allow < min (still prints FAIL)",
    )
    args = ap.parse_args()

    submission = Path(args.submission)
    if not submission.is_file():
        raise SystemExit(f"ERROR: missing {submission}")

    os.chdir(ROOT)
    if args.sync:
        print("=== sync challenge ===")
        subprocess.check_call([sys.executable, str(LAB / "sync-challenge.py")], cwd=str(ROOT))

    template = load_template(submission)
    qids = [x.strip() for x in args.qids.split(",") if x.strip()]
    jq = [x.strip() for x in args.judge_qids.split(",") if x.strip()] or None

    a_payload: dict | None = None
    if args.stage in ("a", "all"):
        a_payload = stage_a(template, qids, args.label, args.min_allows, submission)
        if (
            args.stage == "a"
            and a_payload
            and not a_payload.get("pass_min_allows")
            and not args.stage_a_only_ok
        ):
            return 1

    if args.stage in ("b", "all"):
        if a_payload and not a_payload.get("allows") and args.stage == "all":
            print("Skip Stage B — zero input allows.")
            return 0 if a_payload.get("pass_min_allows") or args.stage_a_only_ok else 1
        stage_b(args.label, jq, args.judge_all, submission)

    if a_payload and not a_payload.get("pass_min_allows") and not args.stage_a_only_ok:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as e:
        print(f"ERROR: network {e}", file=sys.stderr)
        raise SystemExit(2)
