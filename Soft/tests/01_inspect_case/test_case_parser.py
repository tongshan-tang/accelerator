from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOFT_ROOT.parent
SRC_DIR = SOFT_ROOT / "src" / "01_inspect_case"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from case_parser import parse_case_dir, parse_sparse_pair


def test_parse_official_case_pairs():
    matrices = parse_case_dir(REPO_ROOT / "CASE")

    assert {"A_0", "A_1", "A_2", "B_0", "B_1", "B_2"} <= set(matrices)
    assert matrices["A_0"].rows == 256
    assert matrices["A_0"].cols == 256
    assert matrices["B_0"].rows == 256
    assert matrices["B_0"].cols == 121
    assert matrices["B_1"].rows == 316
    assert matrices["B_1"].cols == 6


def test_weight_matches_index_count_for_a0():
    matrix = parse_sparse_pair(
        REPO_ROOT / "CASE" / "A_0_Matrix.txt",
        REPO_ROOT / "CASE" / "A_0_Index.txt",
        name="A_0",
        axis="row",
    )

    assert not [item for item in matrix.diagnostics if item.startswith("weight_mismatch")]
    assert matrix.nnz == sum(len(row) for row in matrix.indices)


def test_mixed_index_base_is_reported():
    matrix = parse_sparse_pair(
        REPO_ROOT / "CASE" / "A_0_Matrix.txt",
        REPO_ROOT / "CASE" / "A_0_Index.txt",
        name="A_0",
        axis="row",
    )

    assert any(item.startswith("index_base=invalid_or_mixed") for item in matrix.diagnostics)


def test_max_weight_ratio_uses_weight_axis_dimension():
    matrices = parse_case_dir(REPO_ROOT / "CASE")

    assert matrices["A_0"].max_weight_ratio == matrices["A_0"].max_weight / matrices["A_0"].cols
    assert matrices["B_1"].max_weight_ratio == matrices["B_1"].max_weight / matrices["B_1"].rows
    assert matrices["A_0"].max_line_density == matrices["A_0"].max_line_weight / matrices["A_0"].cols
    assert matrices["B_1"].max_line_density == matrices["B_1"].max_line_weight / matrices["B_1"].rows
    assert matrices["A_0"].empty_line_count == matrices["A_0"].empty_count
