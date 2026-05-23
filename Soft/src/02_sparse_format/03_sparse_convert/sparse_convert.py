"""Convert CASE matrix profiles into normalized raw, CSR, and CSC structures."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import numpy as np

STEP_DIR = Path(__file__).resolve().parent
SPARSE_ROOT = STEP_DIR.parent
SOFT_ROOT = STEP_DIR.parents[2]
INSPECT_DIR = SOFT_ROOT / "src" / "01_inspect_case"
for path in (
    SPARSE_ROOT / "01_sparse_types",
    SPARSE_ROOT / "02_value_generator",
    INSPECT_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_parser import CaseMatrixProfile
from sparse_types import CSCMatrix, CSRMatrix, SparseMatrixRaw
from value_generator import DEFAULT_VALUE_SEED, generate_values_for_indices


IndexPolicy = Literal["strict_zero_based", "wrap_inner_dim_to_zero_dedup"]


def normalize_indices(
    profile: CaseMatrixProfile,
    *,
    index_policy: IndexPolicy = "wrap_inner_dim_to_zero_dedup",
) -> tuple[tuple[tuple[int, ...], ...], tuple[str, ...]]:
    """Normalize CASE indices into zero-based, strictly increasing records."""

    diagnostics: list[str] = []
    normalized_records: list[tuple[int, ...]] = []
    wrapped_count = 0
    duplicate_drop_count = 0

    for line_id, record in enumerate(profile.line_indices):
        normalized_line: list[int] = []
        for idx in record:
            if 0 <= idx < profile.inner_size:
                normalized_line.append(idx)
            elif idx == profile.inner_size and index_policy == "wrap_inner_dim_to_zero_dedup":
                normalized_line.append(0)
                wrapped_count += 1
            else:
                raise ValueError(
                    f"{profile.name}: line {line_id} index {idx} cannot be normalized "
                    f"with policy={index_policy}"
                )

        unique_sorted = tuple(sorted(set(normalized_line)))
        duplicate_drop_count += len(normalized_line) - len(unique_sorted)
        normalized_records.append(unique_sorted)

    if wrapped_count:
        diagnostics.append(f"index_policy={index_policy}: wrapped_inner_dim_to_zero={wrapped_count}")
    else:
        diagnostics.append(f"index_policy={index_policy}")
    if duplicate_drop_count:
        diagnostics.append(f"deduplicated_indices_after_normalization={duplicate_drop_count}")

    return tuple(normalized_records), tuple(diagnostics)


def raw_from_profile(
    profile: CaseMatrixProfile,
    *,
    seed: int = DEFAULT_VALUE_SEED,
    index_policy: IndexPolicy = "wrap_inner_dim_to_zero_dedup",
) -> SparseMatrixRaw:
    """Create normalized sparse raw data with deterministic FP16 values."""

    if profile.axis not in ("row", "col"):
        raise ValueError(f"{profile.name}: unsupported axis {profile.axis}")
    indices, normalize_diagnostics = normalize_indices(profile, index_policy=index_policy)
    values = generate_values_for_indices(profile.name, indices, seed=seed)
    return SparseMatrixRaw(
        name=profile.name,
        rows=profile.rows,
        cols=profile.cols,
        axis=profile.axis,
        indices=indices,
        values=values,
        diagnostics=tuple(profile.diagnostics) + normalize_diagnostics,
    )


def raw_to_csr(raw: SparseMatrixRaw) -> CSRMatrix:
    """Convert row-oriented raw sparse data into CSR."""

    if raw.axis != "row":
        raise ValueError(f"{raw.name}: CSR conversion requires axis=row")
    if raw.values is None:
        raise ValueError(f"{raw.name}: CSR conversion requires values")

    row_ptr = [0]
    col_idx: list[int] = []
    data: list[np.float16] = []
    for indices, values in zip(raw.indices, raw.values):
        col_idx.extend(indices)
        data.extend(values)
        row_ptr.append(len(col_idx))

    return CSRMatrix(
        name=raw.name,
        rows=raw.rows,
        cols=raw.cols,
        row_ptr=np.array(row_ptr, dtype=np.int32),
        col_idx=np.array(col_idx, dtype=np.int16),
        data=np.array(data, dtype=np.float16),
        diagnostics=raw.diagnostics,
    )


def raw_to_csc(raw: SparseMatrixRaw) -> CSCMatrix:
    """Convert column-oriented raw sparse data into CSC."""

    if raw.axis != "col":
        raise ValueError(f"{raw.name}: CSC conversion requires axis=col")
    if raw.values is None:
        raise ValueError(f"{raw.name}: CSC conversion requires values")

    col_ptr = [0]
    row_idx: list[int] = []
    data: list[np.float16] = []
    for indices, values in zip(raw.indices, raw.values):
        row_idx.extend(indices)
        data.extend(values)
        col_ptr.append(len(row_idx))

    return CSCMatrix(
        name=raw.name,
        rows=raw.rows,
        cols=raw.cols,
        col_ptr=np.array(col_ptr, dtype=np.int32),
        row_idx=np.array(row_idx, dtype=np.int16),
        data=np.array(data, dtype=np.float16),
        diagnostics=raw.diagnostics,
    )


def convert_profile(
    profile: CaseMatrixProfile,
    *,
    seed: int = DEFAULT_VALUE_SEED,
    index_policy: IndexPolicy = "wrap_inner_dim_to_zero_dedup",
) -> tuple[SparseMatrixRaw, CSRMatrix | CSCMatrix]:
    """Normalize one CASE profile and convert it to the matching packed format."""

    raw = raw_from_profile(profile, seed=seed, index_policy=index_policy)
    if raw.axis == "row":
        return raw, raw_to_csr(raw)
    return raw, raw_to_csc(raw)
