"""Deterministic FP16 value generation for sparse nonzero positions."""

from __future__ import annotations

import hashlib

import numpy as np


DEFAULT_VALUE_SEED = 20260523


def fp16_bits(value: float | np.float16) -> str:
    """Return the IEEE-754 binary16 bit pattern as four hex digits."""

    fp16_value = np.float16(value)
    return f"0x{int(fp16_value.view(np.uint16)):04x}"


def generate_fp16_value(
    matrix_name: str,
    line_id: int,
    inner_index: int,
    position_id: int,
    *,
    seed: int = DEFAULT_VALUE_SEED,
) -> np.float16:
    """Generate one stable nonzero FP16 value for a sparse coordinate."""

    key = f"{seed}:{matrix_name}:{line_id}:{inner_index}:{position_id}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    raw = int.from_bytes(digest[:4], byteorder="little", signed=False)
    sign = -1.0 if raw & 1 else 1.0
    # Keep values moderate to avoid early overflow-heavy examples.
    magnitude = 0.25 + ((raw >> 1) % 1984) / 256.0
    value = np.float16(sign * magnitude)
    if value == np.float16(0.0):
        return np.float16(0.25)
    return value


def generate_values_for_indices(
    matrix_name: str,
    indices: tuple[tuple[int, ...], ...],
    *,
    seed: int = DEFAULT_VALUE_SEED,
) -> tuple[tuple[np.float16, ...], ...]:
    """Generate FP16 values aligned with nested sparse index records."""

    values: list[tuple[np.float16, ...]] = []
    for line_id, line_indices in enumerate(indices):
        values.append(
            tuple(
                generate_fp16_value(matrix_name, line_id, inner_index, position_id, seed=seed)
                for position_id, inner_index in enumerate(line_indices)
            )
        )
    return tuple(values)
