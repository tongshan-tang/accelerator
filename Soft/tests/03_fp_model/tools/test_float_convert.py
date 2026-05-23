from pathlib import Path
import sys


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "03_fp_model"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from float_convert import convert_one


def test_convert_one_reports_known_one_bits():
    result = convert_one("1.0")

    assert result["fp16_value"] == 1.0
    assert result["fp16_bits"] == "0x3c00"
    assert result["fp32_value"] == 1.0
    assert result["fp32_bits"] == "0x3f800000"


def test_convert_one_rejects_invalid_input():
    try:
        convert_one("abc")
    except ValueError:
        return
    raise AssertionError("convert_one should reject invalid input")
