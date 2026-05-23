"""Load CSR/CSC sparse array JSON files produced by 02_sparse_format."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np


StorageFormat = Literal["csr", "csc"]


@dataclass(frozen=True)
class SparseArrays:
    name: str
    storage_format: StorageFormat
    rows: int
    cols: int
    ptr: np.ndarray
    index: np.ndarray
    data: np.ndarray
    diagnostics: tuple[str, ...]

    @property
    def nnz(self) -> int:
        return int(self.ptr[-1])

    def line_range(self, line_id: int) -> tuple[int, int]:
        return int(self.ptr[line_id]), int(self.ptr[line_id + 1])


def sparse_arrays_from_payload(payload: dict[str, object], *, source: str) -> SparseArrays:
    """Build one sparse array object from an exported JSON payload."""

    matrix = payload["matrix"]
    arrays = payload["arrays"]
    assert isinstance(matrix, dict)
    assert isinstance(arrays, dict)
    storage_format = matrix["storage_format"]
    if storage_format not in ("csr", "csc"):
        raise ValueError(f"{source}: unsupported storage_format {storage_format}")

    ptr = np.array(arrays["ptr"], dtype=np.int32)
    index = np.array(arrays["index"], dtype=np.int16)
    data = np.array(arrays["data_fp16"], dtype=np.float16)
    expected_ptr_len = matrix["rows"] + 1 if storage_format == "csr" else matrix["cols"] + 1
    if ptr.size != expected_ptr_len:
        raise ValueError(f"{source}: ptr length {ptr.size} does not match expected {expected_ptr_len}")
    if index.size != data.size:
        raise ValueError(f"{source}: index length {index.size} does not match data length {data.size}")
    if int(ptr[-1]) != index.size:
        raise ValueError(f"{source}: ptr[-1] {int(ptr[-1])} does not match nnz {index.size}")

    return SparseArrays(
        name=matrix["name"],
        storage_format=storage_format,
        rows=int(matrix["rows"]),
        cols=int(matrix["cols"]),
        ptr=ptr,
        index=index,
        data=data,
        diagnostics=tuple(matrix.get("diagnostics", ())),
    )


def load_sparse_arrays(path: Path | str) -> SparseArrays:
    """Load one sparse array JSON payload."""

    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return sparse_arrays_from_payload(payload, source=str(path))


def load_pair(a_path: Path | str, b_path: Path | str) -> tuple[SparseArrays, SparseArrays]:
    """Load and validate a CSR/CSC matrix pair for multiplication."""

    a = load_sparse_arrays(a_path)
    b = load_sparse_arrays(b_path)
    return validate_pair(a, b)


def validate_pair(a: SparseArrays, b: SparseArrays) -> tuple[SparseArrays, SparseArrays]:
    """Validate a CSR/CSC matrix pair for multiplication."""

    if a.storage_format != "csr":
        raise ValueError(f"{a.name}: A matrix must use csr, got {a.storage_format}")
    if b.storage_format != "csc":
        raise ValueError(f"{b.name}: B matrix must use csc, got {b.storage_format}")
    if a.cols != b.rows:
        raise ValueError(f"shape mismatch: A is {a.rows}x{a.cols}, B is {b.rows}x{b.cols}")
    return a, b
