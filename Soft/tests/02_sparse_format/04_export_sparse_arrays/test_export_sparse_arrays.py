from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
REPO_ROOT = SOFT_ROOT.parent
SCRIPT_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "04_export_sparse_arrays"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
INSPECT_DIR = SOFT_ROOT / "src" / "01_inspect_case"
for path in (
    SCRIPT_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
    INSPECT_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from export_sparse_arrays import build_exports, packed_to_export
from sparse_convert import convert_profile


def test_build_exports_for_official_case_dir():
    exports = build_exports(REPO_ROOT / "CASE", seed=13)

    assert {"A_0", "A_1", "A_2", "B_0", "B_1", "B_2"} <= set(exports)
    assert exports["A_0"]["matrix"]["storage_format"] == "csr"
    assert exports["B_0"]["matrix"]["storage_format"] == "csc"
    assert len(exports["A_0"]["arrays"]["ptr"]) == exports["A_0"]["matrix"]["rows"] + 1
    assert len(exports["B_0"]["arrays"]["ptr"]) == exports["B_0"]["matrix"]["cols"] + 1


def test_packed_export_has_data_bits():
    from case_parser import parse_case_dir

    _raw, packed = convert_profile(parse_case_dir(REPO_ROOT / "CASE")["B_1"], seed=13)
    payload = packed_to_export(packed)

    assert len(payload["arrays"]["data_bits"]) == payload["matrix"]["data_len"]
    assert all(str(item).startswith("0x") for item in payload["arrays"]["data_bits"])
