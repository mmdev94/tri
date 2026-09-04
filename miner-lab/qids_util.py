"""Shared Q1–Q6 selection for miner-lab test scripts."""

from __future__ import annotations

import re

VALID_QIDS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
DEFAULT_QIDS = list(VALID_QIDS)


def add_question_args(ap, *, default: str | None = None) -> None:
    """Add --question / --questions / --qids (all optional; default = all)."""
    default_help = default if default is not None else ",".join(DEFAULT_QIDS)
    ap.add_argument(
        "--question",
        "-q",
        action="append",
        default=[],
        metavar="QID",
        help="One question id (repeatable): --question Q3  or  -q Q1 -q Q2",
    )
    ap.add_argument(
        "--questions",
        default="",
        metavar="LIST",
        help="Comma list: --questions Q1,Q2 or --questions Q3",
    )
    ap.add_argument(
        "--qids",
        default="",
        metavar="LIST",
        help=f"Alias of --questions (default when none given: {default_help})",
    )


def _split_tokens(raw: str) -> list[str]:
    return [t for t in re.split(r"[,;\s]+", raw.strip()) if t]


def _normalize_qid(token: str) -> str:
    t = token.strip().upper()
    if not t:
        raise SystemExit("empty question id")
    if t.isdigit():
        t = f"Q{t}"
    if not t.startswith("Q"):
        t = f"Q{t}"
    if t not in VALID_QIDS:
        raise SystemExit(f"invalid question {token!r}; use Q1–Q6")
    return t


def resolve_qids(args, default: list[str] | None = None) -> list[str]:
    """Merge --question / --questions / --qids; preserve order; dedupe."""
    parts: list[str] = []
    for item in getattr(args, "question", None) or []:
        parts.extend(_split_tokens(item))
    for src in (getattr(args, "questions", "") or "", getattr(args, "qids", "") or ""):
        if src.strip():
            parts.extend(_split_tokens(src))

    if not parts:
        return list(default if default is not None else DEFAULT_QIDS)

    out: list[str] = []
    for p in parts:
        qid = _normalize_qid(p)
        if qid not in out:
            out.append(qid)
    return out


def clamp_min_allows(min_allows: int, qids: list[str]) -> int:
    """When testing a subset, don't require more allows than questions."""
    if not qids:
        return min_allows
    return min(min_allows, len(qids))
