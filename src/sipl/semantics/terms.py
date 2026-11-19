from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, assert_never

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
    Stmt,
    VarRef,
    WhileStmt,
)
from sipl.parser import parse_ast

TermStyle = Literal["course", "ascii"]


def _overline(value: int) -> str:
    return "".join(f"{ch}\u0304" for ch in str(value))


@dataclass(frozen=True, slots=True)
class SemConst:
    value: int

    def format(self, style: TermStyle = "course") -> str:
        if style == "ascii":
            return f"const({self.value})"
        return _overline(self.value)

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemConst", "value": self.value}


@dataclass(frozen=True, slots=True)
class SemDeref:
    var: str

    def format(self, style: TermStyle = "course") -> str:
        if style == "ascii":
            return f"{self.var}=>"
        return f"{self.var}\u21d2"

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemDeref", "var": self.var}


@dataclass(frozen=True, slots=True)
class SemSuperA:
    op: Literal["add", "sub", "mult"]
    left: TFA
    right: TFA

    def format(self, style: TermStyle = "course") -> str:
        return f"S^2({self.op}, {self.left.format(style)}, {self.right.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemSuperA",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


TFA = SemConst | SemDeref | SemSuperA


@dataclass(frozen=True, slots=True)
class SemSuperCmp:
    op: Literal["eq", "gr"]
    left: TFA
    right: TFA

    def format(self, style: TermStyle = "course") -> str:
        return f"S^2({self.op}, {self.left.format(style)}, {self.right.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemSuperCmp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SemSuperOr:
    left: TFB
    right: TFB

    def format(self, style: TermStyle = "course") -> str:
        return f"S^2(or, {self.left.format(style)}, {self.right.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemSuperOr",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SemSuperNeg:
    operand: TFB

    def format(self, style: TermStyle = "course") -> str:
        return f"S^1(neg, {self.operand.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemSuperNeg", "operand": self.operand.to_dict()}


TFB = SemSuperCmp | SemSuperOr | SemSuperNeg


@dataclass(frozen=True, slots=True)
class SemId:
    def format(self, style: TermStyle = "course") -> str:
        return "id"

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemId"}


@dataclass(frozen=True, slots=True)
class SemAssign:
    var: str
    expr: TFA

    def format(self, style: TermStyle = "course") -> str:
        return f"AS^{self.var}({self.expr.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemAssign", "var": self.var, "expr": self.expr.to_dict()}


@dataclass(frozen=True, slots=True)
class SemSeq:
    first: TFS
    second: TFS

    def format(self, style: TermStyle = "course") -> str:
        sep = " . " if style == "ascii" else " \u00b7 "
        return f"{self.first.format(style)}{sep}{self.second.format(style)}"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemSeq",
            "first": self.first.to_dict(),
            "second": self.second.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SemIf:
    cond: TFB
    then_term: TFS
    else_term: TFS

    def format(self, style: TermStyle = "course") -> str:
        return (
            f"IF({self.cond.format(style)}, "
            f"{self.then_term.format(style)}, "
            f"{self.else_term.format(style)})"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemIf",
            "cond": self.cond.to_dict(),
            "then_term": self.then_term.to_dict(),
            "else_term": self.else_term.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SemWhile:
    cond: TFB
    body: TFS

    def format(self, style: TermStyle = "course") -> str:
        return f"WH({self.cond.format(style)}, {self.body.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SemWhile",
            "cond": self.cond.to_dict(),
            "body": self.body.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SemGroup:
    inner: TFS

    def format(self, style: TermStyle = "course") -> str:
        return f"({self.inner.format(style)})"

    def to_dict(self) -> dict[str, object]:
        return {"kind": "SemGroup", "inner": self.inner.to_dict()}


TFS = SemId | SemAssign | SemSeq | SemIf | SemWhile | SemGroup
SemTerm = TFA | TFB | TFS


@dataclass(frozen=True, slots=True)
class RuleStep:
    rule: str
    node_kind: str
    result: str

    def to_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "node_kind": self.node_kind, "result": self.result}


