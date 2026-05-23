import json
from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "03_tb_runlist"
EXPORT_SRAM_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "02_export_sram"
CASE_DISPATCH_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "01_case_dispatch"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    EXPORT_SRAM_DIR,
    CASE_DISPATCH_DIR,
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import export_runlist
from case_generator import MatrixSpec, PairSpec, write_case


def test_export_tb_runlist_writes_runs_with_mem_paths(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    write_case(
        "case_test",
        [
            PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "col"), "*"),
            PairSpec(MatrixSpec(16, 16, "row"), MatrixSpec(16, 16, "row"), "+"),
        ],
        generated / "case",
        seed=123,
        expected_pair_count=2,
    )
    monkeypatch.setattr("case_dispatch.generated_root", lambda: generated)

    runlist_path = export_runlist.export_tb_runlist("case_test", tmp_path / "runlist_out")
    runlist = json.loads(runlist_path.read_text(encoding="utf-8"))

    assert runlist["case_name"] == "case_test"
    assert runlist["run_count"] == 2
    assert runlist["runs"][0]["run_id"] == 0
    assert runlist["runs"][0]["operation"] == "*"
    assert runlist["runs"][1]["operation"] == "+"
    assert runlist["runs"][0]["mem"]["A_ptr"]["path"].endswith("pair01/A_ptr.mem")
    assert Path(runlist["runs"][0]["mem"]["A_ptr"]["abs_path"]).exists()
    assert Path(runlist["runs"][1]["input_config"]["abs_path"]).exists()


def test_resolve_sram_manifest_accepts_manifest_path(tmp_path):
    case_dir = tmp_path / "case" / "case_test"
    case_dir.mkdir(parents=True)
    manifest = case_dir / "case_sram_manifest.json"
    manifest.write_text('{"case_name": "case_test"}\n', encoding="utf-8")

    assert export_runlist.resolve_sram_manifest(manifest) == manifest
