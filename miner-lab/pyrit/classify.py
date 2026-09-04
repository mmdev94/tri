"""Halo input/output classify via Chutes (same APIs as miner-lab Stage A / Promptfoo)."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

INPUT_URL = os.environ.get(
    "HALO_CLASSIFY_URL", "https://astroboi-halo-guard.chutes.ai/v1/classify"
).rstrip("/")
INPUT_MODEL = os.environ.get("HALO_CLASSIFY_MODEL", "halo-guard")
OUTPUT_URL = os.environ.get(
    "HALO_OUTPUT_CLASSIFY_URL",
    "https://astroboi-halo-output-guard.chutes.ai/v1/classify",
).rstrip("/")
OUTPUT_MODEL = os.environ.get("HALO_OUTPUT_CLASSIFY_MODEL", "halo-output-guard")


def summarize(resp: dict[str, Any]) -> dict[str, Any]:
    status = (resp.get("status") or resp.get("safety_label") or resp.get("safety") or "")
    status_u = status.upper() if isinstance(status, str) else str(status).upper()
    label = str(resp.get("safety_label") or "").lower()
    if status_u in ("HARMFUL", "UNSAFE") or label == "unsafe":
        verdict = "block"
    elif status_u in ("HARMLESS", "SAFE") or label == "safe":
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
        "status": status_u or status,
        "raw": resp,
    }


async def classify_async(
    query: str,
    api_key: str,
    *,
    role: str = "input",
    url: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    role = role.lower().strip()
    if role == "output":
        url = url or OUTPUT_URL
        model = model or OUTPUT_MODEL
    else:
        url = url or INPUT_URL
        model = model or INPUT_MODEL
        role = "input"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "miner-lab-pyrit-classify/1",
    }
    body = {"model": model, "query": query, "role": role}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    out = summarize(data)
    out["url"] = url
    out["model"] = model
    out["role"] = role
    return out


def classify_sync(
    query: str,
    api_key: str,
    *,
    role: str = "input",
    url: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    role = role.lower().strip()
    if role == "output":
        url = url or OUTPUT_URL
        model = model or OUTPUT_MODEL
    else:
        url = url or INPUT_URL
        model = model or INPUT_MODEL
        role = "input"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "miner-lab-pyrit-classify/1",
    }
    body = {"model": model, "query": query, "role": role}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    out = summarize(data)
    out["url"] = url
    out["model"] = model
    out["role"] = role
    return out


def dumps_brief(summary: dict[str, Any]) -> str:
    return json.dumps(
        {
            "verdict": summary.get("verdict"),
            "status": summary.get("status"),
            "category": summary.get("category"),
            "confidence": summary.get("confidence"),
        },
        ensure_ascii=False,
    )
