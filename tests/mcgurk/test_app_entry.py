"""Adım 10c-i — the frozen ``--run`` dispatcher.

The dispatcher must route ``exe --run <subcommand>`` to the same ``main`` the
panel's command builders target.  ``parse_run`` is pure; the routing is checked
by monkeypatching each handler, so no session, checklist or tool actually runs.
The handlers are imported lazily, so importing this module needs neither PyQt6
nor PsychoPy — these tests run in CI.
"""

from __future__ import annotations

import pytest

from mcgurk import app_entry, paths


def test_parse_run_no_flag_is_the_panel_default() -> None:
    assert app_entry.parse_run(["--limit", "8"]) == (None, ["--limit", "8"])


def test_parse_run_splits_the_subcommand() -> None:
    assert app_entry.parse_run(["--run", "session", "--limit", "8"]) == (
        "session",
        ["--limit", "8"],
    )


def test_parse_run_requires_a_subcommand() -> None:
    with pytest.raises(paths.PanelError):
        app_entry.parse_run(["--run"])


def test_main_routes_session(monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        "mcgurk.ui.__main__.main",
        lambda rest: seen.update(rest=rest) or 7,
    )
    assert app_entry.main(["--run", "session", "--limit", "3"]) == 7
    assert seen["rest"] == ["--limit", "3"]


def test_main_routes_checklist(monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        "mcgurk.checklist.main",
        lambda rest: seen.update(rest=rest) or 1,
    )
    assert app_entry.main(["--run", "checklist", "--no-hardware"]) == 1
    assert seen["rest"] == ["--no-hardware"]


def test_main_routes_a_tool_script(monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        app_entry,
        "_run_tool_script",
        lambda script, rest: seen.update(script=script, rest=rest) or 0,
    )
    assert app_entry.main(["--run", "verify-stimuli", "--quick"]) == 0
    assert seen["script"] == "verify_stimuli.py"
    assert seen["rest"] == ["--quick"]


def test_main_unknown_subcommand_raises() -> None:
    with pytest.raises(paths.PanelError):
        app_entry.main(["--run", "bogus"])


def test_main_routes_panel_by_default(monkeypatch) -> None:
    pytest.importorskip("PyQt6")  # panel entry imports PyQt6
    import mcgurk.panel.__main__ as panel_main_mod

    monkeypatch.setattr(panel_main_mod, "main", lambda rest: 0)
    assert app_entry.main([]) == 0
