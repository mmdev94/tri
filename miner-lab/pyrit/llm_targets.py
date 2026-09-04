"""OpenClaw (guarded) + Chutes LLM (unguarded attacker/scorer) PyRIT targets."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyrit.prompt_target import OpenAIChatTarget


def _openclaw_base() -> str:
    u = os.environ.get("OPENCLAW_URL", "http://127.0.0.1:18789").rstrip("/")
    if u.endswith("/v1/chat/completions"):
        u = u[: -len("/v1/chat/completions")]
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def _gateway_token() -> str:
    return (
        os.environ.get("OPENCLAW_GATEWAY_PASSWORD")
        or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or ""
    ).strip()


def _chutes_llm_base() -> str:
    u = (
        os.environ.get("CHUTES_LLM_URL")
        or os.environ.get("CHUTES_BASE_URL")
        or "https://llm.chutes.ai/v1"
    ).rstrip("/")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")]
    if not u.endswith("/v1"):
        u = f"{u}/v1"
    return u


def _chutes_model() -> str:
    return (
        os.environ.get("CHUTES_ATTACK_MODEL")
        or os.environ.get("EVOLVE_LLM_MODEL")
        or os.environ.get("CHUTES_DEFAULT_MODEL_ID")
        or "Qwen/Qwen3.8-27B-TEE"
    ).strip()


def make_openclaw_target(*, model_name: str = "openclaw") -> "OpenAIChatTarget":
    """Objective target: full stack (input Halo → chat → output Halo)."""
    from pyrit.prompt_target import OpenAIChatTarget

    tok = _gateway_token()
    if not tok:
        raise RuntimeError("OPENCLAW_GATEWAY_PASSWORD (or OPENCLAW_GATEWAY_TOKEN) missing")
    return OpenAIChatTarget(
        endpoint=_openclaw_base(),
        api_key=tok,
        model_name=model_name,
    )


def make_attacker_target() -> "OpenAIChatTarget":
    """Adversarial / converter / scorer LLM — direct Chutes chat (no Halo)."""
    from pyrit.prompt_target import OpenAIChatTarget

    key = (os.environ.get("CHUTES_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("CHUTES_API_KEY missing (needed for attacker LLM)")
    return OpenAIChatTarget(
        endpoint=_chutes_llm_base(),
        api_key=key,
        model_name=_chutes_model(),
    )


def describe_targets() -> str:
    return (
        f"objective=OpenClaw({_openclaw_base()}) "
        f"attacker=Chutes({_chutes_llm_base()} model={_chutes_model()})"
    )
