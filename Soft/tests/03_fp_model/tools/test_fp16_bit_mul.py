from pathlib import Path
import sys

import numpy as np


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "03_fp_model"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fp16_bit_mul import multiply_fp16_bits, parse_fp16_hex


def test_parse_fp16_hex_accepts_optional_prefix():
    assert parse_fp16_hex("0x3c00") == np.float16(1.0)
    assert parse_fp16_hex("4000") == np.float16(2.0)


def test_multiply_fp16_bits_reports_fp32_and_fp16_product():
    result = multiply_fp16_bits("3c00", "4000")

    assert result["a_value"] == 1.0
    assert result["b_value"] == 2.0
    assert result["product_fp32"] == 2.0
    assert result["product_fp16"] == 2.0
    assert result["product_fp16_bits"] == "0x4000"


def test_parse_fp16_hex_rejects_wrong_width():
    try:
        parse_fp16_hex("3c000")
    except ValueError:
        return
    raise AssertionError("parse_fp16_hex should reject non-16-bit input")
