from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "01_sparse_array_loader"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sparse_array_loader import load_pair, load_sparse_arrays

SPARSE_OUT = SOFT_ROOT / "output" / "02_sparse_format" / "04_export_sparse_arrays"


def test_load_sparse_arrays_from_official_export():
    matrix = load_sparse_arrays(SPARSE_OUT / "A_1_sparse_arrays.json")

    assert matrix.name == "A_1"
    assert matrix.storage_format == "csr"
    assert matrix.ptr.size == matrix.rows + 1
    assert matrix.index.size == matrix.data.size == matrix.nnz


def test_load_pair_validates_shapes():
    a, b = load_pair(SPARSE_OUT / "A_1_sparse_arrays.json", SPARSE_OUT / "B_1_sparse_arrays.json")

    assert a.cols == b.rows
    assert a.storage_format == "csr"
    assert b.storage_format == "csc"
