from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import assert_never

from sipl.ast import (
    Aexp,
    AssignStmt,
    Bexp,
    BinAexp,
    BlockStmt,
    CmpBexp,
    IfStmt,
    NotBexp,
    NumLit,
    OrBexp,
    Program,
    SeqStmt,
    SkipStmt,
    SourceSpan,
    Stmt,
    VarRef,
    WhileStmt,
)
from sipl.interpreter.trace import TraceCollector, TraceEvent
from sipl.parser import parse_ast


class SiplRuntimeError(Exception):
    def __init__(
        self,
        message: str,
        span: SourceSpan | None = None,
        trace: tuple[TraceEvent, ...] = (),
    ) -> None:
        self.message = message
        self.span = span
        self.trace = trace
        loc = f" (line {span.line}, column {span.column})" if span is not None else ""
        super().__init__(f"{message}{loc}")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": type(self).__name__,
            "message": self.message,
            "span": self.span.to_dict() if self.span is not None else None,
        }


class UndefinedVariableError(SiplRuntimeError):
    def __init__(self, name: str, span: SourceSpan | None = None) -> None:
        self.variable = name
        super().__init__(f"Undefined variable '{name}'", span=span)


class StepLimitExceededError(SiplRuntimeError):
    def __init__(self, max_steps: int, span: SourceSpan | None = None) -> None:
        self.max_steps = max_steps
        super().__init__(f"Execution exceeded step limit of {max_steps}", span=span)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    final_state: dict[str, int]
    steps: int
    trace: tuple[TraceEvent, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "final_state": dict(self.final_state),
            "steps": self.steps,
            "trace": [ev.to_dict() for ev in self.trace],
        }


def eval_aexp(expr: Aexp, state: Mapping[str, int]) -> int:
    if isinstance(expr, NumLit):
        return expr.value
    if isinstance(expr, VarRef):
        if expr.name not in state:
            raise UndefinedVariableError(expr.name, span=expr.span)
        return state[expr.name]
    if isinstance(expr, BinAexp):
        left = eval_aexp(expr.left, state)
        right = eval_aexp(expr.right, state)
        if expr.op == "+":
            return left + right
        if expr.op == "-":
            return left - right
        if expr.op == "*":
            return left * right
        assert_never(expr.op)
    assert_never(expr)


def eval_bexp(expr: Bexp, state: Mapping[str, int]) -> bool:
    if isinstance(expr, CmpBexp):
        left = eval_aexp(expr.left, state)
        right = eval_aexp(expr.right, state)
        if expr.op == "=":
            return left == right
        if expr.op == ">":
            return left > right
        assert_never(expr.op)
    if isinstance(expr, OrBexp):
        return eval_bexp(expr.left, state) or eval_bexp(expr.right, state)
    if isinstance(expr, NotBexp):
        return not eval_bexp(expr.operand, state)
    assert_never(expr)


class _Interpreter:
    def __init__(
        self,
        initial_state: Mapping[str, int] | None,
        max_steps: int,
        on_event: Callable[[TraceEvent], None] | None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.state: dict[str, int] = dict(initial_state) if initial_state is not None else {}
        self.max_steps = max_steps
        self.steps = 0
        self.collector = TraceCollector(on_event=on_event)

    def _tick(self, span: SourceSpan | None) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceededError(self.max_steps, span=span)

    def exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, SeqStmt):
            self.exec_stmt(stmt.first)
            self.exec_stmt(stmt.second)
            return

        stmt_kind = type(stmt).__name__
        self.collector.emit("BeforeStatement", self.state, stmt_kind=stmt_kind, span=stmt.span)

        if isinstance(stmt, SkipStmt):
            self._tick(stmt.span)
        elif isinstance(stmt, BlockStmt):
            self.exec_stmt(stmt.body)
        elif isinstance(stmt, AssignStmt):
            self._tick(stmt.span)
            new_val = eval_aexp(stmt.value, self.state)
            old_val = self.state.get(stmt.target)
            self.state[stmt.target] = new_val
            self.collector.emit(
                "VariableChanged",
                self.state,
                stmt_kind=stmt_kind,
                span=stmt.span,
                variable=stmt.target,
                old_value=old_val,
                new_value=new_val,
            )
        elif isinstance(stmt, IfStmt):
            self._tick(stmt.span)
            cond_val = eval_bexp(stmt.condition, self.state)
            self.collector.emit(
                "ConditionEvaluated",
                self.state,
                stmt_kind=stmt_kind,
                span=stmt.condition.span,
                condition_result=cond_val,
            )
            self.exec_stmt(stmt.then_branch if cond_val else stmt.else_branch)
        elif isinstance(stmt, WhileStmt):
            while True:
                self._tick(stmt.span)
                cond_val = eval_bexp(stmt.condition, self.state)
                self.collector.emit(
                    "ConditionEvaluated",
                    self.state,
                    stmt_kind=stmt_kind,
                    span=stmt.condition.span,
                    condition_result=cond_val,
                )
                if not cond_val:
                    break
                self.exec_stmt(stmt.body)
        else:
            assert_never(stmt)

        self.collector.emit("AfterStatement", self.state, stmt_kind=stmt_kind, span=stmt.span)


def execute(
    program: Program,
    initial_state: Mapping[str, int] | None = None,
    *,
    max_steps: int = 10_000,
    on_event: Callable[[TraceEvent], None] | None = None,
) -> ExecutionResult:
    interp = _Interpreter(initial_state=initial_state, max_steps=max_steps, on_event=on_event)
    try:
        interp.exec_stmt(program.body)
    except SiplRuntimeError as err:
        interp.collector.emit("Terminated", interp.state, span=err.span, reason="error")
        err.trace = interp.collector.events
        raise
    interp.collector.emit("Terminated", interp.state, span=program.span, reason="completed")
    return ExecutionResult(
        final_state=dict(interp.state),
        steps=interp.steps,
        trace=interp.collector.events,
    )


def run_source(
    source: str,
    initial_state: Mapping[str, int] | None = None,
    *,
    max_steps: int = 10_000,
    on_event: Callable[[TraceEvent], None] | None = None,
) -> ExecutionResult:
    program = parse_ast(source)
    return execute(program, initial_state=initial_state, max_steps=max_steps, on_event=on_event)