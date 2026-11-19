from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int
    start_pos: int | None = None
    end_pos: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }


@dataclass(frozen=True, slots=True)
class NumLit:
    value: int
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {"kind": "NumLit", "value": self.value, "span": self.span.to_dict()}


@dataclass(frozen=True, slots=True)
class VarRef:
    name: str
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {"kind": "VarRef", "name": self.name, "span": self.span.to_dict()}


@dataclass(frozen=True, slots=True)
class BinAexp:
    op: Literal["+", "-", "*"]
    left: Aexp
    right: Aexp
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "BinAexp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


Aexp = NumLit | VarRef | BinAexp


@dataclass(frozen=True, slots=True)
class CmpBexp:
    op: Literal["=", ">"]
    left: Aexp
    right: Aexp
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "CmpBexp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class OrBexp:
    left: Bexp
    right: Bexp
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "OrBexp",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NotBexp:
    operand: Bexp
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "NotBexp",
            "operand": self.operand.to_dict(),
            "span": self.span.to_dict(),
        }


Bexp = CmpBexp | OrBexp | NotBexp


@dataclass(frozen=True, slots=True)
class AssignStmt:
    target: str
    value: Aexp
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "AssignStmt",
            "target": self.target,
            "value": self.value.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SeqStmt:
    first: Stmt
    second: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SeqStmt",
            "first": self.first.to_dict(),
            "second": self.second.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class IfStmt:
    condition: Bexp
    then_branch: Stmt
    else_branch: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "IfStmt",
            "condition": self.condition.to_dict(),
            "then_branch": self.then_branch.to_dict(),
            "else_branch": self.else_branch.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class WhileStmt:
    condition: Bexp
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "WhileStmt",
            "condition": self.condition.to_dict(),
            "body": self.body.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class BlockStmt:
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "BlockStmt",
            "body": self.body.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SkipStmt:
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SkipStmt", "span": self.span.to_dict()}


Stmt = AssignStmt | SeqStmt | IfStmt | WhileStmt | BlockStmt | SkipStmt


@dataclass(frozen=True, slots=True)
class Program:
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, object]:
        return {"kind": "Program", "body": self.body.to_dict(), "span": self.span.to_dict()}