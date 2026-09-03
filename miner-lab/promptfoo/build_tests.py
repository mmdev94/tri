#!/usr/bin/env python3
"""Build promptfoo tests + wrap .txt files; patch prompts: in both configs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
QUESTIONS = LAB / "challenges" / "P3-007-questions.json"
FACTORS = LAB / "factors.json"
WRAPS = HERE / "wraps.json"
OUT_TESTS = HERE / "tests.generated.json"
WRAP_DIR = HERE / "wraps"


def load_questions() -> list[dict]:
    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("questions", [])
    return list(rows)


def load_wraps() -> dict[str, str]:
    raw = json.loads(WRAPS.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for k, v in raw.items():
        if k.startswith("_") or not isinstance(v, str):
            continue
        if v.strip() == "LOAD_FROM_FACTORS":
            if FACTORS.is_file():
                fac = json.loads(FACTORS.read_text(encoding="utf-8"))
                for fk, fv in fac.items():
                    if fk.startswith("_") or not isinstance(fv, str):
                        continue
                    out[f"factors__{fk}"] = fv
            continue
        out[k] = v
    return out


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def write_wrap_files(prompts: list[dict[str, str]]) -> list[str]:
    """Write one .txt per wrap; return relative paths for prompts: list."""
    if WRAP_DIR.exists():
        for old in WRAP_DIR.glob("*.txt"):
            old.unlink()
    else:
        WRAP_DIR.mkdir(parents=True)

    paths: list[str] = []
    for p in prompts:
        fname = f"{safe_name(p['label'])}.txt"
        (WRAP_DIR / fname).write_text(p["raw"], encoding="utf-8")
        paths.append(f"file://wraps/{fname}")
    return paths


def patch_prompts_in_config(cfg_path: Path, prompt_paths: list[str]) -> None:
    text = cfg_path.read_text(encoding="utf-8")
    block = "prompts:\n" + "".join(f"  - {p}\n" for p in prompt_paths) + "\n"
    pattern = r"(?m)^prompts:\n(?:  - .*\n)+\n?"
    if not re.search(pattern, text):
        raise SystemExit(f"{cfg_path.name}: no prompts: block found to patch")
    new = re.sub(pattern, block, text, count=1)
    if "tests:" not in new or "providers:" not in new:
        raise SystemExit(f"{cfg_path.name}: patch ate the rest of the config — abort")
    cfg_path.write_text(new, encoding="utf-8")


def write_openclaw_url() -> None:
    url = (os.environ.get("OPENCLAW_URL") or "http://127.0.0.1:18789").strip().rstrip("/")
    if not url.endswith("/v1/chat/completions"):
        url = f"{url}/v1/chat/completions"
    (HERE / "openclaw-url.txt").write_text(url + "\n", encoding="utf-8")
    cfg = HERE / "promptfooconfig.openclaw.yaml"
    text = cfg.read_text(encoding="utf-8")
    out = []
    seen = False
    for line in text.splitlines(True):
        stripped = line.lstrip()
        if (not seen) and stripped.startswith("url:") and "chat/completions" in line:
            indent = line[: len(line) - len(stripped)]
            out.append(f"{indent}url: {url}\n")
            seen = True
            continue
        out.append(line)
    if not seen:
        raise SystemExit("promptfooconfig.openclaw.yaml missing provider url: line")
    cfg.write_text("".join(out), encoding="utf-8")
    print(f"openclaw url={url}")


def main() -> int:
    questions = load_questions()
    wraps = load_wraps()
    if not questions:
        raise SystemExit(f"no questions in {QUESTIONS}")
    if not wraps:
        raise SystemExit(f"no wraps in {WRAPS}")

    prompts: list[dict[str, str]] = []
    for name, tmpl in wraps.items():
        if not re.search(r"\{\{\s*objective\s*\}\}", tmpl, flags=re.I):
            raise SystemExit(f"wrap {name!r} missing {{{{objective}}}}")
        prompts.append({"label": name, "raw": tmpl})

    tests = []
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        obj = q.get("objective") or ""
        tests.append(
            {
                "description": f"{qid} {q.get('category') or ''}".strip(),
                "vars": {
                    "qid": qid,
                    "category": q.get("category") or "",
                    "objective": obj,
                },
                "metadata": {"question_id": qid, "qid": qid},
            }
        )

    prompt_paths = write_wrap_files(prompts)
    OUT_TESTS.write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")
    for cfg_name in ("promptfooconfig.halo-input.yaml", "promptfooconfig.openclaw.yaml"):
        patch_prompts_in_config(HERE / cfg_name, prompt_paths)
    write_openclaw_url()

    # drop broken prompts.js if present
    js = HERE / "prompts.js"
    if js.is_file():
        js.unlink()

    print(f"wraps={len(prompts)} questions={len(tests)}")
    print(f"wrote {OUT_TESTS}")
    print(f"wrote {WRAP_DIR}/*.txt")
    for p, path in zip(prompts, prompt_paths):
        print(f"  {path} len={len(p['raw'])}")
    for t in tests:
        print(f"  test {t['vars']['qid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
