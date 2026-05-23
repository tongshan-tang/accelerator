#!/usr/bin/env python3
"""Export a TB runlist for one SRAM stimulus case."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SOFT_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = Path(__file__).resolve().parent
EXPORT_SRAM_DIR = SOFT_ROOT / "scripts" / "06_stimulus" / "02_export_sram"
for path in (STEP_DIR, EXPORT_SRAM_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from export_sram import export_case_sram


def default_sram_root() -> Path:
    return SOFT_ROOT / "output" / "06_stimulus" / "02_export_sram"


def default_out_dir() -> Path:
    return SOFT_ROOT / "output" / "06_stimulus" / "03_tb_runlist"


def resolve_sram_manifest(path_arg: str | Path, sram_root: Path = default_sram_root()) -> Path:
    path = Path(path_arg)
    if path.exists():
        manifest = path / "case_sram_manifest.json" if path.is_dir() else path
        if manifest.name == "case_sram_manifest.json" and manifest.exists():
            return manifest
        raise ValueError(f"{path}: expected SRAM case directory or case_sram_manifest.json")

    manifest = sram_root / "case" / str(path_arg) / "case_sram_manifest.json"
    if manifest.exists():
        return manifest

    try:
        return export_case_sram(str(path_arg), sram_root)
    except ValueError as exc:
        raise ValueError(f"{path_arg}: no SRAM manifest found and export failed: {exc}") from exc


def rel(path: Path, base: Path) -> str:
    return os.path.relpath(path, start=base)


def build_mem_paths(pair_dir: Path, mem_files: dict[str, str], base: Path) -> dict[str, dict[str, str]]:
    paths: dict[str, dict[str, str]] = {}
    for key, filename in mem_files.items():
        mem_path = pair_dir / filename
        paths[key] = {
            "path": rel(mem_path, base),
            "abs_path": str(mem_path),
        }
    return paths


def export_tb_runlist(path_arg: str | Path, out_dir: Path = default_out_dir()) -> Path:
    sram_manifest_path = resolve_sram_manifest(path_arg)
    sram_case_dir = sram_manifest_path.parent
    sram_manifest = json.loads(sram_manifest_path.read_text(encoding="utf-8"))
    case_name = sram_manifest["case_name"]
    target_dir = out_dir / "case" / case_name
    target_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, object]] = []
    for index, pair in enumerate(sram_manifest["pairs"]):
        pair_name = pair["pair"]
        pair_dir = sram_case_dir / pair_name
        input_config_path = pair_dir / "input_config.json"
        input_config = json.loads(input_config_path.read_text(encoding="utf-8"))
        runs.append(
            {
                "run_id": index,
                "pair": pair_name,
                "operation": input_config["operation"],
                "operation_code": input_config["operation_code"],
                "expression": input_config["expression"],
                "input_config": {
                    "path": rel(input_config_path, target_dir),
                    "abs_path": str(input_config_path),
                },
                "mem": build_mem_paths(pair_dir, input_config["mem_files"], target_dir),
                "a": input_config["a"],
                "b": input_config["b"],
                "c": input_config["c"],
            }
        )

    runlist = {
        "case_name": case_name,
        "source_sram_manifest": str(sram_manifest_path),
        "execution_model": sram_manifest["execution_model"],
        "run_count": len(runs),
        "runs": runs,
    }
    runlist_path = target_dir / "tb_runlist.json"
    runlist_path.write_text(json.dumps(runlist, indent=2) + "\n", encoding="utf-8")
    return runlist_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Case name, SRAM case directory, or case_sram_manifest.json.")
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    args = parser.parse_args()

    try:
        runlist_path = export_tb_runlist(args.path, args.out_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote: {runlist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
