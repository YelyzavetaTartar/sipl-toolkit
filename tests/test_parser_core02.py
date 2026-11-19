import pytest

from sipl.ast import (
    AssignStmt,
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
    VarRef,
    WhileStmt,
)
from sipl.parser import SiplSyntaxError, parse_ast, parse_program


def test_ast_precedence_arithmetic_and_left_associativity() -> None:
    prog = parse_ast("begin X := 1 + 2 * 3 - 4 - 5 end")
    assert isinstance(prog, Program)
    assert isinstance(prog.body, AssignStmt)
    expr = prog.body.value
    # ((1 + (2 * 3)) - 4) - 5
    assert isinstance(expr, BinAexp)
    assert expr.op == "-"
    assert isinstance(expr.right, NumLit) and expr.right.value == 5
    assert isinstance(expr.left, BinAexp) and expr.left.op == "-"
    assert isinstance(expr.left.left, BinAexp) and expr.left.left.op == "+"
    assert isinstance(expr.left.left.right, BinAexp) and expr.left.left.right.op == "*"


def test_ast_precedence_while_binds_tighter_than_seq() -> None:
    prog = parse_ast("begin while X > 0 do X := X - 1; Y := 42 end")
    assert isinstance(prog.body, SeqStmt)
    assert isinstance(prog.body.first, WhileStmt)
    assert isinstance(prog.body.second, AssignStmt)
    assert prog.body.second.target == "Y"


def test_ast_precedence_if_binds_tighter_than_seq() -> None:
    prog = parse_ast("begin if X = 1 then skip else X := 2; Y := 3 end")
    assert isinstance(prog.body, SeqStmt)
    assert isinstance(prog.body.first, IfStmt)
    assert isinstance(prog.body.first.then_branch, SkipStmt)
    assert isinstance(prog.body.first.else_branch, AssignStmt)
    assert isinstance(prog.body.second, AssignStmt)


def test_ast_boolean_precedence_not_before_or_and_parens() -> None:
    prog = parse_ast("begin if ¬X = 0 ∨ (Y > 1) then begin skip end else skip end")
    assert isinstance(prog.body, IfStmt)
    cond = prog.body.condition
    assert isinstance(cond, OrBexp)
    assert isinstance(cond.left, NotBexp)
    assert isinstance(cond.left.operand, CmpBexp) and cond.left.operand.op == "="
    assert isinstance(cond.right, CmpBexp) and cond.right.op == ">"
    assert isinstance(prog.body.then_branch, BlockStmt)


def test_ast_preserves_accurate_source_spans() -> None:
    source = "begin\n  X := -7;\n  skip\nend"
    res = parse_program(source)
    assert res.ast.span.line == 1
    assert res.ast.span.column == 1
    assert res.ast.span.end_line == 4
    assert res.ast.span.end_column == 4

    seq = res.ast.body
    assert isinstance(seq, SeqStmt)
    assign = seq.first
    assert isinstance(assign, AssignStmt)
    assert assign.span.line == 2
    assert assign.span.column == 3
    assert isinstance(assign.value, NumLit)
    assert assign.value.value == -7

    skip_node = seq.second
    assert isinstance(skip_node, SkipStmt)
    assert skip_node.span.line == 3
    assert skip_node.span.column == 3


def test_ast_to_dict_serializes_cleanly() -> None:
    prog = parse_ast("begin X := Y + 1 end")
    data = prog.to_dict()
    assert data["kind"] == "Program"
    body = data["body"]
    assert isinstance(body, dict)
    assert body["kind"] == "AssignStmt"
    assert isinstance(prog.body, AssignStmt)
    assert isinstance(prog.body.value, BinAexp)
    assert isinstance(prog.body.value.left, VarRef)


def test_syntax_error_diagnostics_have_line_and_column() -> None:
    bad_source = "begin\n  X := 1;\n  Y := ;\nend"
    with pytest.raises(SiplSyntaxError) as exc_info:
        parse_ast(bad_source)
    err = exc_info.value
    assert err.span.line == 3
    assert err.span.column >= 8
    err_dict = err.to_dict()
    assert err_dict["kind"] == "SyntaxError"
    assert "Unexpected" in str(err_dict["message"])


def test_syntax_error_on_unexpected_eof() -> None:
    with pytest.raises(SiplSyntaxError) as exc_info:
        parse_ast("begin skip")
    assert "Unexpected end of input" in exc_info.value.message