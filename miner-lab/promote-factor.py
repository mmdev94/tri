#!/usr/bin/env python3
"""Copy a named factor from factors.json into submission.json (and optional snapshot)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("factor", help="Key in factors.json (e.g. archive_short)")
    ap.add_argument("--factors", default=str(LAB / "factors.json"))
    ap.add_argument("--out", default=str(LAB / "submission.json"))
    ap.add_argument("--snapshot", action="store_true", help="Also write submission.promoted-<factor>.json")
    args = ap.parse_args()

    factors = json.loads(Path(args.factors).read_text(encoding="utf-8"))
    if args.factor not in factors or args.factor.startswith("_"):
        keys = [k for k in factors if not k.startswith("_")]
        raise SystemExit(f"Unknown factor {args.factor!r}. Available: {', '.join(keys)}")

    prompt = factors[args.factor]
    if "{{objective}}" not in prompt:
        raise SystemExit("Factor must contain {{objective}}")

    out = Path(args.out)
    if out.exists():
        bak = out.with_suffix(out.suffix + ".bak")
        shutil.copy2(out, bak)
        print(f"Backup {bak}")

    payload = {"prompt": prompt}
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} from factor={args.factor} len={len(prompt)}")

    if args.snapshot:
        snap = LAB / f"submission.promoted-{args.factor}.json"
        snap.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Snapshot {snap}")

    note = LAB / "lab" / "NOTEBOOK.md"
    if note.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with note.open("a", encoding="utf-8") as f:
            f.write(f"\n- {ts}: promoted factor `{args.factor}` → `submission.json`\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
