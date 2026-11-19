from pathlib import Path

from sipl.ast import BinAexp, NumLit, SourceSpan, VarRef
from sipl.semantics import build_semantic_term, sem_A

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_golden_gcd_semantic_term_matches_textbook() -> None:
    source = (EXAMPLES_DIR / "gcd.sipl").read_text(encoding="utf-8")
    term, steps = build_semantic_term(source)
    expected = (
        "WH(S^1(neg, S^2(eq, M\u21d2, N\u21d2)), "
        "IF(S^2(gr, M\u21d2, N\u21d2), "
        "AS^M(S^2(sub, M\u21d2, N\u21d2)), "
        "AS^N(S^2(sub, N\u21d2, M\u21d2))))"
    )
    assert term.format("course") == expected
    assert steps[-1].rule == "NS_Prog"
    assert any(s.rule == "NS_Stm_Wh" for s in steps)
    assert any(s.rule == "NS_Stm_If" for s in steps)


def test_golden_power_semantic_term_matches_practicum() -> None:
    source = (EXAMPLES_DIR / "power.sipl").read_text(encoding="utf-8")
    term, steps = build_semantic_term(source)
    expected = (
        "AS^R(1\u0304) \u00b7 "
        "WH(S^2(gr, Y\u21d2, 0\u0304), "
        "(AS^R(S^2(mult, R\u21d2, X\u21d2)) \u00b7 "
        "AS^Y(S^2(sub, Y\u21d2, 1\u0304))))"
    )
    assert term.format("course") == expected
    assert any(s.rule == "NS_Stm_BE" for s in steps)


def test_golden_factorial_and_ascii_and_json_modes() -> None:
    source = (EXAMPLES_DIR / "factorial.sipl").read_text(encoding="utf-8")
    term, _ = build_semantic_term(source)
    ascii_out = term.format("ascii")
    assert "AS^R(const(1)) . AS^I(const(1)) . WH(S^2(or, " in ascii_out
    assert "N=>" in ascii_out

    payload = term.to_dict()
    assert payload["kind"] == "SemSeq"


def test_all_statement_and_expression_rules_covered() -> None:
    # Перевіряємо skip, + і *, а також приклад 1.2 (X + Y * Z)
    span = SourceSpan(1, 1, 1, 1)
    expr = BinAexp("+", VarRef("X", span), BinAexp("*", VarRef("Y", span), VarRef("Z", span), span), span)
    assert sem_A(expr).format("course") == "S^2(add, X\u21d2, S^2(mult, Y\u21d2, Z\u21d2))"

    term, steps = build_semantic_term("begin if ¬(A = 0) ∨ B > 1 then skip else X := -2 end")
    assert "id" in term.format("course")
    assert "S^1(neg, S^2(eq, A\u21d2, 0\u0304))" in term.format("course")
    assert term.to_dict()["kind"] == "SemIf"
    assert any(s.rule == "NS_Stm_skip" for s in steps)
    assert sem_A(NumLit(-2, span)).format("ascii") == "const(-2)"