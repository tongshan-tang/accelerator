"""Sparse matrix data types used by the hardware-aligned model flow.

This module is intentionally small and dependency-light.  Later steps convert
the official parsed CASE structures into these normalized types before building
golden FP16 arithmetic models or RTL memory images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

import numpy as np


Axis = Literal["row", "col"]


@dataclass(frozen=True)
class SparseMatrixRaw:
    """Sparse structure plus optional generated values before CSR/CSC packing."""

    name: str
    rows: int
    cols: int
    axis: Axis
    indices: tuple[tuple[int, ...], ...]
    values: tuple[tuple[np.float16, ...], ...] | None = None
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.rows <= 0:
            raise ValueError(f"{self.name}: rows must be positive")
        if self.cols <= 0:
            raise ValueError(f"{self.name}: cols must be positive")

        expected_outer = self.rows if self.axis == "row" else self.cols
        if len(self.indices) != expected_outer:
            raise ValueError(
                f"{self.name}: expected {expected_outer} index records for axis={self.axis}, "
                f"got {len(self.indices)}"
            )

        if self.values is not None and len(self.values) != len(self.indices):
            raise ValueError(
                f"{self.name}: values record count {len(self.values)} does not match "
                f"indices record count {len(self.indices)}"
            )

        inner_size = self.cols if self.axis == "row" else self.rows
        for record_id, record in enumerate(self.indices):
            _check_sorted_unique(self.name, record_id, record)
            _check_index_bounds(self.name, record_id, record, inner_size)
            if self.values is not None and len(self.values[record_id]) != len(record):
                raise ValueError(
                    f"{self.name}: values[{record_id}] length {len(self.values[record_id])} "
                    f"does not match indices length {len(record)}"
                )

    @property
    def nnz(self) -> int:
        return sum(len(record) for record in self.indices)

    @property
    def outer_size(self) -> int:
        return self.rows if self.axis == "row" else self.cols

    @property
    def inner_size(self) -> int:
        return self.cols if self.axis == "row" else self.rows

    @property
    def density(self) -> float:
        return self.nnz / (self.rows * self.cols)

    @property
    def max_line_weight(self) -> int:
        return max((len(record) for record in self.indices), default=0)

    @property
    def max_line_density(self) -> float:
        return self.max_line_weight / self.inner_size

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "format": "raw",
            "axis": self.axis,
            "rows": self.rows,
            "cols": self.cols,
            "nnz": self.nnz,
            "density": self.density,
            "max_line_weight": self.max_line_weight,
            "max_line_density": self.max_line_density,
            "has_values": self.values is not None,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class CSRMatrix:
    """Compressed sparse row matrix used for A in matrix multiplication."""

    name: str
    rows: int
    cols: int
    row_ptr: np.ndarray
    col_idx: np.ndarray
    data: np.ndarray
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _check_common_shape(self.name, self.rows, self.cols)
        _check_ptr_array(self.name, "row_ptr", self.row_ptr, self.rows + 1)
        _check_index_data_lengths(self.name, self.col_idx, self.data, int(self.row_ptr[-1]))
        _check_packed_index_bounds(self.name, "col_idx", self.col_idx, self.cols)
        _check_segment_sorted_unique(self.name, self.row_ptr, self.col_idx)

    @property
    def nnz(self) -> int:
        return int(self.row_ptr[-1])

    @property
    def density(self) -> float:
        return self.nnz / (self.rows * self.cols)

    @property
    def max_line_weight(self) -> int:
        if self.row_ptr.size <= 1:
            return 0
        return int(np.max(self.row_ptr[1:] - self.row_ptr[:-1]))

    @property
    def max_line_density(self) -> float:
        return self.max_line_weight / self.cols

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "format": "csr",
            "rows": self.rows,
            "cols": self.cols,
            "nnz": self.nnz,
            "density": self.density,
            "max_line_weight": self.max_line_weight,
            "max_line_density": self.max_line_density,
            "ptr_len": int(self.row_ptr.size),
            "idx_len": int(self.col_idx.size),
            "data_len": int(self.data.size),
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class CSCMatrix:
    """Compressed sparse column matrix used for B in matrix multiplication."""

    name: str
    rows: int
    cols: int
    col_ptr: np.ndarray
    row_idx: np.ndarray
    data: np.ndarray
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _check_common_shape(self.name, self.rows, self.cols)
        _check_ptr_array(self.name, "col_ptr", self.col_ptr, self.cols + 1)
        _check_index_data_lengths(self.name, self.row_idx, self.data, int(self.col_ptr[-1]))
        _check_packed_index_bounds(self.name, "row_idx", self.row_idx, self.rows)
        _check_segment_sorted_unique(self.name, self.col_ptr, self.row_idx)

    @property
    def nnz(self) -> int:
        return int(self.col_ptr[-1])

    @property
    def density(self) -> float:
        return self.nnz / (self.rows * self.cols)

    @property
    def max_line_weight(self) -> int:
        if self.col_ptr.size <= 1:
            return 0
        return int(np.max(self.col_ptr[1:] - self.col_ptr[:-1]))

    @property
    def max_line_density(self) -> float:
        return self.max_line_weight / self.rows

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "format": "csc",
            "rows": self.rows,
            "cols": self.cols,
            "nnz": self.nnz,
            "density": self.density,
            "max_line_weight": self.max_line_weight,
            "max_line_density": self.max_line_density,
            "ptr_len": int(self.col_ptr.size),
            "idx_len": int(self.row_idx.size),
            "data_len": int(self.data.size),
            "diagnostics": list(self.diagnostics),
        }


def _check_common_shape(name: str, rows: int, cols: int) -> None:
    if rows <= 0:
        raise ValueError(f"{name}: rows must be positive")
    if cols <= 0:
        raise ValueError(f"{name}: cols must be positive")


def _check_ptr_array(name: str, field_name: str, ptr: np.ndarray, expected_len: int) -> None:
    if ptr.ndim != 1:
        raise ValueError(f"{name}: {field_name} must be 1-D")
    if ptr.size != expected_len:
        raise ValueError(f"{name}: {field_name} length must be {expected_len}, got {ptr.size}")
    if ptr.size == 0 or int(ptr[0]) != 0:
        raise ValueError(f"{name}: {field_name}[0] must be 0")
    if np.any(ptr < 0):
        raise ValueError(f"{name}: {field_name} contains negative offsets")
    if np.any(ptr[:-1] > ptr[1:]):
        raise ValueError(f"{name}: {field_name} must be monotonically non-decreasing")


def _check_index_data_lengths(
    name: str,
    idx: np.ndarray,
    data: np.ndarray,
    expected_nnz: int,
) -> None:
    if idx.ndim != 1:
        raise ValueError(f"{name}: index array must be 1-D")
    if data.ndim != 1:
        raise ValueError(f"{name}: data array must be 1-D")
    if idx.size != expected_nnz:
        raise ValueError(f"{name}: index length {idx.size} does not match nnz {expected_nnz}")
    if data.size != expected_nnz:
        raise ValueError(f"{name}: data length {data.size} does not match nnz {expected_nnz}")


def _check_packed_index_bounds(
    name: str,
    field_name: str,
    idx: np.ndarray,
    limit: int,
) -> None:
    if idx.size == 0:
        return
    min_idx = int(np.min(idx))
    max_idx = int(np.max(idx))
    if min_idx < 0 or max_idx >= limit:
        raise ValueError(
            f"{name}: {field_name} out of bounds, min={min_idx} max={max_idx} limit={limit}"
        )


def _check_segment_sorted_unique(name: str, ptr: np.ndarray, idx: np.ndarray) -> None:
    for segment_id in range(ptr.size - 1):
        start = int(ptr[segment_id])
        end = int(ptr[segment_id + 1])
        _check_sorted_unique(name, segment_id, idx[start:end])


def _check_sorted_unique(
    name: str,
    record_id: int,
    record: Sequence[int] | np.ndarray,
) -> None:
    for pos in range(len(record) - 1):
        if int(record[pos]) >= int(record[pos + 1]):
            raise ValueError(
                f"{name}: record {record_id} indices must be strictly increasing"
            )


def _check_index_bounds(
    name: str,
    record_id: int,
    record: Sequence[int],
    limit: int,
) -> None:
    for idx in record:
        if idx < 0 or idx >= limit:
            raise ValueError(
                f"{name}: record {record_id} index {idx} out of bounds for limit {limit}"
            )
