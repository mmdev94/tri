"""OpenClaw chat completions (full stack: input Halo → Qwen → output Halo)."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE = os.environ.get("OPENCLAW_URL", "http://127.0.0.1:18789").rstrip("/")


def chat_url(base: str | None = None) -> str:
    u = (base or DEFAULT_BASE).rstrip("/")
    if u.endswith("/v1/chat/completions"):
        return u
    return f"{u}/v1/chat/completions"


def gateway_token() -> str:
    return (
        os.environ.get("OPENCLAW_GATEWAY_PASSWORD")
        or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or ""
    ).strip()


def is_output_blocked(text: str) -> bool:
    t = (text or "").lower()
    return "blocked by output guard" in t or "blocked by the output guard" in t


async def chat_async(
    prompt: str,
    *,
    token: str | None = None,
    base: str | None = None,
    model: str = "openclaw",
    timeout: float = 300.0,
) -> dict[str, Any]:
    tok = (token if token is not None else gateway_token()).strip()
    if not tok:
        raise RuntimeError("OPENCLAW_GATEWAY_PASSWORD (or OPENCLAW_GATEWAY_TOKEN) missing")

    url = chat_url(base)
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": "miner-lab-pyrit-openclaw/1",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=body)
        if r.status_code >= 400:
            return {
                "ok": False,
                "status_code": r.status_code,
                "text": f"OPENCLAW_ERROR: {r.status_code} {r.text[:500]}",
                "output_blocked": False,
            }
        data = r.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        text = json_fallback(data)
    text = text if isinstance(text, str) else str(text)
    return {
        "ok": True,
        "status_code": r.status_code,
        "text": text,
        "output_blocked": is_output_blocked(text),
        "raw": data,
    }


def json_fallback(data: Any) -> str:
    import json

    return json.dumps(data)[:2000]


async def health_ok(base: str | None = None, timeout: float = 2.0) -> bool:
    root = (base or DEFAULT_BASE).rstrip("/")
    if root.endswith("/v1/chat/completions"):
        root = root[: -len("/v1/chat/completions")]
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{root}/health")
            return r.status_code < 500
    except Exception:
        return False
