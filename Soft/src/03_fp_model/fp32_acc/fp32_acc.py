#!/usr/bin/env python3
"""FP16 input with FP32 accumulation reference model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


SOFT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = SOFT_ROOT / "output" / "03_fp_model" / "fp32_acc"


def to_fp16(value: float | np.float16) -> np.float16:
    """Convert one scalar to FP16."""

    return np.float16(value)


def fp16_bits(value: float | np.float16) -> str:
    """Return the IEEE-754 binary16 bit pattern as four hex digits."""

    fp16_value = np.float16(value)
    bits = fp16_value.view(np.uint16)
    return f"0x{int(bits):04x}"


def mul_fp16_to_fp32(a: float | np.float16, b: float | np.float16) -> np.float32:
    """Multiply FP16 inputs and keep the product in FP32."""

    a_fp16 = np.float16(a)
    b_fp16 = np.float16(b)
    return np.float32(a_fp16) * np.float32(b_fp16)


def mac_fp32_acc(
    pairs: list[tuple[float | np.float16, float | np.float16]],
    *,
    initial: float | np.float32 = np.float32(0.0),
) -> np.float32:
    """Accumulate FP16 input products into an FP32 accumulator."""

    acc = np.float32(initial)
    for a, b in pairs:
        acc = np.float32(acc + mul_fp16_to_fp32(a, b))
    return acc


def finalize_output(value: float | np.float32, output_dtype: str = "fp16") -> np.float16 | np.float32:
    """Finalize an accumulator value to the requested output dtype."""

    if output_dtype == "fp32":
        return np.float32(value)
    if output_dtype == "fp16":
        return np.float16(value)
    raise ValueError(f"unsupported output_dtype: {output_dtype}")


def build_samples() -> dict[str, object]:
    pairs = [
        (np.float16(1.25), np.float16(-0.5)),
        (np.float16(0.875), np.float16(2.0)),
        (np.float16(-1.5), np.float16(0.125)),
        (np.float16(3.25), np.float16(-0.25)),
        (np.float16(0.0625), np.float16(0.5)),
    ]
    products = [mul_fp16_to_fp32(a, b) for a, b in pairs]
    acc_fp32 = mac_fp32_acc(pairs)
    out_fp16 = finalize_output(acc_fp32, "fp16")

    return {
        "mode": "fp32_acc",
        "rule": "FP16 inputs are converted to FP32 for multiplication and accumulated in FP32.",
        "finalize_rule": "The FP32 accumulator may be exported as FP32 or rounded once to FP16.",
        "pairs": [
            {
                "a_fp16": float(np.float16(a)),
                "a_bits": fp16_bits(a),
                "b_fp16": float(np.float16(b)),
                "b_bits": fp16_bits(b),
                "product_fp32": float(product),
            }
            for (a, b), product in zip(pairs, products)
        ],
        "acc_fp32": float(acc_fp32),
        "acc_fp32_dtype": str(acc_fp32.dtype),
        "final_fp16": float(out_fp16),
        "final_fp16_bits": fp16_bits(out_fp16),
    }


def build_text_report(samples: dict[str, object]) -> str:
    lines = [
        "03_fp_model / fp32_acc summary",
        "",
        f"mode: {samples['mode']}",
        f"rule: {samples['rule']}",
        f"finalize_rule: {samples['finalize_rule']}",
        "",
        "products:",
    ]
    for idx, item in enumerate(samples["pairs"]):
        lines.append(
            "  "
            f"{idx}: a={item['a_fp16']}({item['a_bits']}) "
            f"b={item['b_fp16']}({item['b_bits']}) "
            f"product_fp32={item['product_fp32']}"
        )
    lines.extend(
        [
            "",
            f"acc_fp32: {samples['acc_fp32']}",
            f"final_fp16: {samples['final_fp16']} ({samples['final_fp16_bits']})",
        ]
    )
    return "\n".join(lines)


def write_reports(out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = build_samples()
    text_path = out_dir / "fp32_acc_summary.txt"
    json_path = out_dir / "fp32_acc_summary.json"
    text_path.write_text(build_text_report(samples) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    return text_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory where fp32_acc reports will be written.",
    )
    args = parser.parse_args()

    text_path, json_path = write_reports(args.out_dir)
    print(f"wrote: {text_path}")
    print(f"wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
