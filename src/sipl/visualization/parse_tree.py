from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Literal

from lark import Token, Tree

from sipl.ast import SourceSpan
from sipl.parser import parse_cst


@dataclass(frozen=True, slots=True)
class ParseTreeNode:
    id: int
    label: str
    kind: Literal["nonterminal", "terminal"]
    span: SourceSpan
    snippet: str
    children: tuple[ParseTreeNode, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "span": self.span.to_dict(),
            "snippet": self.snippet,
            "children": [child.to_dict() for child in self.children],
        }


def _extract_snippet(source: str, span: SourceSpan, fallback: str = "") -> str:
    if span.start_pos is not None and span.end_pos is not None:
        raw = " ".join(source[span.start_pos : span.end_pos].split())
        if len(raw) > 36:
            return raw[:33] + "..."
        return raw
    return fallback


def _token_span(tok: Token) -> SourceSpan:
    line = tok.line if tok.line is not None else 1
    col = tok.column if tok.column is not None else 1
    end_line = tok.end_line if tok.end_line is not None else line
    end_col = tok.end_column if tok.end_column is not None else col
    return SourceSpan(
        line=line,
        column=col,
        end_line=end_line,
        end_column=end_col,
        start_pos=tok.start_pos,
        end_pos=tok.end_pos,
    )


def build_parse_tree(source: str) -> ParseTreeNode:
    cst = parse_cst(source)
    counter = 0

    def convert(node: Tree[Token] | Token) -> ParseTreeNode:
        nonlocal counter
        node_id = counter
        counter += 1

        if isinstance(node, Token):
            span = _token_span(node)
            snippet = _extract_snippet(source, span, fallback=node.value)
            return ParseTreeNode(
                id=node_id,
                label=f"{node.type}: {node.value}",
                kind="terminal",
                span=span,
                snippet=snippet,
                children=(),
            )

        meta = node.meta
        span = SourceSpan(
            line=meta.line,
            column=meta.column,
            end_line=meta.end_line,
            end_column=meta.end_column,
            start_pos=meta.start_pos,
            end_pos=meta.end_pos,
        )
        snippet = _extract_snippet(source, span)
        children = tuple(convert(child) for child in node.children)
        return ParseTreeNode(
            id=node_id,
            label=node.data,
            kind="nonterminal",
            span=span,
            snippet=snippet,
            children=children,
        )

    return convert(cst)


def _format_span(span: SourceSpan) -> str:
    return f"{span.line}:{span.column}..{span.end_line}:{span.end_column}"


def render_text(root: ParseTreeNode) -> str:
    lines: list[str] = []

    def walk(node: ParseTreeNode, prefix: str, is_last: bool, is_root: bool) -> None:
        span_str = _format_span(node.span)
        snippet_part = f' "{node.snippet}"' if node.snippet else ""
        entry = f"[{node.id}] {node.label} ({span_str}){snippet_part}"
        if is_root:
            lines.append(entry)
            child_prefix = ""
        else:
            branch = "`-- " if is_last else "|-- "
            lines.append(f"{prefix}{branch}{entry}")
            child_prefix = prefix + ("    " if is_last else "|   ")

        for idx, child in enumerate(node.children):
            walk(child, child_prefix, idx == len(node.children) - 1, False)

    walk(root, "", True, True)
    return "\n".join(lines)


def render_json(root: ParseTreeNode, *, indent: int = 2) -> str:
    return json.dumps(root.to_dict(), ensure_ascii=False, indent=indent)


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render_dot(root: ParseTreeNode) -> str:
    lines: list[str] = [
        "digraph ParseTree {",
        '  node [fontname="Consolas", fontsize=10];',
        '  edge [color="#64748b"];',
    ]

    def walk(node: ParseTreeNode) -> None:
        span_str = _format_span(node.span)
        label_text = f"{node.label}\\n[{span_str}]"
        tooltip = f"{node.label} ({span_str}) {node.snippet}".strip()
        if node.kind == "terminal":
            style = 'shape=box, style="rounded,filled", fillcolor="#e8f8ee", color="#16a34a"'
        else:
            style = 'shape=box, style="filled", fillcolor="#e8f1fb", color="#2563eb"'
        lines.append(
            f'  n{node.id} [label="{_dot_escape(label_text)}", '
            f'tooltip="{_dot_escape(tooltip)}", {style}];'
        )
        for child in node.children:
            lines.append(f"  n{node.id} -> n{child.id};")
            walk(child)

    walk(root)
    lines.append("}")
    return "\n".join(lines)


