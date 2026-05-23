from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SRC_DIR = SOFT_ROOT / "src" / "03_fp_model" / "fp32_acc"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fp32_acc import finalize_output, fp16_bits, mac_fp32_acc, mul_fp16_to_fp32


def test_fp16_bits_for_one():
    assert fp16_bits(np.float16(1.0)) == "0x3c00"


def test_mul_uses_fp32_product_dtype():
    product = mul_fp16_to_fp32(np.float16(1.5), np.float16(2.0))

    assert isinstance(product, np.float32)
    assert product == np.float32(3.0)


def test_mac_accumulates_in_fp32():
    acc = mac_fp32_acc(
        [
            (np.float16(1.25), np.float16(2.0)),
            (np.float16(-0.5), np.float16(0.25)),
        ]
    )

    assert isinstance(acc, np.float32)
    assert acc == np.float32(2.375)


def test_finalize_output_to_fp16_or_fp32():
    value = np.float32(1.125)

    assert isinstance(finalize_output(value, "fp32"), np.float32)
    assert isinstance(finalize_output(value, "fp16"), np.float16)
