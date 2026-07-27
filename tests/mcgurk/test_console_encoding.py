"""Operator-facing text has to survive the console it is printed on.

Windows opens a Turkish console in cp1254, and Python raises
``UnicodeEncodeError`` rather than degrading when a string cannot be encoded.
A summary line containing U+2212 MINUS SIGN therefore does not print a slightly
wrong character — it replaces the whole report with a traceback, and an error
message containing "≠" replaces the error with a different one.

Adım 5 found this the way it is usually found: at the end of an eleven-minute
run, after the data was collected.  Docstrings and comments are exempt; they
are never encoded to a stream.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Where the code that prints, logs and raises lives.
SEARCH_ROOTS = ("mcgurk", "tools")

#: The console encoding to guarantee.  Turkish Windows; cp1252 and cp1254 agree
#: on everything above 127 that matters here, so this covers both.
CONSOLE_ENCODING = "cp1254"

#: The usual offenders and what to write instead.
SUGGESTIONS = {
    "−": "'-' (ASCII)",
    "≠": "'!='",
    "→": "'->'",
    "≤": "'<='",
    "≥": "'>='",
}


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root in SEARCH_ROOTS:
        files.extend(sorted((PROJECT_ROOT / root).rglob("*.py")))
    return files


def _docstring_ids(tree: ast.AST) -> set[int]:
    """Ids of the string constants that are docstrings, not values."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def _unencodable(text: str) -> list[str]:
    bad = []
    for char in dict.fromkeys(text):
        try:
            char.encode(CONSOLE_ENCODING)
        except UnicodeEncodeError:
            bad.append(char)
    return bad


def test_there_are_files_to_check() -> None:
    assert len(_source_files()) > 20


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_string_literals_can_reach_a_turkish_console(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = _docstring_ids(tree)

    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        for char in _unencodable(node.value):
            hint = SUGGESTIONS.get(char, "ASCII karşılığı")
            problems.append(
                f"  satır {node.lineno}: U+{ord(char):04X} {char!r} -> {hint}"
            )

    assert not problems, (
        f"{path.relative_to(PROJECT_ROOT)} {CONSOLE_ENCODING} konsolunda "
        "basılamayacak karakter içeriyor:\n" + "\n".join(problems)
    )
