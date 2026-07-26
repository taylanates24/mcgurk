"""The mcgurk package must stay importable without PsychoPy.

CI installs no PsychoPy at all, and the config/database layers have to work on
an analysis machine that has none either.  A stray ``from psychopy import ...``
would only surface as a red CI run days later, so it is checked here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "mcgurk"

#: Adım 3 onwards, engine/ and ui/ will legitimately import PsychoPy.
PSYCHOPY_ALLOWED = {"engine", "ui", "modules"}


def _module_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_there_are_modules_to_check() -> None:
    assert len(_module_files()) > 5


@pytest.mark.parametrize("path", _module_files(), ids=lambda p: p.name)
def test_no_psychopy_import_in_the_pure_layers(path: Path) -> None:
    relative = path.relative_to(PACKAGE_ROOT)
    if relative.parts[0] in PSYCHOPY_ALLOWED:
        pytest.skip(f"{relative.parts[0]}/ sunum katmanı")
    assert "psychopy" not in _imported_roots(path.read_text(encoding="utf-8")), (
        f"{relative} PsychoPy import ediyor — config ve db katmanları "
        "PsychoPy'siz çalışabilmeli"
    )


def test_config_and_db_import_without_psychopy_installed(monkeypatch) -> None:
    """Import the layers with PsychoPy made unavailable."""
    import builtins
    import importlib

    real_import = builtins.__import__

    def blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "psychopy" or name.startswith("psychopy."):
            raise ModuleNotFoundError("psychopy (test tarafından engellendi)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", blocking_import)

    for module in (
        "mcgurk.config.schema",
        "mcgurk.config.loader",
        "mcgurk.config.calibration",
        "mcgurk.db.database",
        "mcgurk.db.backup",
        "mcgurk.db.design",
        "mcgurk.logging_setup",
        "mcgurk.provenance",
    ):
        importlib.reload(importlib.import_module(module))
