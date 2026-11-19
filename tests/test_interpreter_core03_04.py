from pathlib import Path

import pytest

from sipl.interpreter import (
    StepLimitExceededError,
    TraceEvent,
    UndefinedVariableError,
    run_source,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_execute_power_example() -> None:
    source = (EXAMPLES_DIR / "power.sipl").read_text(encoding="utf-8")
    result = run_source(source, {"X": 5, "Y": 2})
    assert result.final_state == {"X": 5, "Y": 0, "R": 25}
    assert result.steps > 0


def test_execute_gcd_example() -> None:
    source = (EXAMPLES_DIR / "gcd.sipl").read_text(encoding="utf-8")
    result = run_source(source, {"M": 8, "N": 16})
    assert result.final_state == {"M": 8, "N": 8}


def test_execute_factorial_example() -> None:
    source = (EXAMPLES_DIR / "factorial.sipl").read_text(encoding="utf-8")
    result = run_source(source, {"N": 5})
    assert result.final_state["R"] == 120


def test_execute_if_then_else_and_skip_and_boolean_ops() -> None:
    source = """
    begin
      if ¬(A = 0) ∨ (B > 10) then
        X := A * 2 + 1
      else
        skip
    end
    """
    res_true = run_source(source, {"A": 3, "B": 0})
    assert res_true.final_state["X"] == 7

    res_false = run_source(source, {"A": 0, "B": 5})
    assert res_false.final_state == {"A": 0, "B": 5}


def test_initial_state_is_not_mutated() -> None:
    initial = {"X": 10}
    res = run_source("begin X := X - 3 end", initial)
    assert initial == {"X": 10}
    assert res.final_state == {"X": 7}


def test_undefined_variable_raises_runtime_error() -> None:
    with pytest.raises(UndefinedVariableError) as exc_info:
        run_source("begin X := MISSING + 1 end")
    assert exc_info.value.variable == "MISSING"
    assert exc_info.value.span is not None
    assert exc_info.value.to_dict()["kind"] == "UndefinedVariableError"
    assert exc_info.value.trace[-1].kind == "Terminated"
    assert exc_info.value.trace[-1].reason == "error"


def test_infinite_loop_hits_step_limit() -> None:
    with pytest.raises(StepLimitExceededError) as exc_info:
        run_source("begin while 1 = 1 do skip end", max_steps=15)
    assert exc_info.value.max_steps == 15
    assert exc_info.value.trace[-1].kind == "Terminated"
    assert exc_info.value.trace[-1].reason == "error"


def test_invalid_max_steps_raises_value_error() -> None:
    with pytest.raises(ValueError):
        run_source("begin skip end", max_steps=0)


def test_trace_contains_all_expected_event_kinds_and_streaming_hook() -> None:
    streamed: list[TraceEvent] = []
    source = "begin X := 1; while X > 0 do X := X - 1 end"
    result = run_source(source, on_event=streamed.append)

    assert tuple(streamed) == result.trace
    kinds = [ev.kind for ev in result.trace]
    assert "BeforeStatement" in kinds
    assert "AfterStatement" in kinds
    assert "VariableChanged" in kinds
    assert "ConditionEvaluated" in kinds
    assert kinds[-1] == "Terminated"
    assert result.trace[-1].reason == "completed"

    var_events = [ev for ev in result.trace if ev.kind == "VariableChanged"]
    assert len(var_events) == 2
    assert var_events[0].old_value is None and var_events[0].new_value == 1
    assert var_events[1].old_value == 1 and var_events[1].new_value == 0

    payload = result.to_dict()
    assert payload["final_state"] == {"X": 0}
    assert isinstance(payload["trace"], list)