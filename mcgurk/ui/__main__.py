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
from mcgurk.config.schema import ExperimentConfig  # noqa: E402
from mcgurk.config.selection import (  # noqa: E402
    SelectionError,
    SessionSelection,
)
from mcgurk.config.selection import apply as apply_selection  # noqa: E402
from mcgurk.db.database import DatabaseError  # noqa: E402
from mcgurk.engine import EngineError  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.paths import detect_runtime, ensure_writable_config  # noqa: E402
from mcgurk.stimuli.manifest import ManifestError  # noqa: E402
from mcgurk.ui.session import run_session  # noqa: E402


def _selection_from(
    args: argparse.Namespace, config: ExperimentConfig
) -> SessionSelection | None:
    """The operator's choice, or ``None`` when they made none.

    ``None`` matters: it is what keeps the flags optional.  A session started
    without any of them runs the config's design untouched, so the snapshot,
    the resume path and the analysis see exactly what they saw before Adım 12.
    """
    if (
        args.speaker is None
        and args.modules is None
        and not args.no_practice
        and not args.no_cross_hearing
    ):
        return None

    if args.modules is None:
        modules = tuple(config.enabled_modules())
    else:
        modules = tuple(
            name.strip() for name in args.modules.split(",") if name.strip()
        )

    selection = SessionSelection(
        modules=modules,
        speaker_id=args.speaker,
        practice=not args.no_practice,
        cross_hearing=not args.no_cross_hearing,
    )
    # Fail here, before the checklist and the login dialog: a mistyped module
    # name should not be discovered by the participant already in the chair.
    apply_selection(config, selection)
    return selection


def build_parser() -> argparse.ArgumentParser:
    """The command line, separate from running it so the flags can be tested."""
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
    parser.add_argument(
        "--new-session",
        action="store_true",
        help="yarım oturum bulunsa bile devam teklif etme, yeni oturum başlat",
    )
    # Adım 12b: the operator's choice from the command line.  The menu that asks
    # the same questions is 12c; giving none of these runs the full design with
    # the config's own speaker, exactly as before (§A12.3).
    parser.add_argument(
        "--speaker",
        type=int,
        default=None,
        metavar="N",
        help="bu oturumun konuşmacısı (verilmezse speaker_selection karar verir)",
    )
    parser.add_argument(
        "--modules",
        default=None,
        metavar="A,B",
        help="yalnız bu ölçüm modülleri koşulsun (ör. mcgurk,dichotic)",
    )
    parser.add_argument(
        "--no-practice", action="store_true", help="alıştırma bloğunu atla"
    )
    parser.add_argument(
        "--no-cross-hearing", action="store_true", help="çapraz dinleme kontrolünü atla"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Path resolution goes through the shared layer (§A10.6): from a source
    # checkout ``writable_root`` is the repository root (behaviour unchanged);
    # frozen it is the writable location beside the .exe, and the config is the
    # writable copy (created from the bundled default on first run).
    runtime = detect_runtime()
    config_path = args.config or ensure_writable_config(runtime)
    try:
        config = load_config(config_path, project_root=runtime.writable_root)
    except ConfigError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    if args.device is not None:
        config.audio.device = args.device
        print(f"Aygıt bu koşu için ezildi: {args.device!r} (config değişmedi)")

    setup_logging(
        resolve_path(runtime.writable_root, config.paths.logs),
        console_level=config.logging.console_level,
        file_level=config.logging.file_level,
    )

    try:
        selection = _selection_from(args, config)
    except SelectionError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    db_path = args.db or resolve_path(runtime.writable_root, config.database.path)
    try:
        return run_session(
            config,
            project_root=runtime.writable_root,
            db_path=db_path,
            limit=args.limit,
            offer_resume=not args.new_session,
            selection=selection,
        )
    except (EngineError, DatabaseError, ManifestError) as exc:
        # A broken timing chain, a database problem or a missing stimulus is
        # something the operator has to act on — report it, do not traceback.
        print(f"\nHATA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
