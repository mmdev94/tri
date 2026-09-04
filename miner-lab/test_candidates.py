#!/usr/bin/env python3
"""
Test mining candidates from PyRIT export / FAIL dumps / hand-written wraps.

Mining needs a TEMPLATE with exactly one {{objective}} for P3-007.
Expanded attack texts — use them as:
  A) raw probes (input Halo + optional OpenClaw, no judge), or
  B) templates if you replace the harmful ask with {{objective}}

Usage (repo root):
  # Prefer: bash miner-lab/pyrit/run.sh … → miner-lab/candidates.jsonl
  python3 miner-lab/test_candidates.py --file miner-lab/candidates.jsonl --mode template --question Q3
  python3 miner-lab/test_candidates.py --file miner-lab/candidates.example.json --mode template --promote best --label cand1

Do NOT commit real FAIL payloads. Keep them under /tmp or gitignored paths.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
LAB_DIR = LAB / "lab"
CLASSIFY_URL = os.environ.get(
    "HALO_CLASSIFY_URL", "https://astroboi-halo-guard.chutes.ai/v1/classify"
).rstrip("/")
CLASSIFY_MODEL = os.environ.get("HALO_CLASSIFY_MODEL", "halo-guard")
OUT_CLASSIFY_URL = os.environ.get(
    "HALO_OUTPUT_CLASSIFY_URL",
    "https://astroboi-halo-output-guard.chutes.ai/v1/classify",
).rstrip("/")
OUT_CLASSIFY_MODEL = os.environ.get("HALO_OUTPUT_CLASSIFY_MODEL", "halo-output-guard")

sys.path.insert(0, str(LAB))
from qids_util import add_question_args, clamp_min_allows, resolve_qids  # noqa: E402


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


def classify(query: str, api_key: str, *, role: str, url: str, model: str) -> dict:
    body = json.dumps({"model": model, "query": query, "role": role}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "miner-lab-test-candidates/1",
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
        "status": status_u or resp.get("status"),
    }


def load_candidates(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"empty {path}")
    out: list[dict] = []
    if path.suffix == ".jsonl" or text.startswith("{"):
        # try jsonl first if multiple lines
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if path.suffix == ".jsonl" or (len(lines) > 1 and all(ln.lstrip().startswith("{") for ln in lines)):
            for i, ln in enumerate(lines):
                row = json.loads(ln)
                prompt = (row.get("prompt") or row.get("text") or "").strip()
                if not prompt:
                    continue
                out.append({"id": str(row.get("id") or f"c{i}"), "prompt": prompt, **{k: v for k, v in row.items() if k not in ("prompt", "text")}})
            return out
    data = json.loads(text)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("candidates") or data.get("results") or data.get("fails") or []
        if not rows and data.get("prompt"):
            rows = [data]
    else:
        raise SystemExit("unsupported candidates format")
    for i, row in enumerate(rows):
        if isinstance(row, str):
            out.append({"id": f"c{i}", "prompt": row.strip()})
            continue
        prompt = (row.get("prompt") or row.get("text") or row.get("vars", {}).get("prompt") or "").strip()
        if not prompt:
            continue
        out.append({"id": str(row.get("id") or f"c{i}"), "prompt": prompt})
    if not out:
        raise SystemExit(f"no prompts found in {path}")
    return out


def has_objective(prompt: str) -> bool:
    return bool(re.search(r"\{\{\s*objective\s*\}\}", prompt, flags=re.I))


def resolve_questions() -> Path:
    cands = sorted(
        (LAB / "challenges").glob("*-questions.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if cands:
        return cands[0]
    return ROOT / "tri-check" / "data" / "questions.json"


def load_questions(qids: list[str]) -> list[dict]:
    data = json.loads(resolve_questions().read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    want = set(qids)
    return [r for r in rows if (r.get("question_id") or r.get("id")) in want]


def expand(template: str, objective: str) -> str:
    return re.sub(r"\{\{\s*objective\s*\}\}", objective, template, count=1, flags=re.I)


def stage_raw(cands: list[dict], api_key: str, do_output: bool) -> list[dict]:
    rows = []
    print(f"=== RAW probes n={len(cands)} input={CLASSIFY_URL} ===")
    for c in cands:
        cid, prompt = c["id"], c["prompt"]
        try:
            inn = summarize(classify(prompt, api_key, role="input", url=CLASSIFY_URL, model=CLASSIFY_MODEL))
        except Exception as e:  # noqa: BLE001
            inn = {"verdict": "error", "error": str(e)}
        out = None
        if do_output and inn.get("verdict") == "allow":
            try:
                out = summarize(
                    classify(
                        prompt,
                        api_key,
                        role="output",
                        url=OUT_CLASSIFY_URL,
                        model=OUT_CLASSIFY_MODEL,
                    )
                )
            except Exception as e:  # noqa: BLE001
                out = {"verdict": "error", "error": str(e)}
        print(
            f"{cid:8} input={inn.get('verdict'):6} "
            f"out={((out or {}).get('verdict') or '-'):6} "
            f"len={len(prompt)} tmpl={has_objective(prompt)}"
        )
        rows.append({"id": cid, "input": inn, "output": out, "len": len(prompt), "is_template": has_objective(prompt)})
    return rows


def stage_template(
    cands: list[dict],
    api_key: str,
    qids: list[str],
    label: str,
    min_allows: int,
    promote: str | None,
) -> None:
    questions = load_questions(qids)
    if not questions:
        raise SystemExit(f"no questions for {qids}")

    templates = [c for c in cands if has_objective(c["prompt"])]
    skipped = [c["id"] for c in cands if not has_objective(c["prompt"])]
    if skipped:
        print(f"NOTE: skipping non-templates (need {{{{objective}}}}): {', '.join(skipped)}")
    if not templates:
        raise SystemExit(
            "No candidates contain {{objective}}. "
            "Convert a FAIL framing into a TEMPLATE (replace the harmful ask with {{objective}}), "
            "or use --mode raw."
        )

    print(f"=== TEMPLATE Stage A n={len(templates)} qids={qids} ===")
    best: dict | None = None
    summary_rows = []
    for c in templates:
        cid, tmpl = c["id"], c["prompt"]
        if len(tmpl) > 2000:
            print(f"{cid}: SKIP len={len(tmpl)} > 2000")
            continue
        allows, blocks = [], []
        for q in questions:
            qid = q.get("question_id") or q.get("id")
            obj = q.get("objective") or ""
            query = expand(tmpl, obj)
            try:
                summ = summarize(classify(query, api_key, role="input", url=CLASSIFY_URL, model=CLASSIFY_MODEL))
            except Exception as e:  # noqa: BLE001
                summ = {"verdict": "error", "error": str(e)}
            if summ.get("verdict") == "allow":
                allows.append(str(qid))
            else:
                blocks.append(str(qid))
            conf = summ.get("confidence")
            conf_s = f"{conf:.3f}" if isinstance(conf, (int, float)) else "-"
            print(f"  {cid}/{qid} {summ.get('verdict'):6} conf={conf_s}")
        row = {
            "id": cid,
            "allows": allows,
            "blocks": blocks,
            "n_allow": len(allows),
            "len": len(tmpl),
            "prompt": tmpl,
        }
        summary_rows.append(row)
        print(f"{cid}: allows={len(allows)}/{len(qids)} {allows}")
        if best is None or row["n_allow"] > best["n_allow"]:
            best = row

    LAB_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = LAB_DIR / f"candidates-{ts}-{label}.json"
    out_path.write_text(json.dumps({"utc": ts, "label": label, "rows": summary_rows}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")

    if not best or best["n_allow"] < min_allows:
        print(f"No candidate reached min-allows={min_allows} (best={best['n_allow'] if best else 0})")
        return

    if promote == "best" or promote == best["id"]:
        sub = LAB / "submission.json"
        if sub.exists():
            shutil.copy2(sub, sub.with_suffix(".json.bak"))
        sub.write_text(json.dumps({"prompt": best["prompt"]}, indent=2) + "\n", encoding="utf-8")
        print(f"Promoted {best['id']} → {sub} (allows={best['allows']})")
        print("Next: python3 miner-lab/test_template.py --stage b --label", label)
        # also sync factors key for probe gate
        factors = LAB / "factors.json"
        if factors.is_file():
            fac = json.loads(factors.read_text(encoding="utf-8"))
            fac["candidate_best"] = best["prompt"]
            factors.write_text(json.dumps(fac, indent=2) + "\n", encoding="utf-8")
            print("Updated factors.json key candidate_best")


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")

    ap = argparse.ArgumentParser(description="Test mining candidates from FAIL export / wraps")
    ap.add_argument("--file", "-f", required=True, help="candidates.json / .jsonl / FAIL export")
    ap.add_argument("--mode", choices=("raw", "template"), default="template")
    add_question_args(ap)
    ap.add_argument("--min-allows", type=int, default=1)
    ap.add_argument("--label", default="cand")
    ap.add_argument("--promote", default="", help="'best' or candidate id → submission.json")
    ap.add_argument("--also-output-classify", action="store_true", help="raw mode: also hit output Halo classify")
    args = ap.parse_args()

    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("ERROR: CHUTES_API_KEY missing")

    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    cands = load_candidates(path)
    qids = resolve_qids(args)
    min_allows = clamp_min_allows(args.min_allows, qids)

    os.chdir(ROOT)
    if args.mode == "raw":
        rows = stage_raw(cands, api_key, args.also_output_classify)
        LAB_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = LAB_DIR / f"candidates-raw-{ts}-{args.label}.json"
        out.write_text(json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out}")
        n_tmpl = sum(1 for r in rows if r.get("is_template"))
        print(f"templates_with_{{{{objective}}}}={n_tmpl}/{len(rows)} — only those can go --mode template")
        return 0

    stage_template(cands, api_key, qids, args.label, min_allows, args.promote or None)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as e:
        print(f"ERROR: network {e}", file=sys.stderr)
        raise SystemExit(2)
