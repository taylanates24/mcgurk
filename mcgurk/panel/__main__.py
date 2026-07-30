"""``python -m mcgurk.panel`` — open the operator panel (Adım 10b).

Builds the runtime (source or frozen — Adım 10a), loads the config, resolves the
database path against the writable root, and shows the window.  A config that
will not load is reported in a dialog rather than a traceback: the operator this
panel is for does not read Python errors.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from mcgurk.config.loader import (  # noqa: E402
    ConfigError,
    load_config,
    resolve_path,
)
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.panel import core  # noqa: E402
from mcgurk.panel.app import PanelWindow  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcgurk.panel",
        description="Operatör paneli (steps.md Adım 10)",
    )
    parser.add_argument("--config", type=Path, default=None, help="config dosyası")
    parser.add_argument(
        "--db", type=Path, default=None, help="config'teki veritabanını ez"
    )
    args = parser.parse_args(argv)

    runtime = core.detect_runtime()
    # QApplication must exist before any dialog, so a config error is shown in a
    # message box rather than printed.
    app = QApplication(sys.argv)

    try:
        config = load_config(
            args.config,
            project_root=runtime.resource_root,
            check_filesystem=False,
        )
    except ConfigError as exc:
        QMessageBox.critical(None, "Config yüklenemedi", str(exc))
        return 1

    setup_logging(
        resolve_path(runtime.writable_root, config.paths.logs),
        console_level=config.logging.console_level,
        file_level=config.logging.file_level,
    )

    db_path = args.db or resolve_path(runtime.writable_root, config.database.path)

    window = PanelWindow(runtime, config, db_path)
    window.show()
    # Annotated: QApplication.exec() is Any where PySide6 is absent (CI), which
    # would make main() return Any from an int-declared function (no-any-return).
    exit_code: int = app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
