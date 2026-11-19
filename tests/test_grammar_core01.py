from importlib.resources import files
from pathlib import Path

import pytest
from lark import Lark
from lark.exceptions import LarkError


def _load_parser() -> Lark:
    grammar_text = files("sipl.grammar").joinpath("sipl.lark").read_text(encoding="utf-8")
    return Lark(grammar_text, parser="earley", propagate_positions=True)


PARSER = _load_parser()

POSITIVE_PROGRAMS = [
    "begin skip end",
    "begin X := 1 end",
    "begin X := -1 end",
    "begin X := 0; Y := X + 2 * 3 - 1 end",
    "begin X := (A + B) * (C - D) end",
    "begin if X > 0 then Y := 1 else Y := 0 end",
    "begin if (X = 0) ∨ (Y > 1) then skip else X := X - 1 end",
    "begin if ¬(X = 0) then skip else skip end",
    "begin while not (M = N) do if M > N then M := M - N else N := N - M end",
    "begin while X > 0 or Y > 0 do begin X := X - 1; Y := Y - 1 end end",
    "begin while X > 0 do X := X - 1; Y := 42 end",
    "begin if X > 0 then X := 1 else X := 2; Y := 3 end",
    "begin done := 1; endless := done + 1 end",
]

NEGATIVE_PROGRAMS = [
    "",
    "X := 1",                              # немає зовнішнього begin ... end
    "begin end",                           # порожній блок заборонений БНФ
    "begin skip",                          # немає end
    "begin skip; end",                     # зайва ; перед end
    "begin ; skip end",                    # зайва ; на початку
    "begin if X > 0 then X := 1 end",      # немає else-гілки
    "begin while X do skip end",           # умова не може бути просто змінною
    "begin X := Y > 1 end",                # умова не може бути в правій частині :=
    "begin while := 1 end",                # ключове слово як ім'я змінної
    "begin X := 1 + * 2 end",              # некоректний вираз
    "begin X := (1 + 2 end",               # незакрита дужка
    "begin X := -Y end",                   # унарний мінус перед змінною відсутній у БНФ
]


@pytest.mark.parametrize("source", POSITIVE_PROGRAMS)
def test_valid_sipl_programs_parse(source: str) -> None:
    tree = PARSER.parse(source)
    assert tree.data == "program"


@pytest.mark.parametrize("source", NEGATIVE_PROGRAMS)
def test_invalid_sipl_programs_fail(source: str) -> None:
    with pytest.raises(LarkError):
        PARSER.parse(source)


def test_examples_directory_programs_parse() -> None:
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    sipl_files = sorted(examples_dir.glob("*.sipl"))
    assert len(sipl_files) >= 3
    for path in sipl_files:
        tree = PARSER.parse(path.read_text(encoding="utf-8"))
        assert tree.data == "program"