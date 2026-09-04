#!/usr/bin/env python3
"""
Filter TEMPLATE seeds through Halo (+ optional OpenClaw / output classify).
Uses PyRIT for scaffold converters. Export survivors to candidates.jsonl.

Does NOT author jailbreak text — only runs your seeds / factors / converters.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
ROOT = LAB.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(HERE))

from qids_util import add_question_args, resolve_qids  # noqa: E402

from classify import classify_async, dumps_brief  # noqa: E402
from convert_templates import convert_template, available_converters  # noqa: E402
from openclaw import chat_async, health_ok  # noqa: E402

OBJ_RE = re.compile(r"\{\{\s*objective\s*\}\}", flags=re.I)


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


def load_questions(qids: list[str]) -> list[dict]:
    path = resolve_questions()
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    want = set(qids)
    out = [r for r in rows if (r.get("question_id") or r.get("id")) in want]
    if not out:
        raise SystemExit(f"no questions for {qids} in {path}")
    return out


def expand(template: str, objective: str) -> str:
    return OBJ_RE.sub(objective, template, count=1)


def load_seeds(path: Path | None, seeds_from: str) -> list[dict]:
    seeds: list[dict] = []
    if seeds_from in ("factors", "both"):
        fac = LAB / "factors.json"
        if fac.is_file():
            data = json.loads(fac.read_text(encoding="utf-8"))
            for k, v in data.items():
                if k.startswith("_") or not isinstance(v, str):
                    continue
                if not OBJ_RE.search(v):
                    continue
                seeds.append({"id": k, "prompt": v.strip(), "source": "factors.json"})
    if seeds_from in ("submission", "both"):
        sub = LAB / "submission.json"
        if sub.is_file():
            prompt = (json.loads(sub.read_text(encoding="utf-8")).get("prompt") or "").strip()
            if OBJ_RE.search(prompt):
                seeds.append({"id": "submission", "prompt": prompt, "source": "submission.json"})

    if path and path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("seeds") or data.get("candidates") or data
        if isinstance(rows, dict):
            rows = [{"id": k, "prompt": v} for k, v in rows.items() if isinstance(v, str)]
        for i, row in enumerate(rows):
            if isinstance(row, str):
                seeds.append({"id": f"seed{i}", "prompt": row, "source": str(path)})
            elif isinstance(row, dict) and row.get("prompt"):
                seeds.append(
                    {
                        "id": str(row.get("id") or f"seed{i}"),
                        "prompt": str(row["prompt"]).strip(),
                        "source": str(path),
                    }
                )

    # default example if nothing
    if not seeds:
        ex = HERE / "seeds.example.json"
        if ex.is_file():
            return load_seeds(ex, "none")
        raise SystemExit("no seeds — pass --seeds or --seeds-from factors")

    cleaned: list[dict] = []
    seen: set[str] = set()
    for s in seeds:
        p = s["prompt"]
        if not OBJ_RE.search(p):
            print(f"skip {s['id']}: missing {{objective}}", file=sys.stderr)
            continue
        if len(p) > 2000:
            print(f"skip {s['id']}: len={len(p)} > 2000", file=sys.stderr)
            continue
        key = p
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)
    return cleaned


async def probe_one(
    *,
    seed_id: str,
    template: str,
    q: dict,
    api_key: str,
    stage: str,
    also_output_classify: bool,
    dry_run: bool,
) -> dict:
    qid = q.get("question_id") or q.get("id")
    objective = q.get("objective") or ""
    text = expand(template, objective)
    row: dict = {
        "id": f"{seed_id}__{qid}",
        "seed_id": seed_id,
        "question_id": qid,
        "category": q.get("category"),
        "template_len": len(template),
        "expanded_len": len(text),
        "prompt": template,  # TEMPLATE for export (not expanded)
    }
    if dry_run:
        row["input"] = {"verdict": "allow", "status": "dry-run"}
        print(f"{seed_id} {qid} input=dry-run")
        return row

    inp = await classify_async(text, api_key, role="input")
    row["input"] = {
        "verdict": inp["verdict"],
        "status": inp.get("status"),
        "category": inp.get("category"),
        "confidence": inp.get("confidence"),
    }
    print(f"{seed_id} {qid} input={inp['verdict']} conf={inp.get('confidence')} cat={inp.get('category')}")

    if stage == "input" or inp["verdict"] != "allow":
        return row

    # stack: OpenClaw
    claw = await chat_async(text)
    row["stack"] = {
        "ok": claw.get("ok"),
        "output_blocked": claw.get("output_blocked"),
        "status_code": claw.get("status_code"),
        "reply_preview": (claw.get("text") or "")[:240],
    }
    print(
        f"  stack ok={claw.get('ok')} output_blocked={claw.get('output_blocked')} "
        f"preview={(claw.get('text') or '')[:80]!r}"
    )

    if also_output_classify and claw.get("ok") and claw.get("text") and not claw.get("output_blocked"):
        outc = await classify_async(claw["text"], api_key, role="output")
        row["output_classify"] = {
            "verdict": outc["verdict"],
            "status": outc.get("status"),
            "category": outc.get("category"),
            "confidence": outc.get("confidence"),
        }
        print(f"  output_classify={dumps_brief(outc)}")

    return row


async def amain() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")

    ap = argparse.ArgumentParser(description="PyRIT seed filter → Halo / OpenClaw → candidates.jsonl")
    ap.add_argument("--seeds", default="", help="seeds JSON (default: pyrit/seeds.example.json if no --seeds-from)")
    ap.add_argument(
        "--seeds-from",
        choices=("none", "factors", "submission", "both"),
        default="none",
        help="Also/instead load templates from factors.json / submission.json",
    )
    add_question_args(ap)
    ap.add_argument("--stage", choices=("input", "stack"), default="input")
    ap.add_argument(
        "--convert",
        default="",
        help="Comma PyRIT converters on scaffold: leet,rot13,zero_width,join,caesar,randcap,morse,b64",
    )
    ap.add_argument("--also-output-classify", action="store_true")
    ap.add_argument("--out", default=str(LAB / "candidates.jsonl"))
    ap.add_argument("--label", default="pyrit")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--min-input-allows",
        type=int,
        default=1,
        help="Only export seed if ≥ this many Qs allow on input",
    )
    args = ap.parse_args()

    qids = resolve_qids(args)
    questions = load_questions(qids)

    seeds_path: Path | None = Path(args.seeds) if args.seeds else None
    if args.seeds_from == "none" and seeds_path is None:
        seeds_path = HERE / "seeds.example.json"
    seeds = load_seeds(seeds_path if seeds_path and seeds_path.is_file() else None, args.seeds_from)

    convert_names = [x.strip() for x in args.convert.split(",") if x.strip()]
    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not args.dry_run and not api_key:
        raise SystemExit("ERROR: CHUTES_API_KEY missing")

    if args.stage == "stack" and not args.dry_run:
        if not await health_ok():
            raise SystemExit("ERROR: OpenClaw not healthy — start claw or use --stage input")

    print(f"=== PyRIT filter === stage={args.stage} qids={','.join(qids)} seeds={len(seeds)}")
    print(f"questions={resolve_questions().name} convert={convert_names or '-'}")

    # expand seed list with converter variants
    work: list[dict] = []
    for s in seeds:
        work.append(dict(s))
        if convert_names:
            try:
                mutated = await convert_template(s["prompt"], convert_names)
            except Exception as e:
                print(f"convert fail {s['id']}: {e}", file=sys.stderr)
                continue
            if mutated != s["prompt"]:
                work.append(
                    {
                        "id": f"{s['id']}__{'+'.join(convert_names)}",
                        "prompt": mutated,
                        "source": f"convert:{s.get('source', s['id'])}",
                    }
                )

    rows: list[dict] = []
    for s in work:
        for q in questions:
            row = await probe_one(
                seed_id=s["id"],
                template=s["prompt"],
                q=q,
                api_key=api_key,
                stage=args.stage,
                also_output_classify=args.also_output_classify,
                dry_run=args.dry_run,
            )
            rows.append(row)

    # aggregate by seed template: export if enough input allows
    by_seed: dict[str, list[dict]] = {}
    for r in rows:
        by_seed.setdefault(r["seed_id"], []).append(r)

    export: list[dict] = []
    for seed_id, group in by_seed.items():
        allows = [g for g in group if (g.get("input") or {}).get("verdict") == "allow"]
        # stack survivors: allow and not output_blocked
        if args.stage == "stack":
            stack_ok = [
                g
                for g in allows
                if g.get("stack")
                and g["stack"].get("ok")
                and not g["stack"].get("output_blocked")
            ]
            ok_n = len(stack_ok)
            need = args.min_input_allows
            survivors = stack_ok
        else:
            ok_n = len(allows)
            need = args.min_input_allows
            survivors = allows

        print(f"seed {seed_id}: input_allows={len(allows)}/{len(group)} stage_ok={ok_n}")
        if ok_n >= need and survivors:
            export.append(
                {
                    "id": seed_id,
                    "prompt": survivors[0]["prompt"],
                    "meta": {
                        "label": args.label,
                        "allows": [g["question_id"] for g in allows],
                        "stage_ok": [g["question_id"] for g in survivors],
                    },
                }
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for c in export:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    detail = LAB / "lab" / f"pyrit-{ts}-{args.label}.json"
    detail.parent.mkdir(parents=True, exist_ok=True)
    detail.write_text(
        json.dumps({"utc": ts, "label": args.label, "rows": rows, "export": export}, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {out} ({len(export)} templates)")
    print(f"Wrote {detail}")
    if export:
        print("Next: python3 miner-lab/test_candidates.py -f", out, "--mode template --promote best")
    return 0


def main() -> int:
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
