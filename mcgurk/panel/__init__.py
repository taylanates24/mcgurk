"""Operator panel (Adım 10).

``core`` is the GUI-free, PsychoPy-free logic (Adım 10a): launch-command
builders, read-only anonymous result browsing, analysis wrappers and
source/frozen path resolution.  The PySide6 shell (``app``) and the frozen
``.exe`` come in Adım 10b/10c and build on top of it.  Nothing here imports
PsychoPy (§A10.2).
"""

from __future__ import annotations

from .core import (
    MODULE_CHECKLIST,
    MODULE_UI,
    PanelError,
    ParticipantRow,
    Runtime,
    SessionRow,
    ToolResult,
    checklist_command,
    detect_runtime,
    export_all,
    export_session,
    list_participants,
    list_sessions,
    measures_text,
    open_readonly,
    qc_text,
    resolve_roots,
    run_module_command,
    run_tool,
    session_command,
    verify_backup_command,
    verify_stimuli_command,
)

__all__ = [
    "MODULE_CHECKLIST",
    "MODULE_UI",
    "PanelError",
    "ParticipantRow",
    "Runtime",
    "SessionRow",
    "ToolResult",
    "checklist_command",
    "detect_runtime",
    "export_all",
    "export_session",
    "list_participants",
    "list_sessions",
    "measures_text",
    "open_readonly",
    "qc_text",
    "resolve_roots",
    "run_module_command",
    "run_tool",
    "session_command",
    "verify_backup_command",
    "verify_stimuli_command",
]
