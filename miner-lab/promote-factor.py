#!/usr/bin/env python3
"""Copy a named factor into submission.json (searches factors*.json)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
SEARCH = [
    LAB / "factors.json",
    LAB / "factors.gate.json",
    LAB / "factors.hot.json",
    LAB / "factors.killed.json",
]


def load_all() -> dict[str, tuple[str, Path]]:
    out: dict[str, tuple[str, Path]] = {}
    for path in SEARCH:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k.startswith("_") or not isinstance(v, str):
                continue
            out[k] = (v, path)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("factor", help="Factor key (searched across factors*.json)")
    ap.add_argument("--out", default=str(LAB / "submission.json"))
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument(
        "--allow-gate",
        action="store_true",
        help="Allow promoting from factors.gate.json (score_track=dead)",
    )
    args = ap.parse_args()

    catalog = load_all()
    if args.factor not in catalog:
        raise SystemExit(f"Unknown factor {args.factor!r}. Available: {', '.join(sorted(catalog))}")

    prompt, src = catalog[args.factor]
    if src.name == "factors.gate.json" and not args.allow_gate:
        raise SystemExit(
            f"{args.factor} is in factors.gate.json (score_track=DEAD). "
            "Refusing promote for submit. Use --allow-gate only for gate regression tests."
        )
    if src.name == "factors.killed.json":
        raise SystemExit(f"{args.factor} is killed (judge 0 / toxic). Not promoting.")
    if "{{objective}}" not in prompt:
        raise SystemExit("Factor must contain {{objective}}")

    out = Path(args.out)
    if out.exists():
        bak = out.with_suffix(out.suffix + ".bak")
        shutil.copy2(out, bak)
        print(f"Backup {bak}")

    payload = {"prompt": prompt}
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} from {src.name}:{args.factor} len={len(prompt)}")

    if args.snapshot:
        snap = LAB / f"submission.promoted-{args.factor}.json"
        snap.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Snapshot {snap}")

    note = LAB / "lab" / "NOTEBOOK.md"
    if note.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with note.open("a", encoding="utf-8") as f:
            f.write(f"\n- {ts}: promoted `{src.name}:{args.factor}` → submission.json\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
