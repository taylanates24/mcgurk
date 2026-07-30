"""Export the database to flat files for analysis (Adım 9a).

Writes the ``v_trials_flat`` view — the table every downstream analysis reads —
and, for a whole-database export, the raw tables as well.

    python tools/export_data.py                       # CSV, whole database
    python tools/export_data.py --format both         # CSV + parquet
    python tools/export_data.py --session 3 --out out  # one session's flat rows

CSV is always written; parquet only when pyarrow is installed (``pip install
pyarrow``) — a parquet request with none present is warned and skipped, not an
error.  Exit code 0 on success.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.analysis.export import export_database, parquet_available  # noqa: E402
from mcgurk.config.loader import ConfigError, load_config, resolve_path  # noqa: E402
from mcgurk.db.database import Database, DatabaseError  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402

_FORMATS = {
    "csv": ("csv",),
    "parquet": ("parquet",),
    "both": ("csv", "parquet"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="export_data", description="Veritabanını analiz için düz dosyalara aktar"
    )
    parser.add_argument("--config", type=Path, default=None, help="config yolu")
    parser.add_argument("--db", type=Path, default=None, help="config'teki veritabanını ez")
    parser.add_argument(
        "--out", type=Path, default=None, help="çıktı klasörü (varsayılan: data/export)"
    )
    parser.add_argument(
        "--session", type=int, default=None, help="yalnızca bu oturumun düz satırları"
    )
    parser.add_argument(
        "--format",
        choices=sorted(_FORMATS),
        default="csv",
        help="csv (varsayılan) | parquet | both",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT, check_filesystem=False)
    except ConfigError as exc:
        print(f"Config hatası:\n{exc}", file=sys.stderr)
        return 1

    setup_logging(resolve_path(_PROJECT_ROOT, config.paths.logs))
    db_path = args.db or resolve_path(_PROJECT_ROOT, config.database.path)
    out_dir = args.out or (resolve_path(_PROJECT_ROOT, config.paths.data) / "export")
    formats = _FORMATS[args.format]

    if "parquet" in formats and not parquet_available():
        print(
            "Uyarı: parquet istendi ama pyarrow kurulu değil — yalnızca CSV yazılacak.\n"
            "       Etkinleştirmek için: pip install pyarrow",
            file=sys.stderr,
        )

    try:
        db = Database(db_path, create=False)
    except DatabaseError as exc:
        print(f"Veritabanı açılamadı:\n{exc}", file=sys.stderr)
        return 1

    try:
        written = export_database(db, out_dir, session_id=args.session, formats=formats)
    finally:
        db.close()

    if not written:
        print("Yazılan dosya yok.", file=sys.stderr)
        return 1
    print(f"{len(written)} dosya yazıldı -> {out_dir}")
    for path in written:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
