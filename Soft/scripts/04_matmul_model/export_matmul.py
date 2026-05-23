#!/usr/bin/env python3
"""Export dense matmul golden and task trace for a sparse A/B pair."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SOFT_ROOT = Path(__file__).resolve().parents[2]
STEP_DIR = Path(__file__).resolve().parent
SRC_MATMUL_ROOT = SOFT_ROOT / "src" / "04_matmul_model"
for path in (
    SRC_MATMUL_ROOT / "01_sparse_array_loader",
    SRC_MATMUL_ROOT / "02_merge_matcher",
    SRC_MATMUL_ROOT / "03_dense_golden",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dense_matmul import matmul_from_files, matmul_from_generated_pair, write_result


def default_sparse_out() -> Path:
    return SOFT_ROOT / "output" / "02_sparse_format" / "04_export_sparse_arrays"


def generated_root() -> Path:
    return SOFT_ROOT / "output" / "02_sparse_format" / "05_case_generator"


def default_out_dir() -> Path:
    return SOFT_ROOT / "output" / "04_matmul_model"


def resolve_generated_path(path_arg: str | Path) -> tuple[str, Path]:
    """Resolve --path as either an explicit demo directory or a demo name."""

    path = Path(path_arg)
    if path.exists():
        if path.is_dir():
            parent_name = path.parent.name
            if parent_name != "mul" or path.parent.parent.name != "demo":
                raise ValueError(f"{path}: --path currently supports generated multiplication demo directories only")
            return "demo", path
        raise ValueError(f"{path}: --path must point to a generated multiplication demo directory")

    root = generated_root()
    demo_dir = root / "demo" / "mul" / str(path_arg)
    if demo_dir.exists():
        return "demo", demo_dir
    if (root / "case" / str(path_arg)).exists():
        raise ValueError(f"{path_arg}: case directories are not handled by 04 yet")
    if (root / "demo" / "addsub" / str(path_arg)).exists():
        raise ValueError(f"{path_arg}: add/sub demos are not handled by 04")
    raise ValueError(f"{path_arg}: not found under {root / 'demo' / 'mul'}")


def demo_pair_file(source_dir: Path) -> Path:
    """Return the single pair JSON file from one generated demo directory."""

    pair_files = sorted(source_dir.glob("*_pair*.json"))
    if len(pair_files) != 1:
        raise ValueError(f"{source_dir}: exactly one demo pair JSON is required, got {len(pair_files)}")
    return pair_files[0]


def export_generated_path(path_arg: str | Path, out_dir: Path) -> list[Path]:
    source_kind, source_dir = resolve_generated_path(path_arg)
    target_dir = out_dir / source_kind / "mul" / source_dir.name
    pair_file = demo_pair_file(source_dir)
    result = matmul_from_generated_pair(pair_file)
    return list(write_result(result, target_dir, pair_file.stem))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, default=default_sparse_out() / "A_0_sparse_arrays.json")
    parser.add_argument("--b", type=Path, default=default_sparse_out() / "B_0_sparse_arrays.json")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Generated multiplication demo name or directory under Soft/output/02_sparse_format/05_case_generator/demo/mul.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=default_out_dir(),
    )
    parser.add_argument("--name", type=str, default=None)
    args = parser.parse_args()

    if args.path is not None:
        try:
            paths = export_generated_path(args.path, args.out_dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for path in paths:
            print(f"wrote: {path}")
        return 0

    result = matmul_from_files(args.a, args.b)
    name = args.name or f"{result['summary']['a_name']}_{result['summary']['b_name']}"
    paths = write_result(result, args.out_dir / "manual" / name, name)
    for path in paths:
        print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
