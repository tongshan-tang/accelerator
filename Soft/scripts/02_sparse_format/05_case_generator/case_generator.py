#!/usr/bin/env python3
"""Generate random sparse matrices under line-density constraints."""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sparse_convert import raw_to_csc, raw_to_csr
from sparse_types import SparseMatrixRaw
from value_generator import DEFAULT_VALUE_SEED, fp16_bits, generate_values_for_indices


Axis = Literal["row", "col"]
Operation = Literal["*", "+", "-"]
MIN_MATRIX_DIM = 2**4
MAX_MATRIX_DIM = 2**9
CASE_PAIR_COUNT = 10
DEMO_PAIR_COUNT = 1


@dataclass(frozen=True)
class MatrixSpec:
    rows: int
    cols: int
    axis: Axis


@dataclass(frozen=True)
class PairSpec:
    a: MatrixSpec
    b: MatrixSpec
    operation: Operation


def generate_sparse_raw(
    name: str,
    rows: int,
    cols: int,
    *,
    axis: Axis,
    max_line_density: float = 0.3,
    seed: int = DEFAULT_VALUE_SEED,
) -> SparseMatrixRaw:
    """Generate one sparse matrix with per-line nnz bounded by max_line_density."""

    if not (0.0 <= max_line_density <= 1.0):
        raise ValueError("max_line_density must be in [0, 1]")
    outer_size = rows if axis == "row" else cols
    inner_size = cols if axis == "row" else rows
    max_line_weight = int(np.floor(inner_size * max_line_density))
    rng = np.random.default_rng(seed)

    records: list[tuple[int, ...]] = []
    for _line_id in range(outer_size):
        weight = int(rng.integers(0, max_line_weight + 1)) if max_line_weight > 0 else 0
        if weight == 0:
            records.append(())
            continue
        indices = tuple(sorted(int(x) for x in rng.choice(inner_size, size=weight, replace=False)))
        records.append(indices)

    indices = tuple(records)
    values = generate_values_for_indices(name, indices, seed=seed)
    return SparseMatrixRaw(
        name=name,
        rows=rows,
        cols=cols,
        axis=axis,
        indices=indices,
        values=values,
        diagnostics=(f"generated_random_sparse: seed={seed} max_line_density={max_line_density}",),
    )


def raw_to_export(raw: SparseMatrixRaw) -> dict[str, object]:
    """Convert generated raw sparse data into a compact JSON payload."""

    if raw.axis == "row":
        packed = raw_to_csr(raw)
        ptr = packed.row_ptr.astype(int).tolist()
        index = packed.col_idx.astype(int).tolist()
        storage_format = "csr"
        ptr_name = "row_ptr"
        index_name = "col_idx"
    else:
        packed = raw_to_csc(raw)
        ptr = packed.col_ptr.astype(int).tolist()
        index = packed.row_idx.astype(int).tolist()
        storage_format = "csc"
        ptr_name = "col_ptr"
        index_name = "row_idx"

    summary = packed.summary()
    return {
        "matrix": {
            "name": summary["name"],
            "storage_format": storage_format,
            "rows": summary["rows"],
            "cols": summary["cols"],
            "nnz": summary["nnz"],
            "density": summary["density"],
            "max_line_weight": summary["max_line_weight"],
            "max_line_density": summary["max_line_density"],
            "ptr_len": summary["ptr_len"],
            "index_len": summary["idx_len"],
            "data_len": summary["data_len"],
            "has_values": True,
            "diagnostics": summary["diagnostics"],
        },
        "arrays": {
            "ptr_name": ptr_name,
            "index_name": index_name,
            "data_name": "data",
            "ptr": ptr,
            "index": index,
            "data_fp16": [float(x) for x in packed.data],
            "data_bits": [fp16_bits(x) for x in packed.data],
        },
    }


def write_demo(out_dir: Path, *, seed: int = DEFAULT_VALUE_SEED) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    a_raw = generate_sparse_raw("random_demo_A", 32, 64, axis="row", seed=seed)
    b_raw = generate_sparse_raw("random_demo_B", 64, 32, axis="col", seed=seed + 1)
    payload = {
        "seed": seed,
        "max_line_density": 0.3,
        "matrices": {
            "random_demo_A": raw_to_export(a_raw),
            "random_demo_B": raw_to_export(b_raw),
        },
    }
    json_path = out_dir / "random_sparse_demo.json"
    txt_path = out_dir / "random_sparse_demo.txt"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    txt_path.write_text(build_text_report(payload) + "\n", encoding="utf-8")
    return txt_path, json_path


