#!/usr/bin/env python3
"""Export normalized sparse arrays for official CASE matrices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SOFT_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = SOFT_ROOT.parent
STEP_DIR = Path(__file__).resolve().parent
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
INSPECT_DIR = SOFT_ROOT / "src" / "01_inspect_case"
for path in (
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
    INSPECT_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_parser import parse_case_dir
from sparse_convert import IndexPolicy, convert_profile
from sparse_types import CSCMatrix, CSRMatrix
from value_generator import DEFAULT_VALUE_SEED, fp16_bits


def _fp16_list(data: np.ndarray) -> list[float]:
    return [float(x) for x in data.astype(np.float16)]


def _fp16_bits_list(data: np.ndarray) -> list[str]:
    return [fp16_bits(x) for x in data.astype(np.float16)]


def packed_to_export(packed: CSRMatrix | CSCMatrix) -> dict[str, object]:
    """Convert a CSR/CSC matrix into a compact JSON payload."""

    if isinstance(packed, CSRMatrix):
        return {
            "matrix": matrix_summary(packed, storage_format="csr"),
            "arrays": {
                "ptr_name": "row_ptr",
                "index_name": "col_idx",
                "data_name": "data",
                "ptr": packed.row_ptr.astype(int).tolist(),
                "index": packed.col_idx.astype(int).tolist(),
                "data_fp16": _fp16_list(packed.data),
                "data_bits": _fp16_bits_list(packed.data),
            },
        }
    return {
        "matrix": matrix_summary(packed, storage_format="csc"),
        "arrays": {
            "ptr_name": "col_ptr",
            "index_name": "row_idx",
            "data_name": "data",
            "ptr": packed.col_ptr.astype(int).tolist(),
            "index": packed.row_idx.astype(int).tolist(),
            "data_fp16": _fp16_list(packed.data),
            "data_bits": _fp16_bits_list(packed.data),
        },
    }


def matrix_summary(packed: CSRMatrix | CSCMatrix, *, storage_format: str) -> dict[str, object]:
    """Return non-array matrix metadata without duplicating raw/packed summaries."""

    summary = packed.summary()
    return {
        "name": summary["name"],
        "storage_format": storage_format,
        "rows": summary["rows"],
        "cols": summary["cols"],
        "nnz": summary["nnz"],
        "density": summary["density"],
        "max_line_weight": summary["max_line_weight"],
        "max_line_density": summary["max_line_density"],
        "ptr_len": summary["ptr_len"],
        "index_len": summary["idx_len"],
        "data_len": summary["data_len"],
        "has_values": True,
        "diagnostics": summary["diagnostics"],
    }


def build_exports(
    case_dir: Path,
    *,
    seed: int = DEFAULT_VALUE_SEED,
    index_policy: IndexPolicy = "wrap_inner_dim_to_zero_dedup",
) -> dict[str, dict[str, object]]:
    profiles = parse_case_dir(case_dir)
    exports: dict[str, dict[str, object]] = {}
    for name, profile in sorted(profiles.items()):
        _raw, packed = convert_profile(profile, seed=seed, index_policy=index_policy)
        exports[name] = packed_to_export(packed)
    return exports


def write_exports(
    exports: dict[str, dict[str, object]],
    out_dir: Path,
    *,
    seed: int,
    index_policy: str,
) -> tuple[Path, Path, list[Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_paths: list[Path] = []
    for name, payload in exports.items():
        path = out_dir / f"{name}_sparse_arrays.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        matrix_paths.append(path)

    summary = {
        "step": "02_sparse_format",
        "seed": seed,
        "index_policy": index_policy,
        "matrix_count": len(exports),
        "matrices": {
            name: {
                "matrix": payload["matrix"],
                "arrays": {
                    key: value
                    for key, value in payload["arrays"].items()
                    if key in {"ptr_name", "index_name", "data_name"}
                },
            }
            for name, payload in exports.items()
        },
    }
    summary_json = out_dir / "official_sparse_arrays_summary.json"
    summary_txt = out_dir / "official_sparse_arrays_summary.txt"
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary_txt.write_text(build_text_summary(summary) + "\n", encoding="utf-8")
    return summary_txt, summary_json, matrix_paths


def build_text_summary(summary: dict[str, object]) -> str:
    lines = [
        "02_sparse_format official sparse array summary",
        "",
        f"seed: {summary['seed']}",
        f"index_policy: {summary['index_policy']}",
        f"matrix_count: {summary['matrix_count']}",
        "",
    ]
    matrices = summary["matrices"]
    assert isinstance(matrices, dict)
    for name, payload in matrices.items():
        matrix = payload["matrix"]
        assert isinstance(matrix, dict)
        lines.append(f"[{name}]")
        lines.append(f"  storage_format   : {matrix['storage_format']}")
        lines.append(f"  rows x cols      : {matrix['rows']} x {matrix['cols']}")
        lines.append(f"  nnz              : {matrix['nnz']}")
        lines.append(f"  density          : {matrix['density']:.6f}")
        lines.append(f"  max_line_density : {matrix['max_line_density']:.6f}")
        lines.append(f"  ptr/index/data   : {matrix['ptr_len']} / {matrix['index_len']} / {matrix['data_len']}")
        diagnostics = matrix["diagnostics"]
        if diagnostics:
            lines.append("  diagnostics      :")
            for item in diagnostics:
                lines.append(f"    - {item}")
        else:
            lines.append("  diagnostics      : none")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, default=REPO_ROOT / "CASE")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SOFT_ROOT / "output" / "02_sparse_format" / "04_export_sparse_arrays",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_VALUE_SEED)
    parser.add_argument(
        "--index-policy",
        choices=("strict_zero_based", "wrap_inner_dim_to_zero_dedup"),
        default="wrap_inner_dim_to_zero_dedup",
    )
    args = parser.parse_args()

    exports = build_exports(args.case_dir, seed=args.seed, index_policy=args.index_policy)
    summary_txt, summary_json, matrix_paths = write_exports(
        exports,
        args.out_dir,
        seed=args.seed,
        index_policy=args.index_policy,
    )
    print(f"wrote: {summary_txt}")
    print(f"wrote: {summary_json}")
    for path in matrix_paths:
        print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
