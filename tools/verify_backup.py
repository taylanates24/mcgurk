"""Verify a database backup.

An untested backup is not a backup (steps.md Adım 1).  This opens a backup
file, checks that SQLite considers it intact, that the foreign keys still hold,
that the schema version is the expected one, and reports the row counts — with
an optional comparison against what the live database contained.

    python tools/verify_backup.py backups/mcgurk_20260726T153149.sqlite
    python tools/verify_backup.py <backup> --compare-with data/mcgurk.sqlite

Exit code 0 = backup usable, 1 = do not rely on it.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.db.database import SCHEMA_VERSION  # noqa: E402

TABLES = ("participants", "calibrations", "sessions", "blocks", "trials", "responses")


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in TABLES
    }


def verify(backup_path: Path, compare_with: Path | None = None) -> tuple[bool, str]:
    """Check *backup_path*; return (ok, human-readable report).

    A corrupt file is the very thing this tool exists to catch, so a SQLite
    error is a verdict rather than a crash.
    """
    lines: list[str] = [f"Yedek: {backup_path}"]
    if not backup_path.is_file():
        return False, f"KIRMIZI  Yedek dosyası yok: {backup_path}"

    lines.append(f"Boyut  : {backup_path.stat().st_size:,} bayt")
    try:
        return _verify_open(backup_path, compare_with, lines)
    except sqlite3.DatabaseError as exc:
        lines.append(f"KIRMIZI  Yedek okunamadı: {exc}")
        return False, "\n".join(lines)


def _verify_open(
    backup_path: Path, compare_with: Path | None, lines: list[str]
) -> tuple[bool, str]:
    ok = True

    conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity == "ok":
            lines.append("YESIL    integrity_check: ok")
        else:
            ok = False
            lines.append(f"KIRMIZI  integrity_check: {integrity}")

        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            ok = False
            lines.append(f"KIRMIZI  foreign_key_check: {len(violations)} ihlal")
        else:
            lines.append("YESIL    foreign_key_check: temiz")

        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if version == SCHEMA_VERSION:
            lines.append(f"YESIL    şema sürümü: {version}")
        else:
            ok = False
            lines.append(
                f"KIRMIZI  şema sürümü {version}, beklenen {SCHEMA_VERSION}"
            )

        missing = set(TABLES) - {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if missing:
            ok = False
            lines.append(f"KIRMIZI  eksik tablo: {sorted(missing)}")
            return ok, "\n".join(lines)
        lines.append("YESIL    tablolar eksiksiz")

        counts = _counts(conn)
        lines.append("Satır sayıları:")
        for table, count in counts.items():
            lines.append(f"    {table:<16}{count:>8}")

        # A backup that verifies clean but is empty is the failure mode this
        # tool exists to catch: it looks fine and restores nothing.
        if counts["participants"] == 0 and counts["trials"] == 0:
            lines.append(
                "SARI     yedek boş (katılımcı ve deneme yok) — beklenen bu ise sorun değil"
            )

        if compare_with is not None:
            ok = _compare(compare_with, counts, lines) and ok
    finally:
        conn.close()

    return ok, "\n".join(lines)


def _compare(live_path: Path, counts: dict[str, int], lines: list[str]) -> bool:
    """Compare backup counts against the live database."""
    if not live_path.is_file():
        lines.append(f"KIRMIZI  karşılaştırma hedefi yok: {live_path}")
        return False

    live = sqlite3.connect(f"file:{live_path}?mode=ro", uri=True)
    try:
        live_counts = _counts(live)
    finally:
        live.close()

    lines.append(f"Karşılaştırma: {live_path}")
    ok = True
    for table in TABLES:
        if live_counts[table] == counts[table]:
            lines.append(f"YESIL    {table:<16}{counts[table]:>8} = canlı")
        else:
            # Fewer rows means the backup predates recent writes; more means
            # something is wrong with the live file.  Both need a human.
            ok = False
            lines.append(
                f"KIRMIZI  {table:<16}{counts[table]:>8} ≠ canlı "
                f"{live_counts[table]}"
            )
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_backup", description="Bir veritabanı yedeğini doğrula"
    )
    parser.add_argument("backup", type=Path, help="Doğrulanacak yedek dosyası")
    parser.add_argument(
        "--compare-with",
        type=Path,
        default=None,
        help="Satır sayılarını bu canlı veritabanıyla karşılaştır",
    )
    args = parser.parse_args(argv)

    ok, report = verify(args.backup, args.compare_with)
    print(report)
    print()
    print("SONUÇ: YEDEK KULLANILABİLİR" if ok else "SONUÇ: YEDEK GÜVENİLİR DEĞİL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
