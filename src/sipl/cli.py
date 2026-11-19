from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sipl.interpreter import SiplRuntimeError, execute
from sipl.parser import SiplSyntaxError, parse_program
from sipl.semantics import build_semantic_term
from sipl.visualization import (
    build_parse_tree,
    render_dot,
    render_json,
    render_svg,
    render_text,
)

EXIT_OK = 0
EXIT_CLI_USAGE = 2
EXIT_SYNTAX_ERROR = 3
EXIT_RUNTIME_ERROR = 4
EXIT_IO_ERROR = 5


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            enc = (stream.encoding or "").lower()
            if enc != "utf-8":
                stream.reconfigure(encoding="utf-8", errors="replace")


def _load_source(file_path: str) -> str:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"SIPL source file not found: {file_path}")
    return path.read_text(encoding="utf-8")


def _parse_initial_state(
    state_json: str | None,
    state_file: str | None,
    var_items: list[str] | None,
) -> dict[str, int]:
    state: dict[str, int] = {}

    if state_file is not None:
        raw_file = Path(state_file).read_text(encoding="utf-8")
        loaded = json.loads(raw_file)
        if not isinstance(loaded, dict):
            raise ValueError("--state-file must contain a JSON object mapping names to integers")
        for k, v in loaded.items():
            if not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int):
                raise TypeError(f"Invalid state entry in file: {k!r}={v!r}")
            state[k] = v

    if state_json is not None:
        loaded = json.loads(state_json)
        if not isinstance(loaded, dict):
            raise ValueError("--state must be a JSON object mapping names to integers")
        for k, v in loaded.items():
            if not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, int):
                raise TypeError(f"Invalid state entry: {k!r}={v!r}")
            state[k] = v

    for item in var_items or []:
        if "=" not in item:
            raise ValueError(f"Invalid --var format {item!r}; expected NAME=INT")
        name, raw_val = item.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Empty variable name in --var {item!r}")
        state[name] = int(raw_val.strip())

    return state


def _emit_json(payload: dict[str, object], *, to_stderr: bool = False) -> None:
    target = sys.stderr if to_stderr else sys.stdout
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=target)


def _emit_error(
    command: str,
    err_dict: dict[str, object],
    human_msg: str,
    *,
    as_json: bool,
) -> None:
    if as_json:
        _emit_json({"ok": False, "command": command, "error": err_dict}, to_stderr=True)
    else:
        print(f"Error: {human_msg}", file=sys.stderr)


