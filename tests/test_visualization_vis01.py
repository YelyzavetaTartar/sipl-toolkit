import json
import xml.etree.ElementTree as ET
from pathlib import Path

from sipl.visualization import (
    build_parse_tree,
    render_dot,
    render_json,
    render_svg,
    render_text,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_parse_tree_nodes_link_to_source_spans() -> None:
    source = "begin\n  X := 1 + 2\nend"
    tree = build_parse_tree(source)
    assert tree.label == "program"
    assert tree.kind == "nonterminal"
    assert tree.span.line == 1
    assert tree.span.end_line == 3
    assert len(tree.children) == 3

    assign = tree.children[1]
    assert assign.label == "assign"
    assert assign.span.line == 2
    assert assign.snippet == "X := 1 + 2"


def test_render_text_and_json() -> None:
    source = (EXAMPLES_DIR / "gcd.sipl").read_text(encoding="utf-8")
    tree = build_parse_tree(source)

    text_out = render_text(tree)
    assert "[0] program" in text_out
    assert "while_stmt" in text_out
    assert "if_stmt" in text_out

    json_out = render_json(tree)
    parsed = json.loads(json_out)
    assert parsed["label"] == "program"
    assert parsed["span"]["line"] == 1
    assert len(parsed["children"]) == 3


def test_render_dot_and_valid_svg() -> None:
    source = (EXAMPLES_DIR / "power.sipl").read_text(encoding="utf-8")
    tree = build_parse_tree(source)

    dot_out = render_dot(tree)
    assert dot_out.startswith("digraph ParseTree {")
    assert "n0 -> n1;" in dot_out
    assert "while_stmt" in dot_out

    svg_out = render_svg(tree)
    root_el = ET.fromstring(svg_out)
    assert root_el.tag.endswith("svg")
    assert "<rect " in svg_out
    assert "<line " in svg_out
    assert "<title>" in svg_out