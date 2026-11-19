from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sipl.cli import (
    EXIT_IO_ERROR,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_SYNTAX_ERROR,
    main,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _run_cli_subprocess(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sipl", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

def test_cli_check_and_parse_json(capsys: pytest.CaptureFixture[str]) -> None:
    power_file = str(EXAMPLES_DIR / "power.sipl")
    assert main(["check", power_file, "--json"]) == EXIT_OK
    check_out = json.loads(capsys.readouterr().out)
    assert check_out["ok"] is True
    assert check_out["data"]["valid"] is True

    assert main(["parse", power_file, "--json"]) == EXIT_OK
    parse_out = json.loads(capsys.readouterr().out)
    assert parse_out["ok"] is True
    assert parse_out["data"]["kind"] == "Program"


def test_cli_subprocess_run_and_trace_json() -> None:
    power_file = str(EXAMPLES_DIR / "power.sipl")

    run_proc = _run_cli_subprocess("run", power_file, "--var", "X=5", "--var", "Y=2", "--json")
    assert run_proc.returncode == EXIT_OK
    run_payload = json.loads(run_proc.stdout)
    assert run_payload["ok"] is True
    assert run_payload["command"] == "run"
    assert run_payload["data"]["final_state"] == {"X": 5, "Y": 0, "R": 25}

    trace_proc = _run_cli_subprocess("trace", power_file, "--var", "X=5", "--var", "Y=2", "--json")
    assert trace_proc.returncode == EXIT_OK
    trace_payload = json.loads(trace_proc.stdout)
    assert trace_payload["ok"] is True
    assert trace_payload["command"] == "trace"
    assert len(trace_payload["data"]["trace"]) > 0


def test_cli_run_with_state_file_and_json_flag(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text('{"M": 8, "N": 16}', encoding="utf-8")
    gcd_file = str(EXAMPLES_DIR / "gcd.sipl")

    proc = _run_cli_subprocess("run", gcd_file, "--state-file", str(state_path), "--json")
    assert proc.returncode == EXIT_OK
    payload = json.loads(proc.stdout)
    assert payload["data"]["final_state"] == {"M": 8, "N": 8}


def test_cli_tree_svg_and_sem_commands(tmp_path: Path) -> None:
    gcd_file = str(EXAMPLES_DIR / "gcd.sipl")
    svg_path = tmp_path / "gcd.svg"

    assert main(["tree", gcd_file, "--format", "svg", "-o", str(svg_path)]) == EXIT_OK
    assert "<svg " in svg_path.read_text(encoding="utf-8")

    proc = _run_cli_subprocess("sem", gcd_file, "--json")
    assert proc.returncode == EXIT_OK
    sem_payload = json.loads(proc.stdout)
    assert sem_payload["ok"] is True
    assert sem_payload["data"]["term"]["kind"] == "SemWhile"
    assert len(sem_payload["data"]["steps"]) > 0


def test_cli_error_exit_codes_and_json_errors(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.sipl"
    bad_file.write_text("begin X := end", encoding="utf-8")

    syn_proc = _run_cli_subprocess("check", str(bad_file), "--json")
    assert syn_proc.returncode == EXIT_SYNTAX_ERROR
    syn_err = json.loads(syn_proc.stderr)
    assert syn_err["ok"] is False
    assert syn_err["error"]["kind"] == "SyntaxError"

    undef_file = tmp_path / "undef.sipl"
    undef_file.write_text("begin X := MISSING end", encoding="utf-8")
    rt_proc = _run_cli_subprocess("run", str(undef_file), "--json")
    assert rt_proc.returncode == EXIT_RUNTIME_ERROR
    rt_err = json.loads(rt_proc.stderr)
    assert rt_err["ok"] is False
    assert rt_err["error"]["kind"] == "UndefinedVariableError"

    missing_proc = _run_cli_subprocess("check", str(tmp_path / "none.sipl"), "--json")
    assert missing_proc.returncode == EXIT_IO_ERROR
    io_err = json.loads(missing_proc.stderr)
    assert io_err["ok"] is False
    assert io_err["error"]["kind"] == "FileNotFoundError"