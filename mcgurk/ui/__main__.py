"""``python -m mcgurk.ui`` — run one full session (steps.md §C Adım 8).

This is the new package's session entry point.  ``main.py`` still runs the
legacy ``src/`` flow until Adım 8c repoints it and retires ``src/``; until then
the two live side by side, on separate config and database files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.loader import (  # noqa: E402
    ConfigError,
    load_config,
    resolve_path,
)
from mcgurk.db.database import DatabaseError  # noqa: E402
from mcgurk.engine import EngineError  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.stimuli.manifest import ManifestError  # noqa: E402
from mcgurk.ui.session import run_session  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcgurk.ui",
        description="Tam oturum akışı (steps.md Adım 8)",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--db", type=Path, default=None, help="config'teki veritabanını ez"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="modül başına yalnızca ilk N deneme (geliştirme testi, veri toplama değil)",
    )
    parser.add_argument(
        "--device", default=None, help="bu koşu için audio.device'ı ez (config değişmez)"
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT)
    except ConfigError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    if args.device is not None:
        config.audio.device = args.device
        print(f"Aygıt bu koşu için ezildi: {args.device!r} (config değişmedi)")

    setup_logging(
        resolve_path(_PROJECT_ROOT, config.paths.logs),
        console_level=config.logging.console_level,
        file_level=config.logging.file_level,
    )

    db_path = args.db or resolve_path(_PROJECT_ROOT, config.database.path)
    try:
        return run_session(
            config, project_root=_PROJECT_ROOT, db_path=db_path, limit=args.limit
        )
    except (EngineError, DatabaseError, ManifestError) as exc:
        # A broken timing chain, a database problem or a missing stimulus is
        # something the operator has to act on — report it, do not traceback.
        print(f"\nHATA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
