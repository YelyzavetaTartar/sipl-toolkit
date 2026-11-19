from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from sipl.ast import SourceSpan

EventKind = Literal[
    "BeforeStatement",
    "AfterStatement",
    "VariableChanged",
    "ConditionEvaluated",
    "Terminated",
]


@dataclass(frozen=True, slots=True)
class TraceEvent:
    seq: int
    kind: EventKind
    state: dict[str, int]
    stmt_kind: str | None = None
    span: SourceSpan | None = None
    variable: str | None = None
    old_value: int | None = None
    new_value: int | None = None
    condition_result: bool | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "seq": self.seq,
            "kind": self.kind,
            "state": dict(self.state),
        }
        if self.stmt_kind is not None:
            data["stmt_kind"] = self.stmt_kind
        if self.span is not None:
            data["span"] = self.span.to_dict()
        if self.variable is not None:
            data["variable"] = self.variable
            data["old_value"] = self.old_value
            data["new_value"] = self.new_value
        if self.condition_result is not None:
            data["condition_result"] = self.condition_result
        if self.reason is not None:
            data["reason"] = self.reason
        return data


class TraceCollector:
    def __init__(self, on_event: Callable[[TraceEvent], None] | None = None) -> None:
        self._events: list[TraceEvent] = []
        self._on_event = on_event

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def emit(
        self,
        kind: EventKind,
        state: dict[str, int],
        *,
        stmt_kind: str | None = None,
        span: SourceSpan | None = None,
        variable: str | None = None,
        old_value: int | None = None,
        new_value: int | None = None,
        condition_result: bool | None = None,
        reason: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            seq=len(self._events) + 1,
            kind=kind,
            state=dict(state),
            stmt_kind=stmt_kind,
            span=span,
            variable=variable,
            old_value=old_value,
            new_value=new_value,
            condition_result=condition_result,
            reason=reason,
        )
        self._events.append(event)
        if self._on_event is not None:
            self._on_event(event)
        return event