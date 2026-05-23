from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_ADD_SUB_ROOT = SOFT_ROOT / "src" / "05_addsub_model"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SRC_ADD_SUB_ROOT / "01_sparse_pair_loader",
    SRC_ADD_SUB_ROOT / "02_dense_golden",
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_generator import MatrixSpec, PairSpec, write_case
from dense_addsub import addsub_from_generated_pair, csr_to_dense_fp16, write_result
from addsub_pair_loader import load_addsub_pair


def test_addsub_from_generated_plus_pair_runs(tmp_path):
    demo_dir = write_case(
        "add1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+")],
        tmp_path,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    result = addsub_from_generated_pair(demo_dir / "add1_pair01.json")

    assert result["summary"]["mode"] == "fp16_addsub"
    assert result["summary"]["operation"] == "+"
    assert result["summary"]["c_rows"] == 16
    assert result["summary"]["c_cols"] == 16
    assert len(result["c_dense_fp16"]) == 16
    assert len(result["c_dense_bits"]) == 16


def test_addsub_subtract_matches_fp16_dense_math(tmp_path):
    demo_dir = write_case(
        "sub1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "-")],
        tmp_path,
        seed=456,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    pair_path = demo_dir / "sub1_pair01.json"
    pair = load_addsub_pair(pair_path)
    a_dense = csr_to_dense_fp16(pair.a)
    b_dense = csr_to_dense_fp16(pair.b)
    expected = np.float16(a_dense - b_dense)

    result = addsub_from_generated_pair(pair_path)

    assert result["c_dense_fp16"] == [[float(x) for x in row] for row in expected]


def test_write_result_writes_json_and_text(tmp_path):
    demo_dir = write_case(
        "add1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+")],
        tmp_path,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    result = addsub_from_generated_pair(demo_dir / "add1_pair01.json")

    json_path, text_path = write_result(result, tmp_path / "out", "add1_pair01")

    assert json_path.exists()
    assert text_path.exists()
    assert "fp16_addsub" in text_path.read_text(encoding="utf-8")
