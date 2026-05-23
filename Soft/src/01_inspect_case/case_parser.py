"""Parsers for official sparse matrix testcase text files.

The official files describe sparse structure only.  A Matrix file stores one
record per row/column: ``<weight> <inner_dim>``.  The matching Index file stores
exactly ``weight`` indices on the same line number.  Blank index lines are valid
and represent zero weight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal


Axis = Literal["row", "col", "unknown"]


@dataclass(frozen=True)
class CaseMatrixProfile:
    """Sparse matrix structure as parsed from one Matrix/Index file pair."""

    name: str
    axis: Axis
    outer_size: int
    inner_size: int
    weights: tuple[int, ...]
    indices: tuple[tuple[int, ...], ...]
    matrix_path: Path
    index_path: Path
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def rows(self) -> int:
        if self.axis == "col":
            return self.inner_size
        return self.outer_size

    @property
    def cols(self) -> int:
        if self.axis == "col":
            return self.outer_size
        return self.inner_size

    @property
    def nnz(self) -> int:
        return sum(self.weights)

    @property
    def line_weights(self) -> tuple[int, ...]:
        return self.weights

    @property
    def line_indices(self) -> tuple[tuple[int, ...], ...]:
        return self.indices

    @property
    def max_line_weight(self) -> int:
        return max(self.weights, default=0)

    @property
    def max_line_density(self) -> float:
        denominator = self.cols if self.axis == "row" else self.rows
        return 0.0 if denominator == 0 else self.max_line_weight / denominator

    @property
    def empty_line_count(self) -> int:
        return sum(1 for weight in self.weights if weight == 0)

    @property
    def max_weight(self) -> int:
        return self.max_line_weight

    @property
    def max_weight_ratio(self) -> float:
        return self.max_line_density

    @property
    def empty_count(self) -> int:
        return self.empty_line_count

    @property
    def density(self) -> float:
        total = self.outer_size * self.inner_size
        return 0.0 if total == 0 else self.nnz / total

    @property
    def index_min(self) -> int | None:
        values = [idx for row in self.indices for idx in row]
        return min(values) if values else None

    @property
    def index_max(self) -> int | None:
        values = [idx for row in self.indices for idx in row]
        return max(values) if values else None


def parse_matrix_file(path: Path | str) -> tuple[tuple[int, int], ...]:
    """Parse ``*_Matrix.txt`` into ``(weight, inner_dim)`` records."""

    path = Path(path)
    records: list[tuple[int, int]] = []

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        if not parts:
            raise ValueError(f"{path}:{line_no}: blank Matrix line is not allowed")
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_no}: expected 2 integers, got {len(parts)}")
        try:
            weight, inner_dim = (int(parts[0]), int(parts[1]))
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: non-integer Matrix record") from exc
        if weight < 0:
            raise ValueError(f"{path}:{line_no}: negative sparse weight {weight}")
        if inner_dim <= 0:
            raise ValueError(f"{path}:{line_no}: non-positive inner dimension {inner_dim}")
        records.append((weight, inner_dim))

    if not records:
        raise ValueError(f"{path}: empty Matrix file")
    return tuple(records)


def parse_index_file(path: Path | str) -> tuple[tuple[int, ...], ...]:
    """Parse ``*_Index.txt`` while preserving blank lines as empty records."""

    path = Path(path)
    rows: list[tuple[int, ...]] = []

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        try:
            indices = tuple(int(part) for part in parts)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: non-integer index") from exc
        rows.append(indices)

    if not rows:
        raise ValueError(f"{path}: empty Index file")
    return tuple(rows)


def parse_sparse_pair(
    matrix_path: Path | str,
    index_path: Path | str,
    *,
    name: str | None = None,
    axis: Axis = "unknown",
) -> CaseMatrixProfile:
    """Parse and validate one official Matrix/Index file pair."""

    matrix_path = Path(matrix_path)
    index_path = Path(index_path)
    matrix_records = parse_matrix_file(matrix_path)
    index_rows = parse_index_file(index_path)

    diagnostics: list[str] = []
    if len(matrix_records) != len(index_rows):
        diagnostics.append(
            "record_count_mismatch: "
            f"matrix_records={len(matrix_records)} index_records={len(index_rows)}"
        )

    outer_size = min(len(matrix_records), len(index_rows))
    weights = tuple(weight for weight, _inner_dim in matrix_records[:outer_size])
    inner_dims = tuple(inner_dim for _weight, inner_dim in matrix_records[:outer_size])
    indices = index_rows[:outer_size]

    inner_size = inner_dims[0]
    if any(dim != inner_size for dim in inner_dims):
        diagnostics.append("inner_dim_mismatch: Matrix file contains multiple inner dims")

    for record_idx, (weight, row_indices) in enumerate(zip(weights, indices), 1):
        if weight != len(row_indices):
            diagnostics.append(
                f"weight_mismatch: record={record_idx} weight={weight} "
                f"index_count={len(row_indices)}"
            )
        if any(row_indices[i] > row_indices[i + 1] for i in range(len(row_indices) - 1)):
            diagnostics.append(f"unsorted_indices: record={record_idx}")

    diagnostics.extend(_index_base_diagnostics(indices, inner_size))

    return CaseMatrixProfile(
        name=name or matrix_path.stem.removesuffix("_Matrix"),
        axis=axis,
        outer_size=outer_size,
        inner_size=inner_size,
        weights=weights,
        indices=indices,
        matrix_path=matrix_path,
        index_path=index_path,
        diagnostics=tuple(diagnostics),
    )


def discover_case_pairs(case_dir: Path | str) -> list[tuple[str, Path, Path]]:
    """Return available ``(prefix, matrix_path, index_path)`` pairs."""

    case_dir = Path(case_dir)
    pairs: list[tuple[str, Path, Path]] = []
    for matrix_path in sorted(case_dir.glob("*_Matrix.txt")):
        prefix = matrix_path.name[: -len("_Matrix.txt")]
        index_path = case_dir / f"{prefix}_Index.txt"
        if index_path.exists():
            pairs.append((prefix, matrix_path, index_path))
    return pairs


def parse_case_dir(case_dir: Path | str) -> dict[str, CaseMatrixProfile]:
    """Parse all official Matrix/Index pairs found in a CASE directory."""

    parsed: dict[str, CaseMatrixProfile] = {}
    for prefix, matrix_path, index_path in discover_case_pairs(case_dir):
        parsed[prefix] = parse_sparse_pair(
            matrix_path,
            index_path,
            name=prefix,
            axis=_axis_hint(prefix),
        )
    return parsed


def _axis_hint(prefix: str) -> Axis:
    if prefix.startswith("A_"):
        return "row"
    if prefix.startswith("B_"):
        return "col"
    return "unknown"


def _index_base_diagnostics(indices: Iterable[Iterable[int]], inner_size: int) -> list[str]:
    flat = [idx for row in indices for idx in row]
    if not flat:
        return []

    min_idx = min(flat)
    max_idx = max(flat)
    diagnostics: list[str] = []

    if min_idx < 0:
        diagnostics.append(f"negative_index: min={min_idx}")

    valid_zero_based = min_idx >= 0 and max_idx < inner_size
    valid_one_based = min_idx >= 1 and max_idx <= inner_size

    if valid_zero_based and not valid_one_based:
        diagnostics.append("index_base=zero_based")
    elif valid_one_based and not valid_zero_based:
        diagnostics.append("index_base=one_based")
    elif valid_zero_based and valid_one_based:
        diagnostics.append("index_base=ambiguous")
    else:
        diagnostics.append(
            "index_base=invalid_or_mixed: "
            f"min={min_idx} max={max_idx} inner_dim={inner_size}"
        )

    return diagnostics


SparseMatrixRaw = CaseMatrixProfile
