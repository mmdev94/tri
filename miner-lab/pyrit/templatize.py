"""Turn an expanded attack prompt back into a TEMPLATE with {{objective}}."""

from __future__ import annotations

import re

PLACEHOLDER = "{{objective}}"
SENTINEL = "[[USER_OBJECTIVE_SLOT]]"


def templatize(prompt: str, objective: str, *, max_len: int = 2000) -> str | None:
    """Replace first occurrence of objective with {{objective}}. None if unsafe/unusable."""
    text = (prompt or "").strip()
    obj = (objective or "").strip()
    if not text or not obj:
        return None
    if PLACEHOLDER in text or re.search(r"\{\{\s*objective\s*\}\}", text, flags=re.I):
        # already a template
        out = re.sub(r"\{\{\s*objective\s*\}\}", PLACEHOLDER, text, count=1, flags=re.I)
        return out if len(out) <= max_len else None

    idx = text.find(obj)
    if idx < 0:
        # case-insensitive
        m = re.search(re.escape(obj), text, flags=re.I)
        if not m:
            return None
        out = text[: m.start()] + PLACEHOLDER + text[m.end() :]
    else:
        out = text[:idx] + PLACEHOLDER + text[idx + len(obj) :]

    if out.count(PLACEHOLDER) != 1:
        return None
    if len(out) > max_len:
        return None
    return out


def with_sentinel(template: str) -> str:
    return re.sub(r"\{\{\s*objective\s*\}\}", SENTINEL, template, count=1, flags=re.I)


def from_sentinel(text: str) -> str | None:
    if SENTINEL not in text:
        return None
    out = text.replace(SENTINEL, PLACEHOLDER, 1)
    if out.count(PLACEHOLDER) != 1:
        return None
    if len(out) > 2000:
        return None
    return out
