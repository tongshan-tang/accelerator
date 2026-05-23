import json
from pathlib import Path
import sys

import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "01_case_dispatch"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import case_dispatch
from case_generator import MatrixSpec, PairSpec, write_case


def test_build_case_bundle_dispatches_mul_add_sub(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    case_root = generated / "case"
    write_case(
        "case_test",
        [
            PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "col"), "*"),
            PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+"),
            PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "-"),
        ],
        case_root,
        seed=123,
        expected_pair_count=3,
    )
    monkeypatch.setattr(case_dispatch, "generated_root", lambda: generated)

    manifest_path = case_dispatch.build_case_bundle("case_test", tmp_path / "bundle_out")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["case_name"] == "case_test"
    assert manifest["pair_count"] == 3
    assert [item["operation"] for item in manifest["pairs"]] == ["*", "+", "-"]
    assert [item["output_kind"] for item in manifest["pairs"]] == ["matmul", "addsub", "addsub"]
    assert (manifest_path.parent / "pair01" / "case_test_pair01_dense_golden.json").exists()
    assert (manifest_path.parent / "pair01" / "case_test_pair01_task_trace.json").exists()
    assert (manifest_path.parent / "pair02" / "case_test_pair02_dense_golden.json").exists()
    assert (manifest_path.parent / "pair03" / "case_test_pair03_dense_golden.json").exists()


def test_resolve_case_path_rejects_demo_name(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    (generated / "demo" / "mul" / "mul1").mkdir(parents=True)
    monkeypatch.setattr(case_dispatch, "generated_root", lambda: generated)

    with pytest.raises(ValueError, match="not found"):
        case_dispatch.resolve_case_path("mul1")