@dataclass(slots=True)
class _PositionedNode:
    node: ParseTreeNode
    x: float
    y: float
    width: float
    children: list[_PositionedNode]


def render_svg(root: ParseTreeNode) -> str:
    h_gap = 18.0
    level_height = 88.0
    node_height = 46.0
    margin = 24.0

    def box_width(node: ParseTreeNode) -> float:
        span_len = len(_format_span(node.span))
        chars = max(len(node.label), span_len)
        return max(84.0, chars * 7.4 + 22.0)

    def measure(node: ParseTreeNode) -> tuple[float, list[tuple[float, object]]]:
        own = box_width(node)
        if not node.children:
            return own, []
        child_measures = [measure(c) for c in node.children]
        total_children = sum(w for w, _ in child_measures) + h_gap * (len(node.children) - 1)
        return max(own, total_children), [(w, sub) for w, sub in child_measures]

    def place(
        node: ParseTreeNode,
        left_x: float,
        depth: int,
        subtree_w: float,
        child_data: list[tuple[float, object]],
    ) -> _PositionedNode:
        own = box_width(node)
        center_x = left_x + subtree_w / 2.0
        y = margin + depth * level_height
        placed_children: list[_PositionedNode] = []

        if node.children:
            total_children = (
                sum(w for w, _ in child_data) + h_gap * (len(node.children) - 1)
            )
            cursor = left_x + (subtree_w - total_children) / 2.0
            for child, (cw, grand) in zip(node.children, child_data, strict=True):
                assert isinstance(grand, list)
                placed_children.append(place(child, cursor, depth + 1, cw, grand))
                cursor += cw + h_gap

        return _PositionedNode(
            node=node,
            x=center_x,
            y=y,
            width=own,
            children=placed_children,
        )

    total_w, top_children = measure(root)
    placed_root = place(root, margin, 0, total_w, top_children)

    max_y = margin + node_height
    edges: list[str] = []
    boxes: list[str] = []

    def collect(pnode: _PositionedNode) -> None:
        nonlocal max_y
        max_y = max(max_y, pnode.y + node_height)
        for child in pnode.children:
            edges.append(
                f'<line x1="{pnode.x:.1f}" y1="{pnode.y + node_height:.1f}" '
                f'x2="{child.x:.1f}" y2="{child.y:.1f}" '
                f'stroke="#64748b" stroke-width="1.5" />'
            )
            collect(child)

        x0 = pnode.x - pnode.width / 2.0
        span_str = _format_span(pnode.node.span)
        tooltip_raw = f"{pnode.node.label} ({span_str}) {pnode.node.snippet}".strip()
        if pnode.node.kind == "terminal":
            fill, stroke = "#e8f8ee", "#16a34a"
        else:
            fill, stroke = "#e8f1fb", "#2563eb"

        boxes.append(
            f'<g>'
            f'<title>{html.escape(tooltip_raw)}</title>'
            f'<rect x="{x0:.1f}" y="{pnode.y:.1f}" width="{pnode.width:.1f}" '
            f'height="{node_height:.1f}" rx="8" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="1.5" />'
            f'<text x="{pnode.x:.1f}" y="{pnode.y + 19:.1f}" text-anchor="middle" '
            f'font-family="Consolas, monospace" font-size="12" font-weight="bold" '
            f'fill="#0f172a">{html.escape(pnode.node.label)}</text>'
            f'<text x="{pnode.x:.1f}" y="{pnode.y + 36:.1f}" text-anchor="middle" '
            f'font-family="Consolas, monospace" font-size="10" fill="#475569">'
            f'{html.escape(span_str)}</text>'
            f'</g>'
        )

    collect(placed_root)
    svg_w = total_w + 2 * margin
    svg_h = max_y + margin
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.0f}" '
        f'height="{svg_h:.0f}" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        *edges,
        *boxes,
        "</svg>",
    ]
    return "\n".join(parts)