def validate_matrix_spec(spec: MatrixSpec, *, label: str) -> None:
    if spec.rows <= 0:
        raise ValueError(f"{label}.rows must be positive, got {spec.rows}")
    if spec.cols <= 0:
        raise ValueError(f"{label}.cols must be positive, got {spec.cols}")
    if not (MIN_MATRIX_DIM <= spec.rows <= MAX_MATRIX_DIM):
        raise ValueError(
            f"{label}.rows must be in [{MIN_MATRIX_DIM}, {MAX_MATRIX_DIM}], got {spec.rows}"
        )
    if not (MIN_MATRIX_DIM <= spec.cols <= MAX_MATRIX_DIM):
        raise ValueError(
            f"{label}.cols must be in [{MIN_MATRIX_DIM}, {MAX_MATRIX_DIM}], got {spec.cols}"
        )
    if spec.axis not in ("row", "col"):
        raise ValueError(f"{label}.axis must be row or col, got {spec.axis}")


def validate_pair_spec(pair: PairSpec) -> None:
    validate_matrix_spec(pair.a, label="A")
    validate_matrix_spec(pair.b, label="B")
    if pair.a.axis != "row":
        raise ValueError("A axis must be row")
    if pair.operation == "*":
        if pair.b.axis != "col":
            raise ValueError("B axis must be col for multiplication")
        if pair.a.cols != pair.b.rows:
            raise ValueError(
                f"multiply shape mismatch: A({pair.a.rows},{pair.a.cols}) "
                f"* B({pair.b.rows},{pair.b.cols})"
            )
    elif pair.operation in ("+", "-"):
        if pair.b.axis != "row":
            raise ValueError("B axis must be row for add/sub")
        if pair.a.rows != pair.b.rows or pair.a.cols != pair.b.cols:
            raise ValueError(
                f"add/sub shape mismatch: A({pair.a.rows},{pair.a.cols}) "
                f"{pair.operation} B({pair.b.rows},{pair.b.cols})"
            )
    else:
        raise ValueError(f"unsupported operation: {pair.operation}")


def format_expression(pair: PairSpec) -> str:
    return (
        f"A({pair.a.rows:03d},{pair.a.cols:03d})"
        f"{pair.operation}"
        f"B({pair.b.rows:03d},{pair.b.cols:03d})"
    )


def generate_pair_payload(
    case_name: str,
    pair_id: int,
    pair: PairSpec,
    *,
    seed: int = DEFAULT_VALUE_SEED,
    max_line_density: float = 0.3,
) -> dict[str, object]:
    validate_pair_spec(pair)
    a_name = f"{case_name}_pair{pair_id:02d}_A"
    b_name = f"{case_name}_pair{pair_id:02d}_B"
    a_raw = generate_sparse_raw(
        a_name,
        pair.a.rows,
        pair.a.cols,
        axis="row",
        max_line_density=max_line_density,
        seed=seed + pair_id * 2,
    )
    b_raw = generate_sparse_raw(
        b_name,
        pair.b.rows,
        pair.b.cols,
        axis=pair.b.axis,
        max_line_density=max_line_density,
        seed=seed + pair_id * 2 + 1,
    )
    return {
        "case_name": case_name,
        "pair_id": pair_id,
        "operation": pair.operation,
        "expression": format_expression(pair),
        "seed_base": seed,
        "max_line_density": max_line_density,
        "matrices": {
            "A": raw_to_export(a_raw),
            "B": raw_to_export(b_raw),
        },
    }


def build_pair_text(payload: dict[str, object]) -> str:
    lines = [
        f"{payload['case_name']} pair {int(payload['pair_id']):02d}",
        "",
        f"operation: {payload['operation']}",
        f"expression: {payload['expression']}",
        f"seed_base: {payload['seed_base']}",
        f"max_line_density: {payload['max_line_density']}",
        "",
    ]
    matrices = payload["matrices"]
    assert isinstance(matrices, dict)
    for label in ("A", "B"):
        matrix_payload = matrices[label]
        matrix = matrix_payload["matrix"]
        arrays = matrix_payload["arrays"]
        assert isinstance(matrix, dict)
        assert isinstance(arrays, dict)
        lines.append(f"[{label}]")
        lines.append(f"  storage_format   : {matrix['storage_format']}")
        lines.append(f"  rows x cols      : {matrix['rows']} x {matrix['cols']}")
        lines.append(f"  nnz              : {matrix['nnz']}")
        lines.append(f"  max_line_density : {matrix['max_line_density']:.6f}")
        lines.append(f"  ptr_name         : {arrays['ptr_name']}")
        lines.append(f"  index_name       : {arrays['index_name']}")
        lines.append(f"  ptr/index/data   : {matrix['ptr_len']} / {matrix['index_len']} / {matrix['data_len']}")
        lines.append("")
    return "\n".join(lines)


