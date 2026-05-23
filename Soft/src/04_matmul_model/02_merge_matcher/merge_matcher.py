"""Sparse CSR/CSC merge matcher for matrix multiplication."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MatchTask:
    row_id: int
    col_id: int
    k_index: int
    a_offset: int
    b_offset: int
    a_data_addr: int
    b_data_addr: int
    c_addr: int
    a_value: float
    b_value: float
    product_fp32: float


def match_row_col(
    *,
    row_id: int,
    col_id: int,
    c_cols: int,
    a_base: int,
    a_end: int,
    a_index: np.ndarray,
    a_data: np.ndarray,
    b_base: int,
    b_end: int,
    b_index: np.ndarray,
    b_data: np.ndarray,
) -> list[MatchTask]:
    """Match one CSR row against one CSC column with two pointers."""

    tasks: list[MatchTask] = []
    a_ptr = a_base
    b_ptr = b_base
    c_addr = row_id * c_cols + col_id

    while a_ptr < a_end and b_ptr < b_end:
        a_idx = int(a_index[a_ptr])
        b_idx = int(b_index[b_ptr])
        if a_idx == b_idx:
            a_value = np.float16(a_data[a_ptr])
            b_value = np.float16(b_data[b_ptr])
            product_fp32 = np.float32(a_value) * np.float32(b_value)
            tasks.append(
                MatchTask(
                    row_id=row_id,
                    col_id=col_id,
                    k_index=a_idx,
                    a_offset=a_ptr - a_base,
                    b_offset=b_ptr - b_base,
                    a_data_addr=a_ptr,
                    b_data_addr=b_ptr,
                    c_addr=c_addr,
                    a_value=float(a_value),
                    b_value=float(b_value),
                    product_fp32=float(product_fp32),
                )
            )
            a_ptr += 1
            b_ptr += 1
        elif a_idx < b_idx:
            a_ptr += 1
        else:
            b_ptr += 1

    return tasks


def task_to_dict(task: MatchTask) -> dict[str, object]:
    return {
        "row_id": task.row_id,
        "col_id": task.col_id,
        "k_index": task.k_index,
        "a_offset": task.a_offset,
        "b_offset": task.b_offset,
        "a_data_addr": task.a_data_addr,
        "b_data_addr": task.b_data_addr,
        "c_addr": task.c_addr,
        "a_value": task.a_value,
        "b_value": task.b_value,
        "product_fp32": task.product_fp32,
    }
