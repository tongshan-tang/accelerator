#!/usr/bin/env python3
"""Build a golden bundle for one generated case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
MATMUL_DENSE_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "03_dense_golden"
MATMUL_LOADER_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "01_sparse_array_loader"
MATMUL_MATCHER_DIR = SOFT_ROOT / "src" / "04_matmul_model" / "02_merge_matcher"
ADDSUB_DENSE_DIR = SOFT_ROOT / "src" / "05_addsub_model" / "02_dense_golden"
ADDSUB_LOADER_DIR = SOFT_ROOT / "src" / "05_addsub_model" / "01_sparse_pair_loader"
for path in (
    STEP_DIR,
    MATMUL_LOADER_DIR,
    MATMUL_MATCHER_DIR,
    MATMUL_DENSE_DIR,
    ADDSUB_LOADER_DIR,
    ADDSUB_DENSE_DIR,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dense_addsub import addsub_from_generated_pair, write_result as write_addsub_result
from dense_matmul import matmul_from_generated_pair, write_result as write_matmul_result


def generated_root() -> Path:
    return SOFT_ROOT / "output" / "02_sparse_format" / "05_case_generator"


def default_out_dir() -> Path:
    return SOFT_ROOT / "output" / "06_stimulus" / "01_case_dispatch"


def resolve_case_path(path_arg: str | Path) -> Path:
    path = Path(path_arg)
    if path.exists():
        if path.is_dir() and path.parent.name == "case":
            return path
        raise ValueError(f"{path}: --path currently supports generated case directories only")

    case_dir = generated_root() / "case" / str(path_arg)
    if case_dir.exists():
        return case_dir
    raise ValueError(f"{path_arg}: not found under {generated_root() / 'case'}")


def pair_files(case_dir: Path) -> list[Path]:
    files = sorted(case_dir.glob("*_pair*.json"))
    if not files:
        raise ValueError(f"{case_dir}: no pair JSON files found")
    return files


def load_operation(pair_path: Path) -> str:
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    operation = payload.get("operation")
    if operation not in ("*", "+", "-"):
        raise ValueError(f"{pair_path}: unsupported operation {operation}")
    return str(operation)


def relative_to_out(path: Path, out_dir: Path) -> str:
    return str(path.relative_to(out_dir))


def build_case_bundle(path_arg: str | Path, out_dir: Path = default_out_dir()) -> Path:
    case_dir = resolve_case_path(path_arg)
    case_name = case_dir.name
    target_root = out_dir / "case" / case_name
    target_root.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, object]] = []
    for pair_path in pair_files(case_dir):
        operation = load_operation(pair_path)
        pair_id_text = pair_path.stem.rsplit("_", maxsplit=1)[-1]
        pair_out_dir = target_root / pair_id_text
        if operation == "*":
            result = matmul_from_generated_pair(pair_path)
            written = write_matmul_result(result, pair_out_dir, pair_path.stem)
            output_kind = "matmul"
        else:
            result = addsub_from_generated_pair(pair_path)
            written = write_addsub_result(result, pair_out_dir, pair_path.stem)
            output_kind = "addsub"

        summary = result["summary"]
        assert isinstance(summary, dict)
        entries.append(
            {
                "pair": pair_id_text,
                "operation": operation,
                "output_kind": output_kind,
                "expression": summary.get("source_expression"),
                "source_pair_json": str(pair_path),
                "golden_files": [relative_to_out(path, target_root) for path in written],
                "c_rows": summary.get("c_rows"),
                "c_cols": summary.get("c_cols"),
                "mode": summary.get("mode"),
            }
        )

    manifest = {
        "case_name": case_name,
        "source_case_dir": str(case_dir),
        "pair_count": len(entries),
        "pairs": entries,
    }
    manifest_path = target_root / "case_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Generated case name or case directory.")
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    args = parser.parse_args()

    try:
        manifest_path = build_case_bundle(args.path, args.out_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
