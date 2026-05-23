from pathlib import Path
import sys

import numpy as np
import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "05_addsub_model" / "tools"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fp16_bit_addsub import addsub_fp16_bits, parse_fp16_hex, parse_repl_parts


def test_parse_fp16_hex_accepts_optional_prefix():
    assert parse_fp16_hex("0x3c00") == np.float16(1.0)
    assert parse_fp16_hex("4000") == np.float16(2.0)


def test_addsub_fp16_bits_adds_and_subtracts():
    add = addsub_fp16_bits("3c00", "+", "4000")
    sub = addsub_fp16_bits("4000", "-", "3c00")

    assert add["result_fp16"] == 3.0
    assert add["result_fp16_bits"] == "0x4200"
    assert sub["result_fp16"] == 1.0
    assert sub["result_fp16_bits"] == "0x3c00"


def test_addsub_fp16_bits_uses_fp16_rounding():
    result = addsub_fp16_bits("3c00", "+", "1000")

    assert result["a_value"] == 1.0
    assert result["b_value"] == float(np.array(0x1000, dtype=np.uint16).view(np.float16))
    assert result["result_fp16_bits"] == "0x3c00"


def test_parse_repl_parts_accepts_operator_middle_or_end():
    assert parse_repl_parts("3c00 + 4000") == ("3c00", "+", "4000")
    assert parse_repl_parts("3c00 4000 +") == ("3c00", "+", "4000")


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError, match="4 hex digits"):
        parse_fp16_hex("3c000")
    with pytest.raises(ValueError, match="operation"):
        addsub_fp16_bits("3c00", "*", "4000")