def _add_state_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--state", help='Initial state as JSON object, e.g. \'{"X": 5}\'')
    sub.add_argument("--state-file", help="Path to JSON file with initial variable values")
    sub.add_argument(
        "--var",
        action="append",
        metavar="NAME=INT",
        help="Set a variable value (repeatable, e.g. --var X=5 --var Y=2)",
    )
    sub.add_argument(
        "--max-steps",
        type=int,
        default=10_000,
        help="Maximum execution steps before aborting infinite loops (default: 10000)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sipl",
        description="SIPL Language Toolkit CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_check = subparsers.add_parser("check", help="Validate syntax of a SIPL file")
    p_check.add_argument("file", help="Path to .sipl file")
    p_check.add_argument("--json", action="store_true", help="Output structured JSON")

    p_parse = subparsers.add_parser("parse", help="Parse a SIPL file into typed AST")
    p_parse.add_argument("file", help="Path to .sipl file")
    p_parse.add_argument("--json", action="store_true", help="Output structured JSON")

    p_run = subparsers.add_parser("run", help="Execute a SIPL program")
    p_run.add_argument("file", help="Path to .sipl file")
    _add_state_args(p_run)
    p_run.add_argument("--json", action="store_true", help="Output structured JSON")

    p_trace = subparsers.add_parser("trace", help="Execute and output full event trace")
    p_trace.add_argument("file", help="Path to .sipl file")
    _add_state_args(p_trace)
    p_trace.add_argument("--json", action="store_true", help="Output structured JSON")

    p_tree = subparsers.add_parser("tree", help="Export concrete parse tree")
    p_tree.add_argument("file", help="Path to .sipl file")
    p_tree.add_argument(
        "--format",
        choices=("text", "json", "dot", "svg"),
        default="text",
        help="Output format (default: text)",
    )
    p_tree.add_argument("-o", "--output", help="Write output to a file instead of stdout")
    p_tree.add_argument("--json", action="store_true", help="Wrap output in JSON envelope")

    p_sem = subparsers.add_parser("sem", help="Build semantic term in course notation")
    p_sem.add_argument("file", help="Path to .sipl file")
    p_sem.add_argument(
        "--style",
        choices=("course", "ascii"),
        default="course",
        help="Formatting style (default: course)",
    )
    p_sem.add_argument("--steps", action="store_true", help="Show rule derivation steps")
    p_sem.add_argument("--json", action="store_true", help="Output structured JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command: str = args.command
    as_json: bool = bool(args.json)

    try:
        source = _load_source(args.file)

        if command == "check":
            parsed = parse_program(source)
            if as_json:
                _emit_json(
                    {
                        "ok": True,
                        "command": "check",
                        "data": {"valid": True, "span": parsed.ast.span.to_dict()},
                    }
                )
            else:
                print(f"OK: {args.file}")
            return EXIT_OK

        if command == "parse":
            parsed = parse_program(source)
            ast_dict = parsed.ast.to_dict()
            if as_json:
                _emit_json({"ok": True, "command": "parse", "data": ast_dict})
            else:
                print(json.dumps(ast_dict, ensure_ascii=False, indent=2))
            return EXIT_OK

        if command in ("run", "trace"):
            initial = _parse_initial_state(args.state, args.state_file, args.var)
            parsed = parse_program(source)
            result = execute(parsed.ast, initial_state=initial, max_steps=args.max_steps)

            if command == "run":
                data: dict[str, object] = {
                    "final_state": dict(result.final_state),
                    "steps": result.steps,
                }
                if as_json:
                    _emit_json({"ok": True, "command": "run", "data": data})
                else:
                    print(f"Steps: {result.steps}")
                    print(f"Final state: {json.dumps(result.final_state, ensure_ascii=False)}")
                return EXIT_OK

            trace_data = result.to_dict()
            if as_json:
                _emit_json({"ok": True, "command": "trace", "data": trace_data})
            else:
                for ev in result.trace:
                    print(f"[{ev.seq}] {ev.kind} | state={ev.state}")
            return EXIT_OK

        if command == "tree":
            tree = build_parse_tree(source)
            fmt: str = args.format
            if fmt == "text":
                rendered = render_text(tree)
            elif fmt == "json":
                rendered = render_json(tree)
            elif fmt == "dot":
                rendered = render_dot(tree)
            else:
                rendered = render_svg(tree)

            if args.output is not None:
                Path(args.output).write_text(rendered, encoding="utf-8")

            if as_json:
                _emit_json(
                    {
                        "ok": True,
                        "command": "tree",
                        "data": {
                            "format": fmt,
                            "output_file": args.output,
                            "tree": tree.to_dict() if fmt == "json" else rendered,
                        },
                    }
                )
            elif args.output is None:
                print(rendered)
            else:
                print(f"Saved {fmt} parse tree to {args.output}")
            return EXIT_OK

        if command == "sem":
            term, steps = build_semantic_term(source)
            formatted = term.format(args.style)
            if as_json:
                _emit_json(
                    {
                        "ok": True,
                        "command": "sem",
                        "data": {
                            "style": args.style,
                            "formatted": formatted,
                            "term": term.to_dict(),
                            "steps": [s.to_dict() for s in steps],
                        },
                    }
                )
            else:
                print(formatted)
                if args.steps:
                    print("\nDerivation steps:")
                    for idx, step in enumerate(steps, start=1):
                        print(f"  {idx}. [{step.rule}] {step.node_kind} -> {step.result}")
            return EXIT_OK

    except SiplSyntaxError as err:
        msg = f"{err.message} (line {err.span.line}, column {err.span.column})"
        if err.context and not as_json:
            msg = f"{msg}\n{err.context}"
        _emit_error(command, err.to_dict(), msg, as_json=as_json)
        return EXIT_SYNTAX_ERROR

    except SiplRuntimeError as err:
        _emit_error(command, err.to_dict(), str(err), as_json=as_json)
        return EXIT_RUNTIME_ERROR

    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as err:
        _emit_error(
            command,
            {"kind": type(err).__name__, "message": str(err)},
            str(err),
            as_json=as_json,
        )
        return EXIT_IO_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())