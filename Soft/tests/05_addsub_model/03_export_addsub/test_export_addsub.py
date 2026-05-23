from pathlib import Path
import sys

import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "05_addsub_model" / "03_export_addsub"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_ADD_SUB_ROOT = SOFT_ROOT / "src" / "05_addsub_model"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    SRC_ADD_SUB_ROOT / "01_sparse_pair_loader",
    SRC_ADD_SUB_ROOT / "02_dense_golden",
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import export_addsub
from case_generator import MatrixSpec, PairSpec, write_case


def test_export_demo_path_resolves_add_demo_name(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    demo_root = generated / "demo" / "addsub"
    write_case(
        "add1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+")],
        demo_root,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    monkeypatch.setattr(export_addsub, "generated_root", lambda: generated)

    paths = export_addsub.export_demo_path("add1", tmp_path / "addsub_out")

    assert sorted(path.name for path in paths) == [
        "add1_pair01_dense_golden.json",
        "add1_pair01_dense_golden.txt",
    ]
    assert all(path.parent == tmp_path / "addsub_out" / "demo" / "add1" for path in paths)


def test_export_demo_path_rejects_multiply_demo(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    demo_root = generated / "demo" / "mul"
    write_case(
        "mul1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "col"), "*")],
        demo_root,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    monkeypatch.setattr(export_addsub, "generated_root", lambda: generated)

    with pytest.raises(ValueError, match="multiplication demos are not handled by 05"):
        export_addsub.export_demo_path("mul1", tmp_path / "addsub_out")


def test_export_demo_path_rejects_case_name_for_now(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    case_root = generated / "case"
    write_case(
        "case1",
        [PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+")],
        case_root,
        seed=123,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    monkeypatch.setattr(export_addsub, "generated_root", lambda: generated)

    with pytest.raises(ValueError, match="case directories are not handled by 05 yet"):
        export_addsub.export_demo_path("case1", tmp_path / "addsub_out")
