from pathlib import Path
import sys

import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_ADD_SUB_DIR = SOFT_ROOT / "src" / "05_addsub_model" / "01_sparse_pair_loader"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SRC_ADD_SUB_DIR,
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from addsub_pair_loader import load_addsub_pair
from case_generator import MatrixSpec, PairSpec, write_case


def test_load_addsub_pair_accepts_plus_and_csr_b(tmp_path):
    demo_dir = write_case(
        "add1",
        [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "row"), "+")],
        tmp_path,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    pair = load_addsub_pair(demo_dir / "add1_pair01.json")

    assert pair.operation == "+"
    assert pair.a.storage_format == "csr"
    assert pair.b.storage_format == "csr"
    assert pair.a.rows == pair.b.rows == 16
    assert pair.a.cols == pair.b.cols == 32


def test_load_addsub_pair_rejects_multiply_pair(tmp_path):
    demo_dir = write_case(
        "mul1",
        [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")],
        tmp_path,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    with pytest.raises(ValueError, match="not add/sub"):
        load_addsub_pair(demo_dir / "mul1_pair01.json")
