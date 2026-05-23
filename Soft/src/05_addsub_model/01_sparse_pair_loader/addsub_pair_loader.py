"""Load generated sparse demo pairs for add/sub golden generation."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SOFT_ROOT = Path(__file__).resolve().parents[3]
SPARSE_LOADER_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "01_sparse_array_loader"
if str(SPARSE_LOADER_DIR) not in sys.path:
    sys.path.insert(0, str(SPARSE_LOADER_DIR))

from sparse_array_loader import SparseArrays, sparse_arrays_from_payload


Operation = Literal["+", "-"]


@dataclass(frozen=True)
class AddSubPair:
    case_name: str
    pair_id: int
    operation: Operation
    expression: str
    seed_base: int | None
    a: SparseArrays
    b: SparseArrays
    source_path: Path


def load_addsub_pair(pair_path: Path | str) -> AddSubPair:
    """Load and validate one generated pair JSON for FP16 add/sub."""

    pair_path = Path(pair_path)
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    operation = payload.get("operation")
    if operation not in ("+", "-"):
        raise ValueError(f"{pair_path}: operation is {operation}, not add/sub")

    matrices = payload["matrices"]
    assert isinstance(matrices, dict)
    a_payload = matrices["A"]
    b_payload = matrices["B"]
    assert isinstance(a_payload, dict)
    assert isinstance(b_payload, dict)
    a = sparse_arrays_from_payload(a_payload, source=f"{pair_path}:A")
    b = sparse_arrays_from_payload(b_payload, source=f"{pair_path}:B")
    validate_addsub_arrays(a, b)

    return AddSubPair(
        case_name=str(payload.get("case_name")),
        pair_id=int(payload.get("pair_id")),
        operation=operation,
        expression=str(payload.get("expression")),
        seed_base=payload.get("seed_base"),
        a=a,
        b=b,
        source_path=pair_path,
    )


def validate_addsub_arrays(a: SparseArrays, b: SparseArrays) -> tuple[SparseArrays, SparseArrays]:
    """Validate A/B storage and shape for sparse add/sub."""

    if a.storage_format != "csr":
        raise ValueError(f"{a.name}: A matrix must use csr, got {a.storage_format}")
    if b.storage_format != "csr":
        raise ValueError(f"{b.name}: B matrix must use csr for add/sub, got {b.storage_format}")
    if a.rows != b.rows or a.cols != b.cols:
        raise ValueError(f"shape mismatch: A is {a.rows}x{a.cols}, B is {b.rows}x{b.cols}")
    return a, b
