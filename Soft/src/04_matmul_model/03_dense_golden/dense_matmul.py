"""Dense golden generation for sparse CSR x CSC matrix multiplication."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

STEP_DIR = Path(__file__).resolve().parent
MATMUL_ROOT = STEP_DIR.parent
SOFT_ROOT = STEP_DIR.parents[2]
FP32_ACC_DIR = SOFT_ROOT / "src" / "03_fp_model" / "fp32_acc"
for path in (
    MATMUL_ROOT / "01_sparse_array_loader",
    MATMUL_ROOT / "02_merge_matcher",
    FP32_ACC_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fp32_acc import finalize_output
from merge_matcher import MatchTask, match_row_col, task_to_dict
from sparse_array_loader import SparseArrays, load_pair, sparse_arrays_from_payload, validate_pair


def matmul_sparse_fp32_acc(a: SparseArrays, b: SparseArrays) -> dict[str, object]:
    """Compute dense C and task trace with FP32 accumulation."""

    c_fp32 = np.zeros((a.rows, b.cols), dtype=np.float32)
    c_fp16 = np.zeros((a.rows, b.cols), dtype=np.float16)
    task_trace: list[dict[str, object]] = []
    per_cell_task_count: list[list[int]] = []

    for row_id in range(a.rows):
        a_base, a_end = a.line_range(row_id)
        row_counts: list[int] = []
        for col_id in range(b.cols):
            b_base, b_end = b.line_range(col_id)
            tasks = match_row_col(
                row_id=row_id,
                col_id=col_id,
                c_cols=b.cols,
                a_base=a_base,
                a_end=a_end,
                a_index=a.index,
                a_data=a.data,
                b_base=b_base,
                b_end=b_end,
                b_index=b.index,
                b_data=b.data,
            )
            acc = np.float32(0.0)
            for task in tasks:
                acc = np.float32(acc + np.float32(task.product_fp32))
                task_trace.append(task_to_dict(task))
            c_fp32[row_id, col_id] = acc
            c_fp16[row_id, col_id] = finalize_output(acc, "fp16")
            row_counts.append(len(tasks))
        per_cell_task_count.append(row_counts)

    nonzero_c_fp32 = int(np.count_nonzero(c_fp32))
    task_count = len(task_trace)
    return {
        "summary": {
            "mode": "fp32_acc",
            "a_name": a.name,
            "b_name": b.name,
            "c_rows": a.rows,
            "c_cols": b.cols,
            "task_count": task_count,
            "nonzero_c_count": nonzero_c_fp32,
            "zero_c_count": int(a.rows * b.cols - nonzero_c_fp32),
            "max_tasks_per_cell": max((max(row) for row in per_cell_task_count), default=0),
        },
        "c_dense_fp32": [[float(x) for x in row] for row in c_fp32],
        "c_dense_fp16": [[float(x) for x in row] for row in c_fp16],
        "per_cell_task_count": per_cell_task_count,
        "task_trace": task_trace,
    }


def matmul_from_files(a_path: Path | str, b_path: Path | str) -> dict[str, object]:
    a, b = load_pair(a_path, b_path)
    return matmul_sparse_fp32_acc(a, b)


def matmul_from_generated_pair(pair_path: Path | str) -> dict[str, object]:
    """Compute matmul from one 02 case_generator pair JSON."""

    pair_path = Path(pair_path)
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    if payload.get("operation") != "*":
        raise ValueError(f"{pair_path}: operation is {payload.get('operation')}, not multiplication")
    matrices = payload["matrices"]
    assert isinstance(matrices, dict)
    a_payload = matrices["A"]
    b_payload = matrices["B"]
    assert isinstance(a_payload, dict)
    assert isinstance(b_payload, dict)
    a, b = validate_pair(
        sparse_arrays_from_payload(a_payload, source=f"{pair_path}:A"),
        sparse_arrays_from_payload(b_payload, source=f"{pair_path}:B"),
    )
    result = matmul_sparse_fp32_acc(a, b)
    summary = result["summary"]
    assert isinstance(summary, dict)
    summary["source_pair_json"] = str(pair_path)
    summary["source_case_name"] = payload.get("case_name")
    summary["source_pair_id"] = payload.get("pair_id")
    summary["source_expression"] = payload.get("expression")
    summary["source_seed_base"] = payload.get("seed_base")
    return result


def write_result(result: dict[str, object], out_dir: Path, name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dense_path = out_dir / f"{name}_dense_golden.json"
    trace_path = out_dir / f"{name}_task_trace.json"
    dense_payload = {
        "summary": result["summary"],
        "c_dense_fp32": result["c_dense_fp32"],
        "c_dense_fp16": result["c_dense_fp16"],
        "per_cell_task_count": result["per_cell_task_count"],
    }
    dense_path.write_text(json.dumps(dense_payload, indent=2) + "\n", encoding="utf-8")
    trace_path.write_text(json.dumps(result["task_trace"], indent=2) + "\n", encoding="utf-8")
    return dense_path, trace_path