def choose_seed(seed: int | None) -> int:
    """Return a reproducible user seed or a fresh 32-bit seed for a new artifact."""

    if seed is not None:
        return seed
    return secrets.randbits(32)


def write_case(
    case_name: str,
    pairs: list[PairSpec],
    out_root: Path,
    *,
    seed: int | None = DEFAULT_VALUE_SEED,
    max_line_density: float = 0.3,
    expected_pair_count: int = CASE_PAIR_COUNT,
    overwrite: bool = True,
    write_matrix_list: bool = True,
) -> Path:
    if len(pairs) != expected_pair_count:
        raise ValueError(
            f"{case_name}: exactly {expected_pair_count} matrix pairs are required, got {len(pairs)}"
        )
    seed_base = choose_seed(seed)
    case_dir = out_root / case_name
    if case_dir.exists():
        if not overwrite:
            raise ValueError(f"{case_dir} already exists")
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    expressions: list[str] = []
    try:
        for pair_id, pair in enumerate(pairs, start=1):
            payload = generate_pair_payload(
                case_name,
                pair_id,
                pair,
                seed=seed_base,
                max_line_density=max_line_density,
            )
            expressions.append(str(payload["expression"]))
            stem = f"{case_name}_pair{pair_id:02d}"
            (case_dir / f"{stem}.json").write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
            (case_dir / f"{stem}.txt").write_text(build_pair_text(payload) + "\n", encoding="utf-8")

        if write_matrix_list:
            summary_lines = [f"{case_name}:", *expressions]
            (case_dir / f"{case_name}_matrix_list.txt").write_text(
                "\n".join(summary_lines) + "\n",
                encoding="utf-8",
            )
    except Exception:
        if case_dir.exists():
            shutil.rmtree(case_dir)
        raise
    return case_dir


