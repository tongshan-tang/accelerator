from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "02_merge_matcher"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from merge_matcher import match_row_col


def test_match_row_col_finds_common_indices():
    tasks = match_row_col(
        row_id=2,
        col_id=3,
        c_cols=5,
        a_base=0,
        a_end=4,
        a_index=np.array([1, 3, 5, 9], dtype=np.int16),
        a_data=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float16),
        b_base=0,
        b_end=3,
        b_index=np.array([2, 5, 9], dtype=np.int16),
        b_data=np.array([10.0, 20.0, 30.0], dtype=np.float16),
    )

    assert [task.k_index for task in tasks] == [5, 9]
    assert [task.a_data_addr for task in tasks] == [2, 3]
    assert [task.b_data_addr for task in tasks] == [1, 2]
    assert tasks[0].c_addr == 13


def test_match_row_col_returns_empty_without_intersection():
    tasks = match_row_col(
        row_id=0,
        col_id=0,
        c_cols=1,
        a_base=0,
        a_end=2,
        a_index=np.array([1, 3], dtype=np.int16),
        a_data=np.array([1.0, 2.0], dtype=np.float16),
        b_base=0,
        b_end=2,
        b_index=np.array([2, 4], dtype=np.int16),
        b_data=np.array([3.0, 4.0], dtype=np.float16),
    )

    assert tasks == []
