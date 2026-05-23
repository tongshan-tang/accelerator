import json
from pathlib import Path
import sys

import pytest


STEP_DIR = Path(__file__).resolve().parent
SOFT_ROOT = STEP_DIR.parents[2]
SCRIPT_DIR = SOFT_ROOT / "scripts" / "02_sparse_format" / "05_case_generator"
SRC_SPARSE_ROOT = SOFT_ROOT / "src" / "02_sparse_format"
for path in (
    SCRIPT_DIR,
    SRC_SPARSE_ROOT / "01_sparse_types",
    SRC_SPARSE_ROOT / "02_value_generator",
    SRC_SPARSE_ROOT / "03_sparse_convert",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from case_generator import (
    MAX_MATRIX_DIM,
    MIN_MATRIX_DIM,
    MatrixSpec,
    PairSpec,
    choose_seed,
    format_expression,
    generate_pair_payload,
    generate_sparse_raw,
    raw_to_export,
    run_interactive_addsub,
    run_interactive_mul,
    validate_pair_spec,
    write_case,
)


def test_generate_sparse_raw_respects_max_line_density():
    raw = generate_sparse_raw("demo", 16, 32, axis="row", max_line_density=0.3, seed=1)

    assert raw.rows == 16
    assert raw.cols == 32
    assert raw.max_line_density <= 0.3
    assert raw.values is not None


def test_generate_sparse_raw_is_deterministic():
    first = generate_sparse_raw("demo", 16, 32, axis="col", seed=2)
    second = generate_sparse_raw("demo", 16, 32, axis="col", seed=2)

    assert first.indices == second.indices
    assert first.values == second.values


def test_generate_sparse_raw_rejects_invalid_density():
    with pytest.raises(ValueError, match="max_line_density"):
        generate_sparse_raw("demo", 16, 32, axis="row", max_line_density=-0.1, seed=1)

    with pytest.raises(ValueError, match="max_line_density"):
        generate_sparse_raw("demo", 16, 32, axis="row", max_line_density=1.1, seed=1)


def test_generate_sparse_raw_allows_zero_density():
    raw = generate_sparse_raw("demo", 16, 32, axis="row", max_line_density=0.0, seed=1)
    payload = raw_to_export(raw)

    assert raw.nnz == 0
    assert payload["arrays"]["ptr"] == [0] * (raw.rows + 1)
    assert payload["arrays"]["index"] == []
    assert payload["arrays"]["data_bits"] == []


def test_choose_seed_uses_explicit_seed_or_fresh_entropy(monkeypatch):
    assert choose_seed(123) == 123

    monkeypatch.setattr("case_generator.secrets.randbits", lambda bits: 456)

    assert choose_seed(None) == 456


def test_raw_to_export_contains_ptr_index_data():
    raw = generate_sparse_raw("demo", 16, 32, axis="row", seed=3)
    payload = raw_to_export(raw)

    assert payload["matrix"]["storage_format"] == "csr"
    assert len(payload["arrays"]["ptr"]) == raw.rows + 1
    assert len(payload["arrays"]["index"]) == len(payload["arrays"]["data_bits"])


def test_pair_validation_accepts_mul_and_addsub_shapes():
    validate_pair_spec(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*"))
    validate_pair_spec(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "row"), "+"))
    validate_pair_spec(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "row"), "-"))


def test_pair_validation_rejects_bad_shapes():
    try:
        validate_pair_spec(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 64, "col"), "*"))
    except ValueError:
        return
    raise AssertionError("multiply mismatch should be rejected")


def test_pair_validation_enforces_competition_dimension_range():
    validate_pair_spec(
        PairSpec(
            MatrixSpec(MIN_MATRIX_DIM, MAX_MATRIX_DIM, "row"),
            MatrixSpec(MAX_MATRIX_DIM, MIN_MATRIX_DIM, "col"),
            "*",
        )
    )

    try:
        validate_pair_spec(
            PairSpec(
                MatrixSpec(MIN_MATRIX_DIM - 1, 32, "row"),
                MatrixSpec(32, 16, "col"),
                "*",
            )
        )
    except ValueError as exc:
        assert f"[{MIN_MATRIX_DIM}, {MAX_MATRIX_DIM}]" in str(exc)
        return
    raise AssertionError("dimension below contest range should be rejected")


def test_pair_validation_rejects_dimension_above_competition_range():
    with pytest.raises(ValueError, match=r"\[16, 512\]"):
        validate_pair_spec(
            PairSpec(
                MatrixSpec(16, MAX_MATRIX_DIM + 1, "row"),
                MatrixSpec(MAX_MATRIX_DIM + 1, 16, "col"),
                "*",
            )
        )


def test_pair_validation_rejects_invalid_axis_and_operation():
    with pytest.raises(ValueError, match="A axis must be row"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "col"), MatrixSpec(32, 16, "col"), "*")
        )

    with pytest.raises(ValueError, match="axis must be row or col"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "diag"), "*")
        )

    with pytest.raises(ValueError, match="unsupported operation"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "/")
        )


def test_pair_validation_enforces_operation_specific_b_axis():
    with pytest.raises(ValueError, match="B axis must be col for multiplication"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "row"), "*")
        )

    with pytest.raises(ValueError, match="B axis must be row for add/sub"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "col"), "+")
        )

    with pytest.raises(ValueError, match="B axis must be row for add/sub"):
        validate_pair_spec(
            PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 32, "col"), "-")
        )


def test_pair_validation_rejects_addsub_mismatch():
    with pytest.raises(ValueError, match="add/sub shape mismatch"):
        validate_pair_spec(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 64, "row"), "+"))