def sem_A(expr: Aexp, *, steps: list[RuleStep] | None = None) -> TFA:
    if isinstance(expr, NumLit):
        term: TFA = SemConst(expr.value)
        if steps is not None:
            steps.append(RuleStep("NS_A_Num", "NumLit", term.format()))
        return term
    if isinstance(expr, VarRef):
        term = SemDeref(expr.name)
        if steps is not None:
            steps.append(RuleStep("NS_A_Var", "VarRef", term.format()))
        return term
    if isinstance(expr, BinAexp):
        op_map: dict[Literal["+", "-", "*"], tuple[Literal["add", "sub", "mult"], str]] = {
            "+": ("add", "NS_A_Add"),
            "-": ("sub", "NS_A_Sub"),
            "*": ("mult", "NS_A_Mult"),
        }
        fn_name, rule_name = op_map[expr.op]
        left = sem_A(expr.left, steps=steps)
        right = sem_A(expr.right, steps=steps)
        term = SemSuperA(fn_name, left, right)
        if steps is not None:
            steps.append(RuleStep(rule_name, "BinAexp", term.format()))
        return term
    assert_never(expr)


def sem_B(expr: Bexp, *, steps: list[RuleStep] | None = None) -> TFB:
    if isinstance(expr, CmpBexp):
        op_map: dict[Literal["=", ">"], tuple[Literal["eq", "gr"], str]] = {
            "=": ("eq", "NS_B_eq"),
            ">": ("gr", "NS_B_gr"),
        }
        fn_name, rule_name = op_map[expr.op]
        left = sem_A(expr.left, steps=steps)
        right = sem_A(expr.right, steps=steps)
        term: TFB = SemSuperCmp(fn_name, left, right)
        if steps is not None:
            steps.append(RuleStep(rule_name, "CmpBexp", term.format()))
        return term
    if isinstance(expr, OrBexp):
        term = SemSuperOr(sem_B(expr.left, steps=steps), sem_B(expr.right, steps=steps))
        if steps is not None:
            steps.append(RuleStep("NS_B_or", "OrBexp", term.format()))
        return term
    if isinstance(expr, NotBexp):
        term = SemSuperNeg(sem_B(expr.operand, steps=steps))
        if steps is not None:
            steps.append(RuleStep("NS_B_neg", "NotBexp", term.format()))
        return term
    assert_never(expr)


def sem_S(stmt: Stmt, *, steps: list[RuleStep] | None = None) -> TFS:
    if isinstance(stmt, SkipStmt):
        term: TFS = SemId()
        if steps is not None:
            steps.append(RuleStep("NS_Stm_skip", "SkipStmt", term.format()))
        return term
    if isinstance(stmt, AssignStmt):
        term = SemAssign(stmt.target, sem_A(stmt.value, steps=steps))
        if steps is not None:
            steps.append(RuleStep("NS_Stm_As", "AssignStmt", term.format()))
        return term
    if isinstance(stmt, SeqStmt):
        term = SemSeq(sem_S(stmt.first, steps=steps), sem_S(stmt.second, steps=steps))
        if steps is not None:
            steps.append(RuleStep("NS_Stm_Seq", "SeqStmt", term.format()))
        return term
    if isinstance(stmt, IfStmt):
        term = SemIf(
            sem_B(stmt.condition, steps=steps),
            sem_S(stmt.then_branch, steps=steps),
            sem_S(stmt.else_branch, steps=steps),
        )
        if steps is not None:
            steps.append(RuleStep("NS_Stm_If", "IfStmt", term.format()))
        return term
    if isinstance(stmt, WhileStmt):
        term = SemWhile(
            sem_B(stmt.condition, steps=steps),
            sem_S(stmt.body, steps=steps),
        )
        if steps is not None:
            steps.append(RuleStep("NS_Stm_Wh", "WhileStmt", term.format()))
        return term
    if isinstance(stmt, BlockStmt):
        term = SemGroup(sem_S(stmt.body, steps=steps))
        if steps is not None:
            steps.append(RuleStep("NS_Stm_BE", "BlockStmt", term.format()))
        return term
    assert_never(stmt)


def sem_P(program: Program, *, steps: list[RuleStep] | None = None) -> TFS:
    term = sem_S(program.body, steps=steps)
    if steps is not None:
        steps.append(RuleStep("NS_Prog", "Program", term.format()))
    return term


def build_semantic_term(source: str) -> tuple[TFS, list[RuleStep]]:
    program = parse_ast(source)
    steps: list[RuleStep] = []
    term = sem_P(program, steps=steps)
    return term, steps