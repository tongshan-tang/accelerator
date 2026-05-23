#!/usr/bin/env python3
"""Generate human-readable artifacts for sparse type definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
SRC_DIR = SOFT_ROOT / "src" / "02_sparse_format" / "01_sparse_types"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sparse_types import CSCMatrix, CSRMatrix, SparseMatrixRaw


def build_examples() -> tuple[SparseMatrixRaw, CSRMatrix, CSCMatrix]:
    raw = SparseMatrixRaw(
        name="demo_raw_A",
        rows=6,
        cols=10,
        axis="row",
        indices=((0, 3, 8), (), (1, 4), (2, 5, 9), (7,), (0, 6)),
        values=(
            (np.float16(1.25), np.float16(-0.5), np.float16(0.875)),
            (),
            (np.float16(2.0), np.float16(0.75)),
            (np.float16(-1.5), np.float16(3.25), np.float16(0.125)),
            (np.float16(-0.25),),
            (np.float16(1.75), np.float16(-2.0)),
        ),
    )
    csr = CSRMatrix(
        name="demo_csr_A",
        rows=6,
        cols=10,
        row_ptr=np.array([0, 3, 3, 5, 8, 9, 11], dtype=np.int32),
        col_idx=np.array([0, 3, 8, 1, 4, 2, 5, 9, 7, 0, 6], dtype=np.int16),
        data=np.array(
            [1.25, -0.5, 0.875, 2.0, 0.75, -1.5, 3.25, 0.125, -0.25, 1.75, -2.0],
            dtype=np.float16,
        ),
    )
    csc = CSCMatrix(
        name="demo_csc_B",
        rows=10,
        cols=5,
        col_ptr=np.array([0, 2, 5, 5, 8, 10], dtype=np.int32),
        row_idx=np.array([0, 6, 1, 4, 9, 2, 5, 8, 3, 7], dtype=np.int16),
        data=np.array(
            [1.5, -1.0, 0.25, 2.5, -0.75, 1.125, -2.25, 0.5, 3.0, -0.375],
            dtype=np.float16,
        ),
    )
    return raw, csr, csc


def build_summary() -> dict[str, object]:
    raw, csr, csc = build_examples()
    return {
        "step": "02_sparse_format",
        "implemented_module": "sparse_types.py",
        "purpose": "Define normalized sparse matrix containers used by later converters and golden models.",
        "example_generation": "deterministic_manual",
        "example_note": "Examples are fixed hand-written matrices, not random outputs.",
        "types": {
            "SparseMatrixRaw": {
                "role": "Sparse structure before CSR/CSC packing; values may be absent or generated later.",
                "fields": ["name", "rows", "cols", "axis", "indices", "values", "diagnostics"],
                "main_checks": [
                    "positive rows/cols",
                    "record count matches axis outer size",
                    "indices are strictly increasing per record",
                    "indices are in range",
                    "values length matches indices when present",
                ],
                "example": raw.summary(),
            },
            "CSRMatrix": {
                "role": "Compressed sparse row matrix, used for A in matrix multiplication.",
                "fields": ["name", "rows", "cols", "row_ptr", "col_idx", "data", "diagnostics"],
                "main_checks": [
                    "row_ptr length is rows + 1",
                    "row_ptr starts at 0 and is monotonic",
                    "row_ptr[-1] equals index/data length",
                    "col_idx is in range",
                    "indices are strictly increasing inside each row segment",
                ],
                "example": {
                    **csr.summary(),
                    "row_ptr": csr.row_ptr.tolist(),
                    "col_idx": csr.col_idx.tolist(),
                    "data_fp16": [float(x) for x in csr.data],
                },
            },
            "CSCMatrix": {
                "role": "Compressed sparse column matrix, used for B in matrix multiplication.",
                "fields": ["name", "rows", "cols", "col_ptr", "row_idx", "data", "diagnostics"],
                "main_checks": [
                    "col_ptr length is cols + 1",
                    "col_ptr starts at 0 and is monotonic",
                    "col_ptr[-1] equals index/data length",
                    "row_idx is in range",
                    "indices are strictly increasing inside each column segment",
                ],
                "example": {
                    **csc.summary(),
                    "col_ptr": csc.col_ptr.tolist(),
                    "row_idx": csc.row_idx.tolist(),
                    "data_fp16": [float(x) for x in csc.data],
                },
            },
        },
        "next_artifacts": [
            "generated FP16 values for official CASE sparse positions",
            "raw-to-CSR/CSC conversion outputs",
            "random sparse case generation outputs",
        ],
    }


def build_text_report(summary: dict[str, object]) -> str:
    lines = [
        "02_sparse_format sparse type summary",
        "",
        f"implemented_module: {summary['implemented_module']}",
        f"purpose: {summary['purpose']}",
        "",
    ]
    types = summary["types"]
    assert isinstance(types, dict)
    for type_name, type_info in types.items():
        assert isinstance(type_info, dict)
        lines.append(f"[{type_name}]")
        lines.append(f"  role   : {type_info['role']}")
        lines.append(f"  fields : {', '.join(type_info['fields'])}")
        lines.append("  checks :")
        for check in type_info["main_checks"]:
            lines.append(f"    - {check}")
        lines.append("  example:")
        example = type_info["example"]
        assert isinstance(example, dict)
        for key, value in example.items():
            lines.append(f"    {key}: {value}")
        lines.append("")
    lines.append("next_artifacts:")
    for item in summary["next_artifacts"]:
        lines.append(f"  - {item}")
    return "\n".join(lines)


def write_reports(out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    text_path = out_dir / "sparse_types_summary.txt"
    json_path = out_dir / "sparse_types_summary.json"
    text_path.write_text(build_text_report(summary) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return text_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SOFT_ROOT / "output" / "02_sparse_format" / "01_sparse_types",
        help="Directory where sparse type reports will be written.",
    )
    args = parser.parse_args()

    text_path, json_path = write_reports(args.out_dir)
    print(f"wrote: {text_path}")
    print(f"wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
