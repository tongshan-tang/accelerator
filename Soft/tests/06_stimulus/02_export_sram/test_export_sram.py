import json
from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "02_export_sram"
CASE_DISPATCH_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "01_case_dispatch"
CASE_GEN_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    CASE_DISPATCH_DIR,
    CASE_GEN_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import export_sram
from case_generator import MatrixSpec, PairSpec, write_case


def test_export_case_sram_writes_pair_mem_files(tmp_path, monkeypatch):
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

    manifest_path = export_sram.export_case_sram("case_test", tmp_path / "sram_out")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["case_name"] == "case_test"
    assert manifest["pair_count"] == 2
    pair01 = manifest_path.parent / "pair01"
    pair02 = manifest_path.parent / "pair02"
    for name in (
        "A_ptr.mem",
        "A_index.mem",
        "A_data.mem",
        "B_ptr.mem",
        "B_index.mem",
        "B_data.mem",
        "C_golden_fp16.mem",
        "input_config.json",
    ):
        assert (pair01 / name).exists()
        assert (pair02 / name).exists()

    config = json.loads((pair01 / "input_config.json").read_text(encoding="utf-8"))
    assert config["operation"] == "*"
    assert config["a"]["storage_format"] == "csr"
    assert config["b"]["storage_format"] == "csc"
    assert len((pair01 / "A_ptr.mem").read_text(encoding="utf-8").splitlines()) == config["a"]["ptr_len"]
    assert len((pair01 / "C_golden_fp16.mem").read_text(encoding="utf-8").splitlines()) == config["c"]["output_len"]


def test_hex_helpers_format_expected_widths():
    assert export_sram.hex_word(0x1FF, 16) == "01ff"
    assert export_sram.hex_word(0x3FFFF, 18) == "3ffff"
    assert export_sram.fp16_hex(1.0) == "3c00"
