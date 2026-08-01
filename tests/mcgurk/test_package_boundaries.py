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

#: engine/, ui/ and modules/ legitimately use PsychoPy.
PSYCHOPY_ALLOWED = {"engine", "ui", "modules"}

#: Engine and module files that must still *import* without PsychoPy installed.
#: They may use it — but only inside a function, so that the timing arithmetic,
#: the audio preparation, the trial design and the response categorisation stay
#: testable on a machine with no screen and no sound card, which is where CI
#: runs.  ``modules/response.py`` and ``modules/block.py`` are deliberately not
#: here: drawing an option grid and running a trial loop cannot be done without
#: PsychoPy in any case, and neither can ``modules/stream.py``, which flips a
#: window for five minutes.
ENGINE_IMPORTABLE_WITHOUT_PSYCHOPY = (
    "mcgurk.engine.scheduling",
    "mcgurk.engine.audio",
    "mcgurk.engine.loopback",
    "mcgurk.engine.window",
    "mcgurk.engine.av_presenter",
    "mcgurk.engine.psychopy_prefs",
    "mcgurk.modules.base",
    "mcgurk.modules.mcgurk",
    "mcgurk.modules.avsr",
    "mcgurk.modules.tbw",
    "mcgurk.modules.oddball",
    "mcgurk.modules.dichotic",
    "mcgurk.modules.gin",
)


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


@pytest.mark.parametrize("module_name", ENGINE_IMPORTABLE_WITHOUT_PSYCHOPY)
def test_engine_defers_its_psychopy_imports(module_name: str) -> None:
    """PsychoPy may be used inside functions, never at module level.

    This is what lets ``scheduling``, ``audio`` and ``loopback`` — the parts
    that decide when a sound starts, where it goes and whether it arrived — be
    tested in CI, where PsychoPy does not exist.
    """
    path = PACKAGE_ROOT / Path(*module_name.split(".")[1:]).with_suffix(".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    top_level_roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            top_level_roots.add(node.module.split(".")[0])

    assert "psychopy" not in top_level_roots
    assert "psychtoolbox" not in top_level_roots


#: Everything that has to import on a machine with no PsychoPy.
PURE_LAYERS = (
    "mcgurk.config.schema",
    "mcgurk.config.loader",
    "mcgurk.config.calibration",
    "mcgurk.db.database",
    "mcgurk.db.backup",
    "mcgurk.db.design",
    "mcgurk.logging_setup",
    "mcgurk.provenance",
    "mcgurk.stimuli.dsp",
    "mcgurk.stimuli.ffmpeg",
    "mcgurk.stimuli.manifest",
    "mcgurk.stimuli.prepare",
    "mcgurk.stimuli.verify",
    "mcgurk.stimuli.wavfile",
    # analysis/ runs on a machine that need not have PsychoPy; it reads the flat
    # view and each module's PsychoPy-free measures.
    "mcgurk.analysis.export",
    "mcgurk.analysis.measures",
    "mcgurk.analysis.qc_report",
    # panel/core is the operator panel's logic; it drives PsychoPy only through
    # separate processes (§A10.1) and must import without PsychoPy or PyQt6.
    "mcgurk.panel.core",
    # paths is the shared source/frozen path layer; app_entry is the frozen
    # dispatcher — both are pure and import their heavy handlers lazily.
    "mcgurk.paths",
    "mcgurk.app_entry",
    *ENGINE_IMPORTABLE_WITHOUT_PSYCHOPY,
)


def test_config_and_db_import_without_psychopy_installed(monkeypatch) -> None:
    """Import the layers with PsychoPy made unavailable.

    Imported into *fresh* module objects and thrown away afterwards, rather
    than reloaded in place.  ``importlib.reload`` re-executes the module in its
    existing namespace, so every class it defines becomes a new object while
    the rest of the test session still holds the old one — after which
    ``pytest.raises(FitError)`` stops catching that module's ``FitError`` and a
    pydantic model stops accepting its own config class.  Both were seen (Adım
    4, Adım 6) and both depended on collection order, which made them look like
    unrelated flakiness in whichever test file sorted last.
    """
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "psychopy" or name.startswith("psychopy."):
            raise ModuleNotFoundError("psychopy (test tarafından engellendi)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", blocking_import)

    saved = {name: sys.modules[name] for name in PURE_LAYERS if name in sys.modules}
    for name in PURE_LAYERS:
        sys.modules.pop(name, None)
    try:
        for name in PURE_LAYERS:
            importlib.import_module(name)
    finally:
        for name in PURE_LAYERS:
            sys.modules.pop(name, None)
        sys.modules.update(saved)
        # The import machinery also binds each submodule onto its package, so
        # ``from mcgurk.modules import tbw`` would otherwise keep handing out
        # the throwaway copy.
        for name, module in saved.items():
            parent_name, _, child = name.rpartition(".")
            parent = sys.modules.get(parent_name)
            if parent is not None:
                setattr(parent, child, module)
