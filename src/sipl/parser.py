from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken
from lark.tree import Meta

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


class SiplSyntaxError(Exception):
    def __init__(self, message: str, span: SourceSpan, context: str = "") -> None:
        self.message = message
        self.span = span
        self.context = context
        super().__init__(f"{message} (line {span.line}, column {span.column})")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "SyntaxError",
            "message": self.message,
            "span": self.span.to_dict(),
            "context": self.context,
        }


@dataclass(frozen=True, slots=True)
class ParseResult:
    source: str
    cst: Tree[Token]
    ast: Program


@lru_cache(maxsize=1)
def get_lark_parser() -> Lark:
    grammar_text = files("sipl.grammar").joinpath("sipl.lark").read_text(encoding="utf-8")
    return Lark(grammar_text, parser="earley", propagate_positions=True)


def _span_from_meta(meta: Meta) -> SourceSpan:
    return SourceSpan(
        line=meta.line,
        column=meta.column,
        end_line=meta.end_line,
        end_column=meta.end_column,
        start_pos=meta.start_pos,
        end_pos=meta.end_pos,
    )


def _as_tree(node: Tree[Token] | Token) -> Tree[Token]:
    if not isinstance(node, Tree):
        raise TypeError(f"Expected syntax tree node, got token {node.type!r}")
    return node


def _as_token(node: Tree[Token] | Token) -> Token:
    if not isinstance(node, Token):
        raise TypeError(f"Expected token, got tree node {node.data!r}")
    return node


def _build_aexp(node: Tree[Token]) -> Aexp:
    span = _span_from_meta(node.meta)
    rule = node.data
    if rule == "num":
        tok = _as_token(node.children[0])
        return NumLit(value=int(tok.value), span=span)
    if rule == "neg_num":
        tok = _as_token(node.children[1])
        return NumLit(value=-int(tok.value), span=span)
    if rule == "var":
        tok = _as_token(node.children[0])
        return VarRef(name=tok.value, span=span)
    if rule in ("add", "sub", "mul"):
        op_map: dict[str, Literal["+", "-", "*"]] = {"add": "+", "sub": "-", "mul": "*"}
        return BinAexp(
            op=op_map[rule],
            left=_build_aexp(_as_tree(node.children[0])),
            right=_build_aexp(_as_tree(node.children[2])),
            span=span,
        )
    if rule == "paren_aexp":
        return _build_aexp(_as_tree(node.children[1]))
    raise ValueError(f"Unsupported arithmetic CST node: {rule!r}")


def _build_bexp(node: Tree[Token]) -> Bexp:
    span = _span_from_meta(node.meta)
    rule = node.data
    if rule in ("eq", "gt"):
        op_map: dict[str, Literal["=", ">"]] = {"eq": "=", "gt": ">"}
        return CmpBexp(
            op=op_map[rule],
            left=_build_aexp(_as_tree(node.children[0])),
            right=_build_aexp(_as_tree(node.children[2])),
            span=span,
        )
    if rule == "or_op":
        return OrBexp(
            left=_build_bexp(_as_tree(node.children[0])),
            right=_build_bexp(_as_tree(node.children[2])),
            span=span,
        )
    if rule == "not_op":
        return NotBexp(operand=_build_bexp(_as_tree(node.children[1])), span=span)
    if rule == "paren_bexp":
        return _build_bexp(_as_tree(node.children[1]))
    raise ValueError(f"Unsupported boolean CST node: {rule!r}")


def _build_stmt(node: Tree[Token]) -> Stmt:
    span = _span_from_meta(node.meta)
    rule = node.data
    if rule == "assign":
        target = _as_token(node.children[0]).value
        value = _build_aexp(_as_tree(node.children[2]))
        return AssignStmt(target=target, value=value, span=span)
    if rule == "seq":
        return SeqStmt(
            first=_build_stmt(_as_tree(node.children[0])),
            second=_build_stmt(_as_tree(node.children[2])),
            span=span,
        )
    if rule == "if_stmt":
        return IfStmt(
            condition=_build_bexp(_as_tree(node.children[1])),
            then_branch=_build_stmt(_as_tree(node.children[3])),
            else_branch=_build_stmt(_as_tree(node.children[5])),
            span=span,
        )
    if rule == "while_stmt":
        return WhileStmt(
            condition=_build_bexp(_as_tree(node.children[1])),
            body=_build_stmt(_as_tree(node.children[3])),
            span=span,
        )
    if rule == "block":
        return BlockStmt(body=_build_stmt(_as_tree(node.children[1])), span=span)
    if rule == "skip":
        return SkipStmt(span=span)
    raise ValueError(f"Unsupported statement CST node: {rule!r}")


def cst_to_ast(tree: Tree[Token]) -> Program:
    if tree.data != "program":
        raise ValueError(f"Expected root node 'program', got {tree.data!r}")
    body = _build_stmt(_as_tree(tree.children[1]))
    return Program(body=body, span=_span_from_meta(tree.meta))


def _format_syntax_error(exc: UnexpectedInput, source: str) -> SiplSyntaxError:
    lines = source.splitlines() or [""]
    line = exc.line if getattr(exc, "line", -1) > 0 else len(lines)
    column = exc.column if getattr(exc, "column", -1) > 0 else len(lines[-1]) + 1
    pos = exc.pos_in_stream if getattr(exc, "pos_in_stream", -1) >= 0 else len(source)
    span = SourceSpan(
        line=line,
        column=column,
        end_line=line,
        end_column=column,
        start_pos=pos,
        end_pos=pos,
    )
    try:
        context = exc.get_context(source).rstrip()
    except (ValueError, IndexError):
        context = ""

    if isinstance(exc, UnexpectedEOF):
        expected = ", ".join(sorted(exc.expected)) if exc.expected else "token"
        message = f"Unexpected end of input; expected {expected}"
    elif isinstance(exc, UnexpectedToken):
        expected = ", ".join(sorted(exc.expected)) if exc.expected else "valid token"
        message = f"Unexpected token {exc.token.value!r}; expected {expected}"
    elif isinstance(exc, UnexpectedCharacters):
        message = f"Unexpected character {exc.char!r}"
    else:
        message = str(exc)

    return SiplSyntaxError(message=message, span=span, context=context)


def parse_cst(source: str) -> Tree[Token]:
    try:
        return get_lark_parser().parse(source)
    except UnexpectedInput as exc:
        raise _format_syntax_error(exc, source) from exc


def parse_program(source: str) -> ParseResult:
    cst = parse_cst(source)
    ast = cst_to_ast(cst)
    return ParseResult(source=source, cst=cst, ast=ast)


def parse_ast(source: str) -> Program:
    return parse_program(source).ast