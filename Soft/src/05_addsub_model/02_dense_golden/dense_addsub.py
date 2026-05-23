"""Dense FP16 golden generation for sparse CSR add/sub pairs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

STEP_DIR = Path(__file__).resolve().parent
ADD_SUB_ROOT = STEP_DIR.parent
SOFT_ROOT = STEP_DIR.parents[2]
FP32_ACC_DIR = SOFT_ROOT / "src" / "03_fp_model" / "fp32_acc"
for path in (
    ADD_SUB_ROOT / "01_sparse_pair_loader",
    FP32_ACC_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from addsub_pair_loader import AddSubPair, load_addsub_pair
from fp32_acc import fp16_bits


def csr_to_dense_fp16(matrix) -> np.ndarray:
    """Expand one CSR matrix to dense FP16."""

    if matrix.storage_format != "csr":
        raise ValueError(f"{matrix.name}: expected csr, got {matrix.storage_format}")
    dense = np.zeros((matrix.rows, matrix.cols), dtype=np.float16)
    for row_id in range(matrix.rows):
        start, end = matrix.line_range(row_id)
        for addr in range(start, end):
            dense[row_id, int(matrix.index[addr])] = np.float16(matrix.data[addr])
    return dense


def addsub_sparse_fp16(pair: AddSubPair) -> dict[str, object]:
    """Compute dense C using FP16 add/sub and FP16 output."""

    a_dense = csr_to_dense_fp16(pair.a)
    b_dense = csr_to_dense_fp16(pair.b)
    if pair.operation == "+":
        c_dense = np.float16(a_dense + b_dense)
    elif pair.operation == "-":
        c_dense = np.float16(a_dense - b_dense)
    else:
        raise ValueError(f"unsupported operation: {pair.operation}")

    nonzero_c_count = int(np.count_nonzero(c_dense))
    return {
        "summary": {
            "mode": "fp16_addsub",
            "rule": "FP16 inputs are added/subtracted once and rounded to FP16 output.",
            "operation": pair.operation,
            "a_name": pair.a.name,
            "b_name": pair.b.name,
            "c_rows": pair.a.rows,
            "c_cols": pair.a.cols,
            "nonzero_c_count": nonzero_c_count,
            "zero_c_count": int(pair.a.rows * pair.a.cols - nonzero_c_count),
            "source_pair_json": str(pair.source_path),
            "source_case_name": pair.case_name,
            "source_pair_id": pair.pair_id,
            "source_expression": pair.expression,
            "source_seed_base": pair.seed_base,
        },
        "a_dense_fp16": [[float(x) for x in row] for row in a_dense],
        "b_dense_fp16": [[float(x) for x in row] for row in b_dense],
        "c_dense_fp16": [[float(x) for x in row] for row in c_dense],
        "c_dense_bits": [[fp16_bits(x) for x in row] for row in c_dense],
    }


def addsub_from_generated_pair(pair_path: Path | str) -> dict[str, object]:
    pair = load_addsub_pair(pair_path)
    return addsub_sparse_fp16(pair)


def write_result(result: dict[str, object], out_dir: Path, name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dense_path = out_dir / f"{name}_dense_golden.json"
    text_path = out_dir / f"{name}_dense_golden.txt"
    dense_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    text_path.write_text(build_text_report(result) + "\n", encoding="utf-8")
    return dense_path, text_path


def build_text_report(result: dict[str, object]) -> str:
    summary = result["summary"]
    assert isinstance(summary, dict)
    return "\n".join(
        [
            "05_addsub_model dense golden",
            "",
            f"mode: {summary['mode']}",
            f"operation: {summary['operation']}",
            f"expression: {summary['source_expression']}",
            f"A: {summary['a_name']}",
            f"B: {summary['b_name']}",
            f"C shape: {summary['c_rows']} x {summary['c_cols']}",
            f"nonzero_c_count: {summary['nonzero_c_count']}",
            f"zero_c_count: {summary['zero_c_count']}",
            f"source_pair_json: {summary['source_pair_json']}",
        ]
    )
