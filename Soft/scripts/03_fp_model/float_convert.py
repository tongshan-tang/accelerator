#!/usr/bin/env python3
"""Convert decimal floating-point inputs to FP16 and FP32 representations."""

from __future__ import annotations

import argparse

import numpy as np


def fp16_bits(value: np.float16) -> str:
    return f"0x{int(value.view(np.uint16)):04x}"


def fp32_bits(value: np.float32) -> str:
    return f"0x{int(value.view(np.uint32)):08x}"


def convert_one(text: str) -> dict[str, object]:
    value = float(text)
    fp16_value = np.float16(value)
    fp32_value = np.float32(value)
    return {
        "input": text,
        "float64_parse": value,
        "fp16_value": float(fp16_value),
        "fp16_bits": fp16_bits(fp16_value),
        "fp16_as_fp32": float(np.float32(fp16_value)),
        "fp32_value": float(fp32_value),
        "fp32_bits": fp32_bits(fp32_value),
    }


def print_result(result: dict[str, object]) -> None:
    print(f"input        : {result['input']}")
    print(f"float64_parse: {result['float64_parse']}")
    print(f"fp16_value   : {result['fp16_value']}")
    print(f"fp16_bits    : {result['fp16_bits']}")
    print(f"fp16_as_fp32 : {result['fp16_as_fp32']}")
    print(f"fp32_value   : {result['fp32_value']}")
    print(f"fp32_bits    : {result['fp32_bits']}")


def run_repl() -> int:
    print("Enter a floating-point value, then press Enter. Press Ctrl+C to quit.")
    while True:
        try:
            text = input("> ").strip()
        except KeyboardInterrupt:
            print("")
            return 0
        except EOFError:
            print("")
            return 0

        if not text:
            continue
        try:
            print_result(convert_one(text))
        except ValueError as exc:
            print(f"invalid input: {text} ({exc})")
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "values",
        nargs="*",
        help="Optional decimal floating-point values to convert once. Without values, enters REPL mode.",
    )
    args = parser.parse_args()

    if not args.values:
        return run_repl()

    for index, value in enumerate(args.values):
        if index:
            print("")
        print_result(convert_one(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
