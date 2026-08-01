"""Frozen application entry point — the ``--run`` dispatcher (Adım 10c).

The packaged ``.exe`` is a single binary that is the panel by default and the
experiment, the checklist or a tool when asked.  The panel launches those as
*separate processes* (§A10.1) by re-invoking the same exe with
``--run <subcommand>``; this module is what that resolves to.  The subcommand
vocabulary is the one the panel's command builders target
(``mcgurk.paths.SUB_*``), so the two always agree.

From a source checkout nothing uses this: the panel launches ``-m mcgurk.ui`` and
the ``tools/`` scripts directly.  It exists for the frozen build, but it imports
and runs the very same ``main`` functions, so ``python -m mcgurk.app_entry
--run checklist`` behaves identically from source too — which is how it is
tested.

Handlers are imported lazily, inside each branch, so importing this module (for
the routing tests) pulls in neither PyQt6 nor PsychoPy.
"""

from __future__ import annotations

import runpy
import sys

from . import paths

#: Subcommands whose logic lives in a ``tools/`` script rather than a package
#: ``main``.  Run via runpy so the frozen exe needs no ``tools`` package.
_TOOL_SCRIPTS = {
    paths.SUB_VERIFY_STIMULI: "verify_stimuli.py",
    paths.SUB_VERIFY_BACKUP: "verify_backup.py",
    paths.SUB_RUN_MODULE: "run_module.py",
}


def _force_utf8_when_piped() -> None:
    """Emit UTF-8 on stdout/stderr when they are pipes (captured by the panel).

    A frozen build ignores ``PYTHONIOENCODING`` and defaults a *redirected*
    stream to the Windows ANSI code page (cp1254), so the panel — which reads the
    pipe as UTF-8 — would show mojibake.  ``reconfigure`` is a runtime call, not
    an env var, so the frozen interpreter honours it.  A real console (a direct
    terminal run) is left alone: its own code page already renders the text.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            if not stream.isatty():
                reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def parse_run(argv: list[str]) -> tuple[str | None, list[str]]:
    """Split ``--run <sub> ...`` into ``(subcommand, rest)``.

    Returns ``(None, argv)`` when there is no ``--run`` — the default, which
    opens the panel.  Raises on ``--run`` with no subcommand.
    """
    if argv and argv[0] == paths.RUN_FLAG:
        if len(argv) < 2:
            raise paths.PanelError(f"{paths.RUN_FLAG} icin alt komut gerekli.")
        return argv[1], list(argv[2:])
    return None, list(argv)


def _exit_code(code: object) -> int:
    """Normalise a ``SystemExit`` code to an int (None -> 0, str -> 1)."""
    if code is None:
        return 0
    return code if isinstance(code, int) else 1


def _run_tool_script(script: str, rest: list[str]) -> int:
    """Run a bundled ``tools/`` script as if it were ``python tools/<script>``.

    ``run_name="__main__"`` makes the script's own ``sys.exit(main())`` fire; its
    argv is set first, exactly as a shell invocation would.  The script is read
    from ``resource_root`` (the checkout, or the frozen bundle where the spec
    places ``tools/``).
    """
    runtime = paths.detect_runtime()
    script_path = runtime.resource_root / "tools" / script
    saved_argv = sys.argv
    sys.argv = [str(script_path), *rest]
    try:
        runpy.run_path(str(script_path), run_name="__main__")
        return 0
    except SystemExit as exc:
        return _exit_code(exc.code)
    finally:
        sys.argv = saved_argv


def main(argv: list[str] | None = None) -> int:
    _force_utf8_when_piped()
    args = list(sys.argv[1:] if argv is None else argv)
    subcommand, rest = parse_run(args)

    if subcommand is None:
        from .panel.__main__ import main as panel_main

        return panel_main(rest)
    if subcommand == paths.SUB_SESSION:
        from .ui.__main__ import main as session_main

        return session_main(rest)
    if subcommand == paths.SUB_CHECKLIST:
        from .checklist import main as checklist_main

        return checklist_main(rest)
    if subcommand in _TOOL_SCRIPTS:
        return _run_tool_script(_TOOL_SCRIPTS[subcommand], rest)

    raise paths.PanelError(f"Bilinmeyen {paths.RUN_FLAG} alt komutu: {subcommand}")


if __name__ == "__main__":
    sys.exit(main())
