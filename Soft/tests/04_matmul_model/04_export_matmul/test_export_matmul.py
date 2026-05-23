from pathlib import Path
import sys

import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "04_matmul_model"
SRC_MATMUL_ROOT = SOFT_ROOT / "src" / "04_matmul_model"
CASE_GENERATOR_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    SRC_MATMUL_ROOT / "01_sparse_array_loader",
    SRC_MATMUL_ROOT / "02_merge_matcher",
    SRC_MATMUL_ROOT / "03_dense_golden",
    CASE_GENERATOR_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import export_matmul
from case_generator import MatrixSpec, PairSpec, write_case
from dense_matmul import matmul_from_files, matmul_from_generated_pair

SPARSE_OUT = SOFT_ROOT / "output" / "02_sparse_format" / "04_export_sparse_arrays"


def test_matmul_from_official_a1_b1_runs():
    result = matmul_from_files(
        SPARSE_OUT / "A_1_sparse_arrays.json",
        SPARSE_OUT / "B_1_sparse_arrays.json",
    )

    assert result["summary"]["a_name"] == "A_1"
    assert result["summary"]["b_name"] == "B_1"
    assert result["summary"]["c_rows"] == 32
    assert result["summary"]["c_cols"] == 6
    assert result["summary"]["task_count"] > 0


def test_matmul_from_generated_pair_runs(tmp_path):
    demo_dir = write_case(
        "mul1",
        [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")],
        tmp_path,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    result = matmul_from_generated_pair(demo_dir / "mul1_pair01.json")

    assert result["summary"]["source_case_name"] == "mul1"
    assert result["summary"]["source_pair_id"] == 1
    assert result["summary"]["c_rows"] == 16
    assert result["summary"]["c_cols"] == 16


def test_export_generated_path_resolves_demo_name(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    demo_root = generated / "demo" / "mul"
    write_case(
        "mul1",
        [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")],
        demo_root,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    monkeypatch.setattr(export_matmul, "generated_root", lambda: generated)

    paths = export_matmul.export_generated_path("mul1", tmp_path / "matmul_out")

    assert sorted(path.name for path in paths) == [
        "mul1_pair01_dense_golden.json",
        "mul1_pair01_task_trace.json",
    ]
    assert all(path.parent == tmp_path / "matmul_out" / "demo" / "mul" / "mul1" for path in paths)


def test_export_generated_path_rejects_addsub_demo(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    addsub_root = generated / "demo" / "addsub"
    write_case(
        "add1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+")],
        addsub_root,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    monkeypatch.setattr(export_matmul, "generated_root", lambda: generated)

    with pytest.raises(ValueError, match="add/sub demos are not handled by 04"):
        export_matmul.export_generated_path("add1", tmp_path / "matmul_out")


def test_export_generated_path_rejects_case_name_for_now(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    case_root = generated / "case"
    write_case(
        "casex",
        [
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*"),
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "row"), "+"),
        ],
        case_root,
        seed=123,
        expected_pair_count=2,
    )
    monkeypatch.setattr(export_matmul, "generated_root", lambda: generated)

    try:
        export_matmul.export_generated_path("casex", tmp_path / "matmul_out")
    except ValueError as exc:
        assert "case directories are not handled by 04 yet" in str(exc)
        return
    raise AssertionError("case path should be rejected until add/sub model is ready")
