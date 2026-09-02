#!/usr/bin/env python3
"""
One-shot miner-lab test: Stage A (Halo) → Stage B (judge on allows).

Usage (repo root or miner-lab/, with .env CHUTES_API_KEY; OpenClaw for Stage B):
  python3 miner-lab/test_batch.py
  python3 miner-lab/test_batch.py --stage a
  python3 miner-lab/test_batch.py --stage b
  python3 miner-lab/test_batch.py --sync --qids Q3,Q4,Q6 --judge-qids Q3,Q6
  python3 miner-lab/test_batch.py --max-judge 5 --label t8
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
FACTORS = LAB / "factors.json"
SURVIVORS = LAB_DIR / "BATCH-SURVIVORS.json"
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


def resolve_questions() -> Path:
    cands = sorted(
        (LAB / "challenges").glob("*-questions.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if cands:
        return cands[0]
    return ROOT / "tri-check" / "data" / "questions.json"


def load_questions(path: Path, qids: list[str] | None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    if qids:
        want = set(qids)
        rows = [r for r in rows if (r.get("question_id") or r.get("id")) in want]
    return rows


def active_factors() -> dict[str, str]:
    raw = json.loads(FACTORS.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str)}


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
            "User-Agent": "miner-lab-test-batch/1",
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


def is_case_note(prompt: str) -> bool:
    low = prompt.lower()
    return (
        "case_note" in low
        or ("archival note" in low and "historical evidence" in low)
        or ("compliance board" in low and "quoted evidence" in low)
    )


def stage_a(qids: list[str], label: str, include_case_note: bool) -> dict:
    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("ERROR: CHUTES_API_KEY missing (.env)")

    factors = active_factors()
    if not factors:
        raise SystemExit("ERROR: factors.json has no templates")

    qpath = resolve_questions()
    questions = load_questions(qpath, qids)
    if not questions:
        raise SystemExit(f"ERROR: no questions for {qids} in {qpath}")

    LAB_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"=== STAGE A Halo === factors={len(factors)} q={qpath.name} qids={qids}")
    print(f"classify={CLASSIFY_URL}")
    print("-" * 72)

    rows = []
    by: dict[str, dict] = {}
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        for name, tmpl in factors.items():
            query = expand(tmpl, obj)
            try:
                raw = classify(query, api_key)
                summ = summarize(raw)
            except Exception as e:  # noqa: BLE001
                summ = {"verdict": "error", "confidence": None, "category": None, "error": str(e)}
            conf = summ.get("confidence")
            conf_s = f"{conf:.4f}" if isinstance(conf, (int, float)) else str(conf)
            print(
                f"{qid:4} {name:22} {summ.get('verdict'):6}  "
                f"cat={summ.get('category') or '-'}  conf={conf_s}"
            )
            row = {
                "question_id": qid,
                "variant": f"factor:{name}",
                **summ,
                "query_len": len(query),
            }
            rows.append(row)
            by.setdefault(name, {"allows": [], "blocks": [], "conf": {}})
            if summ.get("verdict") == "allow":
                by[name]["allows"].append(qid)
            elif summ.get("verdict") == "block":
                by[name]["blocks"].append(qid)
                if isinstance(conf, (int, float)):
                    by[name]["conf"][qid] = float(conf)

    baseline_path = LAB_DIR / f"baseline-{ts}-{label}-A.json"
    baseline_path.write_text(
        json.dumps(
            {
                "utc": ts,
                "classify_url": CLASSIFY_URL,
                "questions_path": str(qpath),
                "modes": ["factors"],
                "label": label,
                "results": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    survivors = []
    near = []
    for name, info in sorted(by.items()):
        prompt = factors[name]
        allows = info["allows"]
        item = {
            "name": name,
            "allows": allows,
            "n_allow": len(allows),
            "block_conf": info["conf"],
            "case_note": is_case_note(prompt),
            "prompt": prompt,
            "len": len(prompt),
        }
        if allows:
            if item["case_note"] and not include_case_note:
                item["stage_b"] = False
                item["skip_reason"] = "case_note_family_known_judge0"
                near.append(item)
            else:
                item["stage_b"] = True
                survivors.append(item)
        else:
            lows = [c for c in info["conf"].values() if c < 0.85]
            if lows:
                item["stage_b"] = False
                item["skip_reason"] = "near_miss_no_allow"
                near.append(item)

    survivors.sort(key=lambda r: (-r["n_allow"], r["name"]))
    payload = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "baseline": baseline_path.name,
        "label": label,
        "qids": qids,
        "include_case_note": include_case_note,
        "survivors": survivors,
        "skipped_case_note_or_near": near,
    }
    SURVIVORS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# test_batch Stage A (`{payload['utc']}` / {label})",
        "",
        f"- Baseline: `{baseline_path.name}`",
        f"- Survivors for Stage B: **{len(survivors)}**",
        "",
        "| Factor | len | Allows | Stage B | Note |",
        "|--------|-----|--------|---------|------|",
    ]
    for r in survivors:
        md_lines.append(
            f"| {r['name']} | {r['len']} | {','.join(r['allows']) or '-'} | yes | |"
        )
    for r in near:
        md_lines.append(
            f"| {r['name']} | {r['len']} | {','.join(r['allows']) or '-'} | no | {r.get('skip_reason','')} |"
        )
    md_lines += ["", f"Survivors: `{SURVIVORS}`", ""]
    (LAB_DIR / "LATEST-BATCH.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("-" * 72)
    print(f"Wrote {baseline_path}")
    print(f"Wrote {SURVIVORS} survivors={len(survivors)} near={len(near)}")
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


def stage_b(judge_qids: list[str], label: str, max_judge: int) -> int:
    if not SURVIVORS.is_file():
        raise SystemExit(f"ERROR: missing {SURVIVORS} — run Stage A first")

    data = json.loads(SURVIVORS.read_text(encoding="utf-8"))
    todo = [r for r in data.get("survivors") or [] if r.get("stage_b")][:max_judge]
    if not todo:
        print("=== STAGE B === No survivors (all input-blocked or CASE_NOTE skipped).")
        print("Try more indirect factors, or --include-case-note for gate regression only.")
        return 0

    print(f"=== STAGE B judge === n={len(todo)} qids={judge_qids}")
    hist_path = LAB_DIR / "BATCH-HISTORY.md"
    if not hist_path.is_file():
        hist_path.write_text(
            "# Batch Stage B history\n\n"
            "| UTC | Label | Factor | Soft judge sum | Notes |\n"
            "|-----|-------|--------|----------------|-------|\n",
            encoding="utf-8",
        )
    hit_path = LAB_DIR / "BATCH-HIT.txt"
    if hit_path.is_file():
        hit_path.unlink()

    utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    best = 0
    for row in todo:
        name = row["name"]
        run_label = f"{label}-B-{name}"
        print(f"\n----- {name} (allows={row.get('allows')}) -----")
        rc_p = subprocess.call(
            [sys.executable, str(LAB / "promote-factor.py"), name],
            cwd=str(ROOT),
        )
        if rc_p != 0:
            print(f"promote failed rc={rc_p}")
            continue
        qids_arg = ",".join(judge_qids)
        rc = subprocess.call(
            [
                "bash",
                str(LAB / "probe-and-judge.sh"),
                "--label",
                run_label,
                "--qids",
                qids_arg,
            ],
            cwd=str(ROOT),
        )
        if rc == 3:
            print("probe refused (dead-family/empty) — retry with --force-gate")
            rc = subprocess.call(
                [
                    "bash",
                    str(LAB / "probe-and-judge.sh"),
                    "--label",
                    run_label,
                    "--qids",
                    qids_arg,
                    "--force-gate",
                ],
                cwd=str(ROOT),
            )
        jsum = read_judge_sum(run_label)
        best = max(best, jsum)
        note = f"rc={rc}"
        if jsum > 0:
            note = f"SCORE_HIT {note}"
            hit_path.write_text(name + "\n", encoding="utf-8")
            print(f"=== HIT {name} soft_judge_sum={jsum} ===")
        with hist_path.open("a", encoding="utf-8") as f:
            f.write(f"| {utc} | {label} | {name} | {jsum} | {note} |\n")
        print(f"factor={name} soft_judge_sum={jsum}")

    print("\n=== STAGE B done ===")
    if hit_path.is_file():
        print(f"Submit candidate: {hit_path.read_text().strip()}")
    else:
        print("No judge>0 this run.")
    return best


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")

    ap = argparse.ArgumentParser(description="One-shot Halo→judge batch test")
    ap.add_argument("--stage", choices=("a", "b", "all"), default="all")
    ap.add_argument("--qids", default="Q3,Q4,Q6")
    ap.add_argument("--judge-qids", default="Q3,Q6")
    ap.add_argument("--max-judge", type=int, default=8)
    ap.add_argument("--label", default="t8")
    ap.add_argument("--sync", action="store_true", help="Refresh ACTIVE challenge first")
    ap.add_argument("--include-case-note", action="store_true")
    args = ap.parse_args()

    os.chdir(ROOT)
    if args.sync:
        print("=== sync challenge ===")
        subprocess.check_call([sys.executable, str(LAB / "sync-challenge.py")], cwd=str(ROOT))

    qids = [x.strip() for x in args.qids.split(",") if x.strip()]
    jq = [x.strip() for x in args.judge_qids.split(",") if x.strip()]

    # validate factor lengths
    for name, tmpl in active_factors().items():
        if tmpl.count("{{objective}}") != 1 and "{{ objective }}" not in tmpl:
            # allow flexible placeholder via expand regex — still require one match
            if not re.search(r"\{\{\s*objective\s*\}\}", tmpl, flags=re.I):
                print(f"WARN: {name} missing {{objective}}", file=sys.stderr)
        if len(tmpl) > 2000:
            raise SystemExit(f"ERROR: {name} len={len(tmpl)} > 2000")

    if args.stage in ("a", "all"):
        stage_a(qids, args.label, args.include_case_note)
    if args.stage in ("b", "all"):
        stage_b(jq, args.label, args.max_judge)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as e:
        print(f"ERROR: network {e}", file=sys.stderr)
        raise SystemExit(2)
