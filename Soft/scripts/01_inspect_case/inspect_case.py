#!/usr/bin/env python3
"""Inspect official CASE sparse matrix files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOFT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOFT_ROOT.parent
STEP_DIR = Path(__file__).resolve().parent
SRC_DIR = SOFT_ROOT / "src" / "01_inspect_case"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from case_parser import CaseMatrixProfile, parse_case_dir


def matrix_summary(matrix: CaseMatrixProfile) -> dict[str, object]:
    return {
        "name": matrix.name,
        "axis": matrix.axis,
        "rows": matrix.rows,
        "cols": matrix.cols,
        "axis_outer_size": matrix.outer_size,
        "axis_inner_size": matrix.inner_size,
        "nnz": matrix.nnz,
        "density": matrix.density,
        "empty_line_count": matrix.empty_line_count,
        "max_line_weight": matrix.max_line_weight,
        "max_line_density": matrix.max_line_density,
        "index_min": matrix.index_min,
        "index_max": matrix.index_max,
        "diagnostics": list(matrix.diagnostics),
    }


def build_text_report(matrices: dict[str, CaseMatrixProfile]) -> str:
    lines: list[str] = []
    for name, matrix in sorted(matrices.items()):
        lines.append(f"[{name}]")
        lines.append(f"  axis        : {matrix.axis}")
        lines.append(f"  rows        : {matrix.rows}")
        lines.append(f"  cols        : {matrix.cols}")
        lines.append(f"  nnz         : {matrix.nnz}")
        lines.append(f"  density     : {matrix.density:.6f}")
        lines.append(f"  empty_line_count : {matrix.empty_line_count}")
        lines.append(f"  max_line_weight  : {matrix.max_line_weight}")
        lines.append(f"  max_line_density : {matrix.max_line_density:.6f}")
        lines.append(f"  index_range : {matrix.index_min}..{matrix.index_max}")
        if matrix.diagnostics:
            lines.append("  diagnostics :")
            for item in matrix.diagnostics:
                lines.append(f"    - {item}")
        else:
            lines.append("  diagnostics : none")
        lines.append("")
    return "\n".join(lines)


def write_reports(
    matrices: dict[str, CaseMatrixProfile],
    out_dir: Path,
    *,
    text_name: str = "case_inspect.txt",
    json_name: str = "case_inspect.json",
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / text_name
    json_path = out_dir / json_name

    text_path.write_text(build_text_report(matrices) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps({k: matrix_summary(v) for k, v in matrices.items()}, indent=2) + "\n",
        encoding="utf-8",
    )
    return text_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=REPO_ROOT / "CASE",
        help="Directory containing official CASE files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SOFT_ROOT / "output" / "01_inspect_case",
        help="Directory where report files will be written.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Only print to stdout; do not write report files.",
    )
    args = parser.parse_args()

    matrices = parse_case_dir(args.case_dir)
    if not args.no_write:
        text_path, json_path = write_reports(matrices, args.out_dir)
        print(f"wrote: {text_path}")
        print(f"wrote: {json_path}")

    if args.json:
        print(json.dumps({k: matrix_summary(v) for k, v in matrices.items()}, indent=2))
    else:
        print(build_text_report(matrices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
