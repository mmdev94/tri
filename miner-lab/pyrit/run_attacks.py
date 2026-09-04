#!/usr/bin/env python3
"""
Advanced PyRIT attacks for miner-lab (you don't hand-write jailbreaks).

Modes
  llm     — Variation / Persuasion / Tone converters on TEMPLATE seeds (keeps {{objective}})
  crescendo | pair | redteam — multi-turn attacks vs OpenClaw; templatize user turns
  all     — llm then crescendo

Attacker LLM = Chutes (no Halo). Objective target = OpenClaw (full guards).
Always optional Halo input filter before writing candidates.jsonl.

Examples:
  bash miner-lab/pyrit/run.sh attack --mode llm --question Q3 --seeds-from factors
  bash miner-lab/pyrit/run.sh attack --mode crescendo --question Q3 --max-turns 5
  bash miner-lab/pyrit/run.sh attack --mode all --questions Q3,Q6 --filter-halo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
ROOT = LAB.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(HERE))

from qids_util import add_question_args, resolve_qids  # noqa: E402

from classify import classify_async  # noqa: E402
from llm_targets import describe_targets, make_attacker_target, make_openclaw_target  # noqa: E402
from openclaw import health_ok  # noqa: E402
from templatize import from_sentinel, templatize, with_sentinel  # noqa: E402

OBJ_RE = re.compile(r"\{\{\s*objective\s*\}\}", flags=re.I)

PERSUASION_TECHNIQUES = (
    "authority_endorsement",
    "evidence_based",
    "expert_endorsement",
    "logical_appeal",
)
DEFAULT_TONES = ("authoritative", "academic", "curious", "helpful")


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


def load_seeds(seeds_from: str, seeds_path: Path | None) -> list[dict]:
    seeds: list[dict] = []
    if seeds_from in ("factors", "both", "submission"):
        if seeds_from in ("factors", "both"):
            fac = LAB / "factors.json"
            if fac.is_file():
                data = json.loads(fac.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if k.startswith("_") or not isinstance(v, str):
                        continue
                    if OBJ_RE.search(v):
                        seeds.append({"id": k, "prompt": v.strip()})
        if seeds_from in ("submission", "both"):
            sub = LAB / "submission.json"
            if sub.is_file():
                p = (json.loads(sub.read_text(encoding="utf-8")).get("prompt") or "").strip()
                if OBJ_RE.search(p):
                    seeds.append({"id": "submission", "prompt": p})
    path = seeds_path
    if path is None and seeds_from == "none":
        path = HERE / "seeds.example.json"
    if path and path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("seeds") or data.get("candidates") or []
        for i, row in enumerate(rows):
            if isinstance(row, dict) and row.get("prompt") and OBJ_RE.search(row["prompt"]):
                seeds.append({"id": str(row.get("id") or f"seed{i}"), "prompt": row["prompt"].strip()})
    # dedupe
    seen: set[str] = set()
    out: list[dict] = []
    for s in seeds:
        if s["prompt"] in seen:
            continue
        seen.add(s["prompt"])
        out.append(s)
    if not out:
        raise SystemExit("no TEMPLATE seeds — use --seeds-from factors or --seeds path")
    return out


def piece_text(piece) -> str:
    return (getattr(piece, "converted_value", None) or getattr(piece, "original_value", None) or "") or ""


async def convert_seed_llm(seed: dict, attacker, kinds: list[str]) -> list[dict]:
    """LLM converters on scaffold with sentinel so {{objective}} survives."""
    from pyrit.converter import PersuasionConverter, ToneConverter, VariationConverter

    out: list[dict] = []
    base = with_sentinel(seed["prompt"])
    jobs: list[tuple[str, object]] = []

    if "vary" in kinds or "variation" in kinds or "all" in kinds:
        jobs.append(("vary", VariationConverter(converter_target=attacker)))
    if "persuade" in kinds or "all" in kinds:
        for tech in PERSUASION_TECHNIQUES:
            jobs.append((f"persuade_{tech}", PersuasionConverter(converter_target=attacker, persuasion_technique=tech)))
    if "tone" in kinds or "all" in kinds:
        for tone in DEFAULT_TONES:
            jobs.append((f"tone_{tone}", ToneConverter(converter_target=attacker, tone=tone)))

    for name, conv in jobs:
        try:
            result = await conv.convert_async(prompt=base, input_type="text")
            text = getattr(result, "output_text", None) or ""
            tmpl = from_sentinel(text)
            if not tmpl:
                # try templatize if model echoed objective slot oddly
                print(f"  skip {seed['id']}/{name}: sentinel lost or len>2000")
                continue
            out.append({"id": f"{seed['id']}__{name}", "prompt": tmpl, "via": name})
            print(f"  + {seed['id']}/{name} len={len(tmpl)}")
        except Exception as e:
            print(f"  fail {seed['id']}/{name}: {e}", file=sys.stderr)
    return out


async def extract_user_templates(conversation_id: str, objective: str) -> list[str]:
    from pyrit.memory import CentralMemory

    mem = CentralMemory.get_memory_instance()
    pieces = mem.get_message_pieces(conversation_id=conversation_id, role="user")
    templates: list[str] = []
    seen: set[str] = set()
    for p in sorted(pieces, key=lambda x: getattr(x, "sequence", 0) or 0):
        if getattr(p, "role", None) != "user":
            continue
        raw = piece_text(p).strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)
        t = templatize(raw, objective)
        if t and t not in templates:
            templates.append(t)
    return templates


async def run_multi_turn(
    *,
    mode: str,
    objective: str,
    qid: str,
    max_turns: int,
    tree_width: int,
    tree_depth: int,
) -> dict:
    from pyrit.executor.attack import (
        AttackAdversarialConfig,
        CrescendoAttack,
        PAIRAttack,
        RedTeamingAttack,
    )

    objective_target = make_openclaw_target()
    attacker = make_attacker_target()
    adv = AttackAdversarialConfig(target=attacker)

    if mode == "crescendo":
        attack = CrescendoAttack(
            objective_target=objective_target,
            attack_adversarial_config=adv,
            max_turns=max_turns,
            max_backtracks=min(5, max_turns),
        )
    elif mode == "pair":
        attack = PAIRAttack(
            objective_target=objective_target,
            attack_adversarial_config=adv,
            tree_width=tree_width,
            tree_depth=tree_depth,
        )
    elif mode == "redteam":
        attack = RedTeamingAttack(
            objective_target=objective_target,
            attack_adversarial_config=adv,
            max_turns=max_turns,
        )
    else:
        raise ValueError(mode)

    print(f"--- {mode} {qid} objective={objective[:60]!r}… ---")
    result = await attack.execute_async(objective=objective)
    outcome = getattr(result, "outcome", None)
    outcome_s = getattr(outcome, "value", None) or str(outcome)
    reason = getattr(result, "outcome_reason", None)
    turns = getattr(result, "executed_turns", None)
    cid = getattr(result, "conversation_id", None)
    print(f"  outcome={outcome_s} turns={turns} reason={(reason or '')[:120]}")

    templates: list[str] = []
    if cid:
        templates = await extract_user_templates(cid, objective)

    last = getattr(result, "last_response", None)
    last_txt = piece_text(last) if last is not None else ""
    return {
        "mode": mode,
        "question_id": qid,
        "objective": objective,
        "outcome": outcome_s,
        "outcome_reason": reason,
        "executed_turns": turns,
        "conversation_id": cid,
        "templates": templates,
        "last_response_preview": last_txt[:400],
    }


async def halo_filter_templates(
    templates: list[dict],
    questions: list[dict],
    api_key: str,
    min_allows: int,
) -> list[dict]:
    kept: list[dict] = []
    for t in templates:
        allows: list[str] = []
        for q in questions:
            qid = q.get("question_id") or q.get("id")
            obj = q.get("objective") or ""
            expanded = OBJ_RE.sub(obj, t["prompt"], count=1)
            try:
                s = await classify_async(expanded, api_key, role="input")
            except Exception as e:
                print(f"  classify fail {t['id']}/{qid}: {e}", file=sys.stderr)
                continue
            print(f"  halo {t['id']}/{qid} {s['verdict']} conf={s.get('confidence')}")
            if s["verdict"] == "allow":
                allows.append(str(qid))
        if len(allows) >= min_allows:
            t = dict(t)
            t["meta"] = {"allows": allows, "source": "pyrit-attack"}
            kept.append(t)
            print(f"  KEEP {t['id']} allows={allows}")
        else:
            print(f"  drop {t['id']} allows={allows}")
    return kept


async def amain() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "tri-check" / ".env")
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    ap = argparse.ArgumentParser(description="Advanced PyRIT attacks → candidates.jsonl")
    ap.add_argument(
        "--mode",
        default="llm",
        choices=("llm", "crescendo", "pair", "redteam", "all"),
        help="llm=converter mutation; crescendo/pair/redteam=multi-turn; all=llm+crescendo",
    )
    ap.add_argument(
        "--llm-kinds",
        default="all",
        help="For --mode llm: all|vary,persuade,tone (comma)",
    )
    add_question_args(ap)
    ap.add_argument("--seeds", default="", help="seeds JSON path")
    ap.add_argument(
        "--seeds-from",
        choices=("none", "factors", "submission", "both"),
        default="factors",
        help="Default factors.json (has {{objective}} scaffolds)",
    )
    ap.add_argument("--max-turns", type=int, default=5)
    ap.add_argument("--tree-width", type=int, default=2)
    ap.add_argument("--tree-depth", type=int, default=3)
    ap.add_argument(
        "--no-filter-halo",
        action="store_true",
        help="Skip Halo input filter (export all templates; for debugging)",
    )
    ap.add_argument("--min-allows", type=int, default=1)
    ap.add_argument("--out", default=str(LAB / "candidates.jsonl"))
    ap.add_argument("--label", default="atk")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    filter_halo = not args.no_filter_halo
    qids = resolve_qids(args)
    questions = load_questions(qids)
    seeds_path = Path(args.seeds) if args.seeds else None
    seeds = load_seeds(args.seeds_from, seeds_path)

    print(f"=== PyRIT attack === mode={args.mode} qids={','.join(qids)} seeds={len(seeds)}")
    print(describe_targets())

    if args.dry_run:
        print("dry-run: would attack", [s["id"] for s in seeds], "qs", qids)
        return 0

    # PyRIT memory
    from pyrit.setup import IN_MEMORY, initialize_pyrit_async

    await initialize_pyrit_async(memory_db_type=IN_MEMORY)

    need_claw = args.mode in ("crescendo", "pair", "redteam", "all")
    if need_claw and not await health_ok():
        raise SystemExit("ERROR: OpenClaw not healthy — required for multi-turn modes")

    candidates: list[dict] = []
    attack_log: list[dict] = []

    # --- LLM template mutation ---
    if args.mode in ("llm", "all"):
        kinds = [k.strip().lower() for k in args.llm_kinds.split(",") if k.strip()]
        attacker = make_attacker_target()
        print(f"=== LLM converters kinds={kinds} ===")
        for seed in seeds:
            print(f"seed {seed['id']}")
            mutated = await convert_seed_llm(seed, attacker, kinds)
            candidates.extend(mutated)
        # always keep originals too
        for seed in seeds:
            candidates.append({"id": seed["id"], "prompt": seed["prompt"], "via": "seed"})

    # --- multi-turn ---
    if args.mode in ("crescendo", "pair", "redteam", "all"):
        mt_mode = "crescendo" if args.mode == "all" else args.mode
        for q in questions:
            qid = str(q.get("question_id") or q.get("id"))
            obj = q.get("objective") or ""
            try:
                row = await run_multi_turn(
                    mode=mt_mode,
                    objective=obj,
                    qid=qid,
                    max_turns=args.max_turns,
                    tree_width=args.tree_width,
                    tree_depth=args.tree_depth,
                )
            except Exception as e:
                print(f"attack fail {qid}: {e}", file=sys.stderr)
                attack_log.append({"question_id": qid, "error": str(e)})
                continue
            attack_log.append(row)
            for i, tmpl in enumerate(row.get("templates") or []):
                candidates.append(
                    {
                        "id": f"{mt_mode}_{qid}_u{i}",
                        "prompt": tmpl,
                        "via": mt_mode,
                        "question_id": qid,
                    }
                )

    # dedupe by prompt
    deduped: list[dict] = []
    seen_p: set[str] = set()
    for c in candidates:
        p = c["prompt"]
        if p in seen_p:
            continue
        seen_p.add(p)
        deduped.append(c)
    candidates = deduped
    print(f"candidate templates before halo: {len(candidates)}")

    api_key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if filter_halo:
        if not api_key:
            raise SystemExit("CHUTES_API_KEY required for --filter-halo")
        candidates = await halo_filter_templates(candidates, questions, api_key, args.min_allows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps({"id": c["id"], "prompt": c["prompt"], "meta": c.get("meta") or {"via": c.get("via")}}, ensure_ascii=False) + "\n")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    detail = LAB / "lab" / f"pyrit-attack-{ts}-{args.label}.json"
    detail.parent.mkdir(parents=True, exist_ok=True)
    detail.write_text(
        json.dumps(
            {
                "utc": ts,
                "label": args.label,
                "mode": args.mode,
                "qids": qids,
                "attack_log": attack_log,
                "export": [{"id": c["id"], "via": c.get("via"), "meta": c.get("meta")} for c in candidates],
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({len(candidates)} templates)")
    print(f"Wrote {detail}")
    if candidates:
        print("Next: python3 miner-lab/test_candidates.py -f", out, "--mode template --promote best")
        print("Then: python3 miner-lab/test_template.py --stage b --question", ",".join(qids), "--label", args.label)
    else:
        print("No survivors — try --mode llm, more seeds, or --no-filter-halo to inspect raw templates")
    return 0


def main() -> int:
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
