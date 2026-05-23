from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_DIR = SOFT_ROOT / "src" / "02_sparse_format" / "02_value_generator"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from value_generator import fp16_bits, generate_fp16_value, generate_values_for_indices


def test_generate_fp16_value_is_stable_and_nonzero():
    first = generate_fp16_value("A_demo", 1, 3, 0, seed=7)
    second = generate_fp16_value("A_demo", 1, 3, 0, seed=7)

    assert isinstance(first, np.float16)
    assert first == second
    assert first != np.float16(0.0)


def test_generate_values_for_indices_matches_shape():
    values = generate_values_for_indices("A_demo", ((0, 2), (), (1,)), seed=7)

    assert len(values) == 3
    assert len(values[0]) == 2
    assert len(values[1]) == 0
    assert len(values[2]) == 1


def test_fp16_bits_for_one():
    assert fp16_bits(np.float16(1.0)) == "0x3c00"
