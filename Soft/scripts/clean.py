#!/usr/bin/env python3
"""Clean Soft/output artifacts by step number."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SOFT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = SOFT_ROOT / "output"

STEP_OUTPUTS = {
    "01": "01_inspect_case",
    "02": "02_sparse_format",
    "03": "03_fp_model",
    "04": "04_matmul_model",
    "05": "05_addsub_model",
    "06": "06_stimulus",
    "07": "07_checker",
}


def clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def resolve_targets(step_args: list[str]) -> list[Path]:
    if not step_args:
        raise ValueError("at least one step is required, for example: 01")

    normalized = [item.strip().lower() for item in step_args]
    if "all" in normalized:
        return [OUTPUT_ROOT / name for name in STEP_OUTPUTS.values()]

    targets: list[Path] = []
    for step in normalized:
        step_key = step.zfill(2) if step.isdigit() else step
        if step_key not in STEP_OUTPUTS:
            valid = ", ".join(STEP_OUTPUTS)
            raise ValueError(f"unsupported step {step!r}; valid steps: {valid}, all")
        targets.append(OUTPUT_ROOT / STEP_OUTPUTS[step_key])
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "steps",
        nargs="+",
        help="Step numbers to clean, e.g. 01 02, or all.",
    )
    args = parser.parse_args()

    try:
        targets = resolve_targets(args.steps)
    except ValueError as exc:
        parser.error(str(exc))

    for target in targets:
        clean_dir(target)
        print(f"cleaned: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
