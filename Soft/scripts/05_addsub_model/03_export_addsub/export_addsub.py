#!/usr/bin/env python3
"""Export dense FP16 add/sub golden for one generated demo pair."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
SRC_ADD_SUB_ROOT = SOFT_ROOT / "src" / "05_addsub_model"
for path in (
    SRC_ADD_SUB_ROOT / "01_sparse_pair_loader",
    SRC_ADD_SUB_ROOT / "02_dense_golden",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dense_addsub import addsub_from_generated_pair, write_result


def generated_root() -> Path:
    return SOFT_ROOT / "output" / "02_sparse_format" / "05_case_generator"


def default_out_dir() -> Path:
    return SOFT_ROOT / "output" / "05_addsub_model"


def resolve_demo_path(path_arg: str | Path) -> Path:
    path = Path(path_arg)
    if path.exists():
        if path.is_dir() and path.parent.name == "addsub" and path.parent.parent.name == "demo":
            return path
        raise ValueError(f"{path}: --path currently supports generated add/sub demo directories only")

    root = generated_root()
    demo_dir = root / "demo" / "addsub" / str(path_arg)
    if demo_dir.exists():
        return demo_dir
    if (root / "case" / str(path_arg)).exists():
        raise ValueError(f"{path_arg}: case directories are not handled by 05 yet")
    if (root / "demo" / "mul" / str(path_arg)).exists():
        raise ValueError(f"{path_arg}: multiplication demos are not handled by 05")
    raise ValueError(f"{path_arg}: not found under {root / 'demo' / 'addsub'}")


def demo_pair_file(source_dir: Path) -> Path:
    pair_files = sorted(source_dir.glob("*_pair*.json"))
    if len(pair_files) != 1:
        raise ValueError(f"{source_dir}: exactly one demo pair JSON is required, got {len(pair_files)}")
    return pair_files[0]


def export_demo_path(path_arg: str | Path, out_dir: Path) -> list[Path]:
    source_dir = resolve_demo_path(path_arg)
    pair_file = demo_pair_file(source_dir)
    result = addsub_from_generated_pair(pair_file)
    return list(write_result(result, out_dir / "demo" / source_dir.name, pair_file.stem))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        required=True,
        help="Generated add/sub demo name or directory under Soft/output/02_sparse_format/05_case_generator/demo/addsub.",
    )
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    args = parser.parse_args()

    try:
        paths = export_demo_path(args.path, args.out_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