def _prompt_nonempty(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValueError(f"empty input for prompt: {prompt}")
    return value


def _prompt_int(prompt: str) -> int:
    value = int(_prompt_nonempty(prompt))
    return value


def _prompt_operation() -> Operation:
    value = _prompt_nonempty("operation (*, +, -): ")
    if value not in ("*", "+", "-"):
        raise ValueError(f"operation must be *, +, or -, got {value}")
    return value  # type: ignore[return-value]


def _prompt_addsub_operation() -> Operation:
    value = _prompt_nonempty("operation (+, -): ")
    if value not in ("+", "-"):
        raise ValueError(f"operation must be + or -, got {value}")
    return value  # type: ignore[return-value]


def _prompt_axis(prompt: str) -> Axis:
    value = _prompt_nonempty(prompt).lower()
    if value not in ("row", "col"):
        raise ValueError(f"axis must be row or col, got {value}")
    return value  # type: ignore[return-value]


def run_interactive_bundle(
    out_root: Path,
    *,
    prompt_name: str,
    pair_count: int,
    seed: int | None = DEFAULT_VALUE_SEED,
) -> Path:
    bundle_name = _prompt_nonempty(prompt_name)
    bundle_dir = out_root / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pairs: list[PairSpec] = []
    try:
        for pair_id in range(1, pair_count + 1):
            print(f"\n[{bundle_name} pair {pair_id:02d}]")
            print("A axis: row")
            a_rows = _prompt_int("A rows: ")
            a_cols = _prompt_int("A cols: ")
            operation = _prompt_operation()
            b_axis = _prompt_axis("B axis (row/col): ")
            b_rows = _prompt_int("B rows: ")
            b_cols = _prompt_int("B cols: ")
            pair = PairSpec(
                a=MatrixSpec(a_rows, a_cols, "row"),
                b=MatrixSpec(b_rows, b_cols, b_axis),
                operation=operation,
            )
            validate_pair_spec(pair)
            print(f"accepted: {format_expression(pair)}")
            pairs.append(pair)
        return write_case(
            bundle_name,
            pairs,
            out_root,
            seed=seed,
            expected_pair_count=pair_count,
            overwrite=True,
            write_matrix_list=pair_count > 1,
        )
    except Exception:
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        raise


def run_interactive_fixed_demo(
    out_root: Path,
    *,
    demo_kind: Literal["mul", "addsub"],
    seed: int | None = DEFAULT_VALUE_SEED,
) -> Path:
    demo_name = _prompt_nonempty("demo name: ")
    demo_dir = out_root / "demo" / demo_kind / demo_name
    demo_dir.mkdir(parents=True, exist_ok=True)
    try:
        print(f"\n[{demo_name} pair 01]")
        print("A axis: row")
        a_rows = _prompt_int("A rows: ")
        a_cols = _prompt_int("A cols: ")
        if demo_kind == "mul":
            operation: Operation = "*"
            b_axis: Axis = "col"
            print("operation: *")
            print("B axis: col")
        else:
            operation = _prompt_addsub_operation()
            b_axis = "row"
            print("B axis: row")
        b_rows = _prompt_int("B rows: ")
        b_cols = _prompt_int("B cols: ")
        pair = PairSpec(
            a=MatrixSpec(a_rows, a_cols, "row"),
            b=MatrixSpec(b_rows, b_cols, b_axis),
            operation=operation,
        )
        validate_pair_spec(pair)
        print(f"accepted: {format_expression(pair)}")
        return write_case(
            demo_name,
            [pair],
            out_root / "demo" / demo_kind,
            seed=seed,
            expected_pair_count=DEMO_PAIR_COUNT,
            overwrite=True,
            write_matrix_list=False,
        )
    except Exception:
        if demo_dir.exists():
            shutil.rmtree(demo_dir)
        raise


def run_interactive_case(out_root: Path, *, seed: int | None = DEFAULT_VALUE_SEED) -> Path:
    return run_interactive_bundle(
        out_root / "case",
        prompt_name="case name: ",
        pair_count=CASE_PAIR_COUNT,
        seed=seed,
    )


def run_interactive_mul(out_root: Path, *, seed: int | None = DEFAULT_VALUE_SEED) -> Path:
    return run_interactive_fixed_demo(out_root, demo_kind="mul", seed=seed)


def run_interactive_addsub(out_root: Path, *, seed: int | None = DEFAULT_VALUE_SEED) -> Path:
    return run_interactive_fixed_demo(out_root, demo_kind="addsub", seed=seed)


def build_text_report(payload: dict[str, object]) -> str:
    lines = [
        "02_sparse_format random sparse demo",
        "",
        f"seed: {payload['seed']}",
        f"max_line_density: {payload['max_line_density']}",
        "",
    ]
    matrices = payload["matrices"]
    assert isinstance(matrices, dict)
    for name, matrix_payload in matrices.items():
        matrix = matrix_payload["matrix"]
        assert isinstance(matrix, dict)
        lines.append(f"[{name}]")
        lines.append(f"  storage_format   : {matrix['storage_format']}")
        lines.append(f"  rows x cols      : {matrix['rows']} x {matrix['cols']}")
        lines.append(f"  nnz              : {matrix['nnz']}")
        lines.append(f"  max_line_density : {matrix['max_line_density']:.6f}")
        lines.append(f"  ptr/index/data   : {matrix['ptr_len']} / {matrix['index_len']} / {matrix['data_len']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SOFT_ROOT / "output" / "02_sparse_format" / "05_case_generator",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for reproducible output. If omitted, a fresh seed is generated.",
    )
    parser.add_argument(
        "--interactive-case",
        action="store_true",
        help="Interactively generate a 10-pair case directory.",
    )
    parser.add_argument(
        "--interactive-mul",
        action="store_true",
        help="Interactively generate a 1-pair multiplication demo directory.",
    )
    parser.add_argument(
        "--interactive-addsub",
        action="store_true",
        help="Interactively generate a 1-pair add/sub demo directory.",
    )
    args = parser.parse_args()

    selected_modes = sum(bool(x) for x in (args.interactive_case, args.interactive_mul, args.interactive_addsub))
    if selected_modes > 1:
        parser.error("--interactive-case, --interactive-mul, and --interactive-addsub cannot be used together")

    if args.interactive_case:
        try:
            case_dir = run_interactive_case(args.out_dir, seed=args.seed)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote case directory: {case_dir}")
        return 0

    if args.interactive_mul:
        try:
            demo_dir = run_interactive_mul(args.out_dir, seed=args.seed)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote demo directory: {demo_dir}")
        return 0

    if args.interactive_addsub:
        try:
            demo_dir = run_interactive_addsub(args.out_dir, seed=args.seed)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote demo directory: {demo_dir}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