def test_format_expression_zero_pads_dimensions():
    pair = PairSpec(MatrixSpec(32, 316, "row"), MatrixSpec(316, 16, "col"), "*")

    assert format_expression(pair) == "A(032,316)*B(316,016)"


def test_generate_pair_payload_contains_two_matrices():
    pair = PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")
    payload = generate_pair_payload("caseX", 1, pair, seed=5)

    assert payload["expression"] == "A(016,032)*B(032,016)"
    assert set(payload["matrices"]) == {"A", "B"}
    assert payload["matrices"]["A"]["matrix"]["storage_format"] == "csr"
    assert payload["matrices"]["B"]["matrix"]["storage_format"] == "csc"


def test_write_case_writes_10_pairs_and_summary(tmp_path):
    pairs = [
        PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")
        for _ in range(10)
    ]

    case_dir = write_case("case_test", pairs, tmp_path, seed=9)

    assert case_dir.exists()
    assert len(list(case_dir.glob("*.json"))) == 10
    assert len([p for p in case_dir.glob("*.txt") if p.name != "case_test_matrix_list.txt"]) == 10
    assert (case_dir / "case_test_matrix_list.txt").exists()


def test_write_case_rejects_wrong_pair_count(tmp_path):
    pairs = [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")]

    with pytest.raises(ValueError, match="exactly 10"):
        write_case("case_test", pairs, tmp_path, seed=9)


def test_write_case_removes_directory_on_invalid_pair(tmp_path):
    pairs = [
        PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")
        for _ in range(9)
    ]
    pairs.append(PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(16, 64, "col"), "*"))

    try:
        write_case("bad_case", pairs, tmp_path, seed=9)
    except ValueError:
        pass
    else:
        raise AssertionError("bad case should fail")

    assert not (tmp_path / "bad_case").exists()


def test_write_case_with_explicit_seed_reproduces_sparse_structure(tmp_path):
    pairs = [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")]

    first_dir = write_case(
        "first",
        pairs,
        tmp_path,
        seed=99,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    second_dir = write_case(
        "second",
        pairs,
        tmp_path,
        seed=99,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    first = json.loads((first_dir / "first_pair01.json").read_text(encoding="utf-8"))
    second = json.loads((second_dir / "second_pair01.json").read_text(encoding="utf-8"))
    for label in ("A", "B"):
        assert first["matrices"][label]["arrays"]["ptr"] == second["matrices"][label]["arrays"]["ptr"]
        assert first["matrices"][label]["arrays"]["index"] == second["matrices"][label]["arrays"]["index"]


def test_write_case_without_seed_uses_fresh_sparse_structure(tmp_path, monkeypatch):
    seeds = iter((101, 202))
    monkeypatch.setattr("case_generator.secrets.randbits", lambda bits: next(seeds))
    pairs = [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")]

    first_dir = write_case(
        "first",
        pairs,
        tmp_path,
        seed=None,
        expected_pair_count=1,
        write_matrix_list=False,
    )
    second_dir = write_case(
        "second",
        pairs,
        tmp_path,
        seed=None,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    first = json.loads((first_dir / "first_pair01.json").read_text(encoding="utf-8"))
    second = json.loads((second_dir / "second_pair01.json").read_text(encoding="utf-8"))
    assert first["seed_base"] == 101
    assert second["seed_base"] == 202
    for label in ("A", "B"):
        assert first["matrices"][label]["arrays"]["ptr"] != second["matrices"][label]["arrays"]["ptr"]
        assert first["matrices"][label]["arrays"]["index"] != second["matrices"][label]["arrays"]["index"]


def test_write_case_can_write_one_pair_demo(tmp_path):
    pairs = [PairSpec(MatrixSpec(16, 32, "row"), MatrixSpec(32, 16, "col"), "*")]

    demo_dir = write_case(
        "demo_test",
        pairs,
        tmp_path,
        seed=9,
        expected_pair_count=1,
        write_matrix_list=False,
    )

    assert demo_dir.exists()
    assert len(list(demo_dir.glob("*.json"))) == 1
    assert list(p.name for p in demo_dir.glob("*.txt")) == ["demo_test_pair01.txt"]
    assert not (demo_dir / "demo_test_matrix_list.txt").exists()


def test_run_interactive_mul_writes_under_mul_demo_subdir(tmp_path, monkeypatch):
    answers = iter(("mulx", "16", "32", "32", "16"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    demo_dir = run_interactive_mul(tmp_path, seed=123)

    assert demo_dir == tmp_path / "demo" / "mul" / "mulx"
    assert (demo_dir / "mulx_pair01.json").exists()
    assert (demo_dir / "mulx_pair01.txt").exists()


def test_run_interactive_addsub_writes_under_addsub_demo_subdir(tmp_path, monkeypatch):
    answers = iter(("addx", "16", "32", "+", "16", "32"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    demo_dir = run_interactive_addsub(tmp_path, seed=123)

    assert demo_dir == tmp_path / "demo" / "addsub" / "addx"
    assert (demo_dir / "addx_pair01.json").exists()
    assert (demo_dir / "addx_pair01.txt").exists()


def test_run_interactive_mul_removes_demo_on_shape_mismatch(tmp_path, monkeypatch):
    answers = iter(("badmul", "16", "32", "16", "16"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    with pytest.raises(ValueError, match="multiply shape mismatch"):
        run_interactive_mul(tmp_path, seed=123)

    assert not (tmp_path / "demo" / "mul" / "badmul").exists()


def test_run_interactive_addsub_removes_demo_on_shape_mismatch(tmp_path, monkeypatch):
    answers = iter(("badadd", "16", "32", "+", "16", "16"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    with pytest.raises(ValueError, match="add/sub shape mismatch"):
        run_interactive_addsub(tmp_path, seed=123)

    assert not (tmp_path / "demo" / "addsub" / "badadd").exists()
