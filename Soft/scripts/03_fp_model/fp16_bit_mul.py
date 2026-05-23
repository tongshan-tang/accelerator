#!/usr/bin/env python3
"""Multiply two FP16 bit-pattern hex values interactively."""

from __future__ import annotations

import argparse

import numpy as np


def parse_fp16_hex(text: str) -> np.float16:
    clean = text.strip().lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) != 4:
        raise ValueError("FP16 hex input must contain exactly 4 hex digits")
    bits = int(clean, 16)
    if bits < 0 or bits > 0xFFFF:
        raise ValueError("FP16 hex input out of 16-bit range")
    return np.array(bits, dtype=np.uint16).view(np.float16)[()]


def fp16_bits(value: np.float16) -> str:
    return f"0x{int(np.float16(value).view(np.uint16)):04x}"


def fp32_bits(value: np.float32) -> str:
    return f"0x{int(np.float32(value).view(np.uint32)):08x}"


def multiply_fp16_bits(a_hex: str, b_hex: str) -> dict[str, object]:
    a = parse_fp16_hex(a_hex)
    b = parse_fp16_hex(b_hex)
    product_fp32 = np.float32(a) * np.float32(b)
    product_fp16 = np.float16(product_fp32)
    return {
        "a_bits": fp16_bits(a),
        "a_value": float(a),
        "b_bits": fp16_bits(b),
        "b_value": float(b),
        "product_fp32": float(product_fp32),
        "product_fp32_bits": fp32_bits(product_fp32),
        "product_fp16": float(product_fp16),
        "product_fp16_bits": fp16_bits(product_fp16),
    }


def print_result(result: dict[str, object]) -> None:
    print(f"a_fp16        : {result['a_value']} ({result['a_bits']})")
    print(f"b_fp16        : {result['b_value']} ({result['b_bits']})")
    print(f"product_fp32  : {result['product_fp32']} ({result['product_fp32_bits']})")
    print(f"product_fp16  : {result['product_fp16']} ({result['product_fp16_bits']})")


def run_repl() -> int:
    print("Enter two FP16 hex values, e.g. '3c00 4000'. Press Ctrl+C to quit.")
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
        parts = text.replace(",", " ").split()
        if len(parts) != 2:
            print("invalid input: enter exactly two 16-bit hex values")
            print("")
            continue
        try:
            print_result(multiply_fp16_bits(parts[0], parts[1]))
        except ValueError as exc:
            print(f"invalid input: {exc}")
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values", nargs="*", help="Optional pair of FP16 hex values.")
    args = parser.parse_args()

    if not args.values:
        return run_repl()
    if len(args.values) != 2:
        parser.error("expected either no arguments or exactly two FP16 hex values")
    print_result(multiply_fp16_bits(args.values[0], args.values[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
