#!/usr/bin/env python3
"""
Optional: send one prompt through PyRIT PromptSendingAttack → OpenClaw.

Sandbox for multi-converter attacks. For mining score, prefer run_filter.py
(Halo allow + stack) then test_template.py Stage B.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


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


async def main() -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True, help="Full user prompt (already expanded)")
    ap.add_argument(
        "--endpoint",
        default=os.environ.get("OPENCLAW_URL", "http://127.0.0.1:18789").rstrip("/"),
        help="OpenClaw base URL (…/v1 will be used for OpenAIChatTarget)",
    )
    args = ap.parse_args()

    token = (
        os.environ.get("OPENCLAW_GATEWAY_PASSWORD")
        or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or ""
    ).strip()
    if not token:
        print("ERROR: OPENCLAW_GATEWAY_PASSWORD missing", file=sys.stderr)
        return 2

    from pyrit.setup import IN_MEMORY, initialize_pyrit_async
    from pyrit.executor.attack import PromptSendingAttack
    from pyrit.prompt_target import OpenAIChatTarget

    await initialize_pyrit_async(memory_db_type=IN_MEMORY)

    base = args.endpoint.rstrip("/")
    if base.endswith("/v1/chat/completions"):
        base = base[: -len("/v1/chat/completions")]
    if not base.endswith("/v1"):
        base = f"{base}/v1"

    target = OpenAIChatTarget(
        endpoint=base,
        api_key=token,
        model_name="openclaw",
    )
    attack = PromptSendingAttack(objective_target=target)
    result = await attack.execute_async(objective=args.prompt)
    # best-effort print
    text = getattr(result, "last_response", None) or result
    preview = getattr(text, "converted_value", None) or getattr(text, "original_value", None) or str(text)
    print(str(preview)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
