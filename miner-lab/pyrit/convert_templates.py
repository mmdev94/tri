"""Apply PyRIT converters to TEMPLATE scaffolds while preserving {{objective}}."""

from __future__ import annotations

import asyncio
import re
from typing import Callable

OBJ_RE = re.compile(r"\{\{\s*objective\s*\}\}", flags=re.I)
PLACEHOLDER = "{{objective}}"

# name -> factory that returns a PromptConverter instance
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


def available_converters() -> dict[str, ConverterFactory]:
    from pyrit.converter import (
        LeetspeakConverter,
        ROT13Converter,
        ZeroWidthConverter,
        StringJoinConverter,
        CaesarConverter,
        RandomCapitalLettersConverter,
        MorseConverter,
        Base64Converter,
    )

    return {
        "leet": LeetspeakConverter,
        "rot13": ROT13Converter,
        "zero_width": ZeroWidthConverter,
        "join": lambda: StringJoinConverter(join_value="*"),
        "caesar": lambda: CaesarConverter(caesar_offset=3),
        "randcap": RandomCapitalLettersConverter,
        "morse": MorseConverter,
        "b64": Base64Converter,
    }


async def convert_template(template: str, names: list[str]) -> str:
    """Convert left/right scaffold text with each named converter in sequence."""
    left, _, right = _split_scaffold(template)
    catalog = available_converters()
    for name in names:
        key = name.strip().lower()
        if not key or key in ("none", "-"):
            continue
        if key not in catalog:
            raise SystemExit(f"unknown converter {name!r}; choose from: {', '.join(sorted(catalog))}")
        conv = catalog[key]()
        left = await _convert_text(conv, left)
        right = await _convert_text(conv, right)
    out = _join(left, right)
    if not OBJ_RE.search(out):
        raise RuntimeError("converter wiped {{objective}} — refuse")
    if len(out) > 2000:
        raise RuntimeError(f"converted template len={len(out)} > 2000")
    return out


def convert_template_sync(template: str, names: list[str]) -> str:
    return asyncio.run(convert_template(template, names))
