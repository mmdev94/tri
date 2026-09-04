"""
PyRIT LLM + deterministic mutations that preserve {{objective}}.

Used to expand Halo search space after dimension-based generation.
"""

from __future__ import annotations

import asyncio
import re
from typing import Callable

OBJ_RE = re.compile(r"\{\{\s*objective\s*\}\}", flags=re.I)
PLACEHOLDER = "{{objective}}"
SENTINEL = "[[USER_OBJECTIVE_SLOT]]"

ConverterFactory = Callable[[], object]


def _split_scaffold(template: str) -> tuple[str, str, str]:
    m = OBJ_RE.search(template)
    if not m:
        raise ValueError("template missing {{objective}}")
    return template[: m.start()], PLACEHOLDER, template[m.end() :]


def _join(left: str, right: str) -> str:
    return f"{left}{PLACEHOLDER}{right}"


async def _convert_text(converter: object, text: str) -> str:
    if not text:
        return text
    result = await converter.convert_async(prompt=text, input_type="text")  # type: ignore[attr-defined]
    out = getattr(result, "output_text", None)
    if out is None:
        out = str(result)
    return str(out)


def deterministic_converters() -> dict[str, ConverterFactory]:
    from pyrit.converter import (
        LeetspeakConverter,
        ROT13Converter,
        ZeroWidthConverter,
        StringJoinConverter,
        CaesarConverter,
        RandomCapitalLettersConverter,
    )

    return {
        "leet": LeetspeakConverter,
        "rot13": ROT13Converter,
        "zero_width": ZeroWidthConverter,
        "join": lambda: StringJoinConverter(join_value="*"),
        "caesar": lambda: CaesarConverter(caesar_offset=3),
        "randcap": RandomCapitalLettersConverter,
    }


def with_sentinel(template: str) -> str:
    return OBJ_RE.sub(SENTINEL, template, count=1)


def from_sentinel(text: str) -> str | None:
    t = (text or "").strip()
    if SENTINEL not in t:
        # model may have echoed {{objective}}
        if OBJ_RE.search(t):
            t = OBJ_RE.sub(SENTINEL, t, count=1)
        else:
            return None
    if t.count(SENTINEL) > 1:
        a, b = t.split(SENTINEL, 1)
        t = a + SENTINEL + b.replace(SENTINEL, "")
    out = t.replace(SENTINEL, PLACEHOLDER, 1)
    if out.count(PLACEHOLDER) != 1 or len(out) > 2000 or len(out) < 40:
        return None
    return out


async def convert_template_det(template: str, names: list[str]) -> str:
    left, _, right = _split_scaffold(template)
    catalog = deterministic_converters()
    for name in names:
        key = name.strip().lower()
        if not key or key in ("none", "-"):
            continue
        if key not in catalog:
            raise ValueError(f"unknown det converter {name!r}")
        conv = catalog[key]()
        left = await _convert_text(conv, left)
        right = await _convert_text(conv, right)
    out = _join(left, right)
    if not OBJ_RE.search(out) or len(out) > 2000:
        raise RuntimeError("det convert broke template")
    return out


async def mutate_llm(template: str, kind: str, attacker) -> str:
    """
    kind: vary | tone_<name> | persuade_<technique>
    Operates on sentinel form so {{objective}} survives.
    """
    from pyrit.converter import PersuasionConverter, ToneConverter, VariationConverter

    base = with_sentinel(template)
    if kind == "vary" or kind == "variation":
        conv = VariationConverter(converter_target=attacker)
    elif kind.startswith("tone_"):
        tone = kind[len("tone_") :]
        conv = ToneConverter(converter_target=attacker, tone=tone)
    elif kind.startswith("persuade_"):
        tech = kind[len("persuade_") :]
        conv = PersuasionConverter(converter_target=attacker, persuasion_technique=tech)
    else:
        raise ValueError(f"unknown llm mutate kind {kind!r}")

    result = await conv.convert_async(prompt=base, input_type="text")
    text = getattr(result, "output_text", None) or ""
    out = from_sentinel(text)
    if not out:
        raise RuntimeError(f"llm mutate lost sentinel ({kind})")
    return out


async def expand_with_pyrit(
    templates: list[dict],
    *,
    attacker=None,
    llm_kinds: list[str] | None = None,
    det_kinds: list[str] | None = None,
    max_extra: int = 24,
) -> list[dict]:
    """
    Mutate existing TEMPLATE dicts {id,prompt,...} via PyRIT.
    Skip deterministic obfuscation by default (often worsens Halo).
    """
    llm_kinds = llm_kinds or ["vary", "persuade_logical_appeal", "tone_authoritative", "tone_academic"]
    det_kinds = det_kinds or []  # empty: leet/rot13 usually hurt Halo allow
    out = list(templates)
    seen = {t["prompt"] for t in templates}
    extra = 0

    if attacker is not None:
        for t in list(templates):
            if extra >= max_extra:
                break
            for kind in llm_kinds:
                if extra >= max_extra:
                    break
                try:
                    mutated = await mutate_llm(t["prompt"], kind, attacker)
                except Exception:
                    continue
                if mutated in seen:
                    continue
                seen.add(mutated)
                out.append(
                    {
                        **{k: v for k, v in t.items() if k != "prompt"},
                        "id": f"{t['id']}__{kind}",
                        "prompt": mutated,
                        "via": f"pyrit:{kind}",
                    }
                )
                extra += 1

    for t in list(templates):
        if extra >= max_extra:
            break
        for kind in det_kinds:
            if extra >= max_extra:
                break
            try:
                mutated = await convert_template_det(t["prompt"], [kind])
            except Exception:
                continue
            if mutated in seen:
                continue
            seen.add(mutated)
            out.append(
                {
                    **{k: v for k, v in t.items() if k != "prompt"},
                    "id": f"{t['id']}__det_{kind}",
                    "prompt": mutated,
                    "via": f"pyrit_det:{kind}",
                }
            )
            extra += 1

    return out


def expand_with_pyrit_sync(*args, **kwargs) -> list[dict]:
    return asyncio.run(expand_with_pyrit(*args, **kwargs))
