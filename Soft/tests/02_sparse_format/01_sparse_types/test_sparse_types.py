from pathlib import Path
import sys

import numpy as np
import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_DIR = SOFT_ROOT / "src" / "02_sparse_format" / "01_sparse_types"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sparse_types import CSCMatrix, CSRMatrix, SparseMatrixRaw


def test_raw_matrix_summary_without_values():
    matrix = SparseMatrixRaw(
        name="A_demo",
        rows=2,
        cols=4,
        axis="row",
        indices=((0, 3), (1,)),
    )

    assert matrix.nnz == 3
    assert matrix.outer_size == 2
    assert matrix.inner_size == 4
    assert matrix.max_line_weight == 2
    assert matrix.max_line_density == 0.5
    assert matrix.summary()["has_values"] is False


def test_csr_matrix_accepts_valid_packed_arrays():
    matrix = CSRMatrix(
        name="A_csr",
        rows=2,
        cols=4,
        row_ptr=np.array([0, 2, 3], dtype=np.int32),
        col_idx=np.array([0, 3, 1], dtype=np.int16),
        data=np.array([1.0, 2.0, 3.0], dtype=np.float16),
    )

    assert matrix.nnz == 3
    assert matrix.max_line_weight == 2
    assert matrix.max_line_density == 0.5
    assert matrix.summary()["format"] == "csr"


def test_csc_matrix_accepts_valid_packed_arrays():
    matrix = CSCMatrix(
        name="B_csc",
        rows=4,
        cols=2,
        col_ptr=np.array([0, 2, 3], dtype=np.int32),
        row_idx=np.array([0, 3, 1], dtype=np.int16),
        data=np.array([1.0, 2.0, 3.0], dtype=np.float16),
    )

    assert matrix.nnz == 3
    assert matrix.max_line_weight == 2
    assert matrix.max_line_density == 0.5
    assert matrix.summary()["format"] == "csc"


def test_raw_rejects_unsorted_or_duplicate_indices():
    with pytest.raises(ValueError, match="strictly increasing"):
        SparseMatrixRaw(
            name="bad",
            rows=1,
            cols=4,
            axis="row",
            indices=((1, 1),),
        )


def test_csr_rejects_bad_ptr_length():
    with pytest.raises(ValueError, match="row_ptr length"):
        CSRMatrix(
            name="bad_csr",
            rows=2,
            cols=4,
            row_ptr=np.array([0, 1], dtype=np.int32),
            col_idx=np.array([0], dtype=np.int16),
            data=np.array([1.0], dtype=np.float16),
        )


def test_csc_rejects_index_out_of_bounds():
    with pytest.raises(ValueError, match="out of bounds"):
        CSCMatrix(
            name="bad_csc",
            rows=4,
            cols=1,
            col_ptr=np.array([0, 1], dtype=np.int32),
            row_idx=np.array([4], dtype=np.int16),
            data=np.array([1.0], dtype=np.float16),
        )
