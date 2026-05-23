#!/usr/bin/env python3
"""Add or subtract two FP16 bit-pattern hex values interactively."""

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


def fp16_bits(value: float | np.float16) -> str:
    return f"0x{int(np.float16(value).view(np.uint16)):04x}"


def addsub_fp16_bits(a_hex: str, operation: str, b_hex: str) -> dict[str, object]:
    if operation not in ("+", "-"):
        raise ValueError("operation must be + or -")
    a = parse_fp16_hex(a_hex)
    b = parse_fp16_hex(b_hex)
    if operation == "+":
        result = np.float16(a + b)
    else:
        result = np.float16(a - b)
    return {
        "a_bits": fp16_bits(a),
        "a_value": float(a),
        "operation": operation,
        "b_bits": fp16_bits(b),
        "b_value": float(b),
        "result_fp16": float(result),
        "result_fp16_bits": fp16_bits(result),
    }


def print_result(result: dict[str, object]) -> None:
    print(f"a_fp16       : {result['a_value']} ({result['a_bits']})")
    print(f"operation    : {result['operation']}")
    print(f"b_fp16       : {result['b_value']} ({result['b_bits']})")
    print(f"result_fp16  : {result['result_fp16']} ({result['result_fp16_bits']})")


def parse_repl_parts(text: str) -> tuple[str, str, str]:
    parts = text.replace(",", " ").split()
    if len(parts) != 3:
        raise ValueError("enter exactly two 16-bit hex values and one operation")
    if parts[1] in ("+", "-"):
        return parts[0], parts[1], parts[2]
    if parts[2] in ("+", "-"):
        return parts[0], parts[2], parts[1]
    raise ValueError("operation must be + or -")


def run_repl() -> int:
    print("Enter FP16 hex operation, e.g. '3c00 + 4000'. Press Ctrl+C to quit.")
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
            a_hex, operation, b_hex = parse_repl_parts(text)
            print_result(addsub_fp16_bits(a_hex, operation, b_hex))
        except ValueError as exc:
            print(f"invalid input: {exc}")
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values", nargs="*", help="Optional operation: A_HEX OP B_HEX.")
    args = parser.parse_args()

    if not args.values:
        return run_repl()
    a_hex, operation, b_hex = parse_repl_parts(" ".join(args.values))
    print_result(addsub_fp16_bits(a_hex, operation, b_hex))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
