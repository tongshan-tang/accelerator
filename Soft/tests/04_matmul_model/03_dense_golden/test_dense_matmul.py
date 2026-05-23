from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_MATMUL_ROOT = SOFT_ROOT / "src" / "04_matmul_model"
for path in (
    SRC_MATMUL_ROOT / "01_sparse_array_loader",
    SRC_MATMUL_ROOT / "02_merge_matcher",
    SRC_MATMUL_ROOT / "03_dense_golden",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dense_matmul import matmul_sparse_fp32_acc
from sparse_array_loader import SparseArrays


def test_matmul_sparse_fp32_acc_small_case():
    a = SparseArrays(
        name="A",
        storage_format="csr",
        rows=2,
        cols=3,
        ptr=np.array([0, 2, 3], dtype=np.int32),
        index=np.array([0, 2, 1], dtype=np.int16),
        data=np.array([1.0, 2.0, 3.0], dtype=np.float16),
        diagnostics=(),
    )
    b = SparseArrays(
        name="B",
        storage_format="csc",
        rows=3,
        cols=2,
        ptr=np.array([0, 2, 3], dtype=np.int32),
        index=np.array([0, 2, 1], dtype=np.int16),
        data=np.array([4.0, 5.0, 6.0], dtype=np.float16),
        diagnostics=(),
    )

    result = matmul_sparse_fp32_acc(a, b)

    assert result["c_dense_fp32"] == [[14.0, 0.0], [0.0, 18.0]]
    assert result["summary"]["task_count"] == 3
    assert result["per_cell_task_count"] == [[2, 0], [0, 1]]
