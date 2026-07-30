"""Print a session quality-control report (Adım 9b).

Timing (dropped frames, worst frame interval, SOA drift), timeout rates, the
per-module response distribution, objectively flagged trials, and the
cross-hearing check verdict.  The thresholds come from the session's own config
snapshot (``qc`` block), fixed before data collection.

    python tools/qc_report.py               # every session in the database
    python tools/qc_report.py --session 3   # one session

Exit code 0 on success, 1 if the database has no sessions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.analysis.qc_report import QCError, session_qc  # noqa: E402
from mcgurk.config.loader import ConfigError, load_config, resolve_path  # noqa: E402
from mcgurk.db.database import Database, DatabaseError  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402


def _session_ids(db: Database) -> list[int]:
    return [
        int(row["session_id"])
        for row in db.conn.execute("SELECT session_id FROM sessions ORDER BY session_id")
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qc_report", description="Oturum kalite kontrol raporu"
    )
    parser.add_argument("--config", type=Path, default=None, help="config yolu")
    parser.add_argument("--db", type=Path, default=None, help="config'teki veritabanını ez")
    parser.add_argument(
        "--session", type=int, default=None, help="yalnızca bu oturum (varsayılan: hepsi)"
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT, check_filesystem=False)
    except ConfigError as exc:
        print(f"Config hatası:\n{exc}", file=sys.stderr)
        return 1

    setup_logging(resolve_path(_PROJECT_ROOT, config.paths.logs))
    db_path = args.db or resolve_path(_PROJECT_ROOT, config.database.path)

    try:
        db = Database(db_path, create=False)
    except DatabaseError as exc:
        print(f"Veritabanı açılamadı:\n{exc}", file=sys.stderr)
        return 1

    try:
        sessions = [args.session] if args.session is not None else _session_ids(db)
        if not sessions:
            print("Veritabanında oturum yok.", file=sys.stderr)
            return 1
        for index, session_id in enumerate(sessions):
            if index:
                print("\n")
            try:
                print(session_qc(db, session_id).summary_text())
            except QCError as exc:
                print(f"Oturum {session_id}: {exc}", file=sys.stderr)
                return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
