#!/usr/bin/env python3
"""Export per-pair SRAM init files from one case golden bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
CASE_DISPATCH_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "01_case_dispatch"
for path in (STEP_DIR, CASE_DISPATCH_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_dispatch import build_case_bundle


def default_case_bundle_root() -> Path:
    return SOFT_ROOT / "output" / "06_stimulus" / "01_case_dispatch"


def default_out_dir() -> Path:
    return SOFT_ROOT / "output" / "06_stimulus" / "02_export_sram"


def resolve_case_bundle(path_arg: str | Path, bundle_root: Path = default_case_bundle_root()) -> Path:
    path = Path(path_arg)
    if path.exists():
        manifest = path / "case_manifest.json" if path.is_dir() else path
        if manifest.name == "case_manifest.json" and manifest.exists():
            return manifest
        raise ValueError(f"{path}: expected case bundle directory or case_manifest.json")

    manifest = bundle_root / "case" / str(path_arg) / "case_manifest.json"
    if manifest.exists():
        return manifest

    # Build the golden bundle lazily from the 02 generated case if it is missing.
    try:
        return build_case_bundle(str(path_arg), bundle_root)
    except ValueError as exc:
        raise ValueError(f"{path_arg}: no case bundle found and build failed: {exc}") from exc


def hex_word(value: int, width_bits: int) -> str:
    mask = (1 << width_bits) - 1
    digits = (width_bits + 3) // 4
    return f"{int(value) & mask:0{digits}x}"


def fp16_hex(value: float) -> str:
    bits = np.float16(value).view(np.uint16)
    return hex_word(int(bits), 16)


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def matrix_export_payload(pair_payload: dict[str, object], label: str) -> tuple[dict[str, object], dict[str, object]]:
    matrices = pair_payload["matrices"]
    assert isinstance(matrices, dict)
    matrix_payload = matrices[label]
    assert isinstance(matrix_payload, dict)
    matrix = matrix_payload["matrix"]
    arrays = matrix_payload["arrays"]
    assert isinstance(matrix, dict)
    assert isinstance(arrays, dict)
    return matrix, arrays


def dense_golden_path(pair_bundle_dir: Path, pair_stem: str) -> Path:
    path = pair_bundle_dir / f"{pair_stem}_dense_golden.json"
    if not path.exists():
        raise ValueError(f"{path}: dense golden not found")
    return path


def c_dense_fp16_from_golden(golden_path: Path) -> list[list[float]]:
    payload = json.loads(golden_path.read_text(encoding="utf-8"))
    dense = payload["c_dense_fp16"]
    assert isinstance(dense, list)
    return dense


def flatten_dense(dense: list[list[float]]) -> list[float]:
    return [float(value) for row in dense for value in row]


def write_pair_sram_files(
    pair_payload: dict[str, object],
    pair_bundle_dir: Path,
    pair_out_dir: Path,
) -> dict[str, object]:
    pair_out_dir.mkdir(parents=True, exist_ok=True)
    pair_stem = f"{pair_payload['case_name']}_pair{int(pair_payload['pair_id']):02d}"
    operation = str(pair_payload["operation"])
    a_matrix, a_arrays = matrix_export_payload(pair_payload, "A")
    b_matrix, b_arrays = matrix_export_payload(pair_payload, "B")
    golden_path = dense_golden_path(pair_bundle_dir, pair_stem)
    c_dense = c_dense_fp16_from_golden(golden_path)

    files = {
        "A_ptr": "A_ptr.mem",
        "A_index": "A_index.mem",
        "A_data": "A_data.mem",
        "B_ptr": "B_ptr.mem",
        "B_index": "B_index.mem",
        "B_data": "B_data.mem",
        "C_golden_fp16": "C_golden_fp16.mem",
    }

    write_lines(pair_out_dir / files["A_ptr"], [hex_word(x, 18) for x in a_arrays["ptr"]])
    write_lines(pair_out_dir / files["A_index"], [hex_word(x, 16) for x in a_arrays["index"]])
    write_lines(pair_out_dir / files["A_data"], [str(x).removeprefix("0x") for x in a_arrays["data_bits"]])
    write_lines(pair_out_dir / files["B_ptr"], [hex_word(x, 18) for x in b_arrays["ptr"]])
    write_lines(pair_out_dir / files["B_index"], [hex_word(x, 16) for x in b_arrays["index"]])
    write_lines(pair_out_dir / files["B_data"], [str(x).removeprefix("0x") for x in b_arrays["data_bits"]])
    write_lines(pair_out_dir / files["C_golden_fp16"], [fp16_hex(x) for x in flatten_dense(c_dense)])

    c_rows = len(c_dense)
    c_cols = len(c_dense[0]) if c_dense else 0
    config = {
        "pair": f"pair{int(pair_payload['pair_id']):02d}",
        "operation": operation,
        "operation_code": {"*": 0, "+": 1, "-": 2}[operation],
        "expression": pair_payload["expression"],
        "seed_base": pair_payload.get("seed_base"),
        "a": {
            "rows": a_matrix["rows"],
            "cols": a_matrix["cols"],
            "storage_format": a_matrix["storage_format"],
            "ptr_len": len(a_arrays["ptr"]),
            "index_len": len(a_arrays["index"]),
            "data_len": len(a_arrays["data_bits"]),
        },
        "b": {
            "rows": b_matrix["rows"],
            "cols": b_matrix["cols"],
            "storage_format": b_matrix["storage_format"],
            "ptr_len": len(b_arrays["ptr"]),
            "index_len": len(b_arrays["index"]),
            "data_len": len(b_arrays["data_bits"]),
        },
        "c": {
            "rows": c_rows,
            "cols": c_cols,
            "output_len": c_rows * c_cols,
            "storage_format": "dense_row_major_fp16",
        },
        "mem_files": files,
        "source_pair_json": str(pair_payload.get("_source_pair_json", "")),
        "source_dense_golden_json": str(golden_path),
    }
    config_path = pair_out_dir / "input_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config


def export_case_sram(path_arg: str | Path, out_dir: Path = default_out_dir()) -> Path:
    manifest_path = resolve_case_bundle(path_arg)
    bundle_root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_name = manifest["case_name"]
    target_root = out_dir / "case" / case_name
    target_root.mkdir(parents=True, exist_ok=True)

    pair_entries: list[dict[str, object]] = []
    for entry in manifest["pairs"]:
        pair_name = entry["pair"]
        source_pair_json = Path(entry["source_pair_json"])
        pair_payload = json.loads(source_pair_json.read_text(encoding="utf-8"))
        pair_payload["_source_pair_json"] = str(source_pair_json)
        pair_bundle_dir = bundle_root / pair_name
        pair_out_dir = target_root / pair_name
        config = write_pair_sram_files(pair_payload, pair_bundle_dir, pair_out_dir)
        pair_entries.append(
            {
                "pair": pair_name,
                "operation": config["operation"],
                "operation_code": config["operation_code"],
                "expression": config["expression"],
                "input_config": f"{pair_name}/input_config.json",
                "c_rows": config["c"]["rows"],
                "c_cols": config["c"]["cols"],
            }
        )

    sram_manifest = {
        "case_name": case_name,
        "source_case_manifest": str(manifest_path),
        "execution_model": "load_one_pair_then_start_wait_done_check_then_overwrite",
        "pair_count": len(pair_entries),
        "pairs": pair_entries,
    }
    sram_manifest_path = target_root / "case_sram_manifest.json"
    sram_manifest_path.write_text(json.dumps(sram_manifest, indent=2) + "\n", encoding="utf-8")
    return sram_manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Case name, case bundle directory, or case_manifest.json.")
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    args = parser.parse_args()

    try:
        manifest_path = export_case_sram(args.path, args.out_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
