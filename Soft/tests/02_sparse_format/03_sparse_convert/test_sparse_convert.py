from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
REPO_ROOT = SOFT_ROOT.parent
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
INSPECT_DIR = SOFT_ROOT / "src" / "01_inspect_case"
for path in (
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
    INSPECT_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_parser import parse_case_dir
from sparse_convert import convert_profile, normalize_indices, raw_from_profile, raw_to_csc, raw_to_csr


def test_normalize_indices_wraps_inner_dim_and_deduplicates():
    profile = parse_case_dir(REPO_ROOT / "CASE")["A_0"]

    indices, diagnostics = normalize_indices(profile)

    assert all(0 <= idx < profile.inner_size for line in indices for idx in line)
    assert all(tuple(sorted(set(line))) == line for line in indices)
    assert any(item.startswith("index_policy=") for item in diagnostics)
    assert any(item.startswith("deduplicated_indices") for item in diagnostics)


def test_raw_from_profile_generates_values():
    profile = parse_case_dir(REPO_ROOT / "CASE")["B_1"]
    raw = raw_from_profile(profile, seed=11)

    assert raw.values is not None
    assert raw.nnz == sum(len(line) for line in raw.indices)
    assert raw.nnz == sum(len(line) for line in raw.values)
    assert raw.max_line_density <= 0.3


def test_convert_a_profile_to_csr():
    profile = parse_case_dir(REPO_ROOT / "CASE")["A_1"]
    raw, packed = convert_profile(profile, seed=11)
    csr = raw_to_csr(raw)

    assert packed.name == "A_1"
    assert csr.row_ptr.size == csr.rows + 1
    assert csr.col_idx.size == csr.data.size == csr.nnz
    assert int(csr.row_ptr[-1]) == csr.nnz


def test_convert_b_profile_to_csc():
    profile = parse_case_dir(REPO_ROOT / "CASE")["B_1"]
    raw, packed = convert_profile(profile, seed=11)
    csc = raw_to_csc(raw)

    assert packed.name == "B_1"
    assert csc.col_ptr.size == csc.cols + 1
    assert csc.row_idx.size == csc.data.size == csc.nnz
    assert int(csc.col_ptr[-1]) == csc.nnz
