"""Export the database to flat files for analysis.

Two artifacts:

* **``trials_flat``** — the ``v_trials_flat`` view, one row per (trial, response),
  which is the table every downstream analysis reads.  The module-specific
  design fields it hides in ``trials.design_extra`` are exposed as columns here
  (§ schema notes), so the analyst never touches JSON.
* **the raw tables** — ``participants`` … ``responses`` — a faithful dump for
  audit, so the export can be reconstructed into a database if the file is lost.

Formats: **CSV is always written**; **parquet only when ``pyarrow`` is
installed**.  Parquet keeps column types and the difference between NULL and an
empty string — which matters here, where ``is_correct`` NULL means "no correct
answer" and an empty ``free_text`` means the participant typed nothing — but it
is a ~100 MB dependency, so it is optional rather than required.  A parquet
request with no ``pyarrow`` present is logged and skipped, never an error.
"""

from __future__ import annotations

import importlib.util
import logging
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path

import pandas as pd

from ..db.database import Database

logger = logging.getLogger(__name__)

#: The raw tables, in dependency order (a participant before their sessions).
#: A fixed allow-list: the table name goes into SQL, so it is never taken from
#: the caller.
TABLES: tuple[str, ...] = (
    "participants",
    "calibrations",
    "sessions",
    "blocks",
    "trials",
    "responses",
)

#: The formats a caller may ask for.  CSV always works; parquet needs pyarrow.
FORMATS: tuple[str, ...] = ("csv", "parquet")


class ExportError(RuntimeError):
    """Raised for an export request that cannot be honoured (bad format/path)."""


def parquet_available() -> bool:
    """Whether parquet can be written — i.e. whether ``pyarrow`` is importable."""
    return importlib.util.find_spec("pyarrow") is not None


def _query_frame(
    conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()
) -> pd.DataFrame:
    """Run *sql* into a DataFrame, keeping the column names even for 0 rows.

    Built from the cursor rather than :func:`pandas.read_sql_query` on purpose:
    read_sql warns about a non-SQLAlchemy connection and would pull SQLAlchemy
    in as a dependency, and an empty result there loses the column headers.
    """
    cursor = conn.execute(sql, tuple(params))
    columns = [description[0] for description in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=columns)


def read_flat(db: Database, session_id: int | None = None) -> pd.DataFrame:
    """The ``v_trials_flat`` view as a DataFrame, optionally for one session."""
    if session_id is None:
        return _query_frame(
            db.conn,
            "SELECT * FROM v_trials_flat ORDER BY trial_id, response_index",
        )
    return _query_frame(
        db.conn,
        "SELECT * FROM v_trials_flat WHERE session_id = ? "
        "ORDER BY trial_id, response_index",
        (session_id,),
    )


def read_table(db: Database, table: str) -> pd.DataFrame:
    """One raw table as a DataFrame.  *table* must be a known table name."""
    if table not in TABLES:
        raise ExportError(f"Bilinmeyen tablo: {table!r}")
    return _query_frame(db.conn, f"SELECT * FROM {table}")


def _normalise_formats(formats: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(formats))  # de-duplicate, keep order
    unknown = [fmt for fmt in requested if fmt not in FORMATS]
    if unknown:
        raise ExportError(
            f"Bilinmeyen biçim: {unknown}. Desteklenen: {list(FORMATS)}"
        )
    if not requested:
        raise ExportError("En az bir biçim gerekli (csv veya parquet).")
    return requested


def write_frame(
    frame: pd.DataFrame, stem: Path, formats: Iterable[str] = ("csv",)
) -> list[Path]:
    """Write *frame* to ``stem.csv`` and/or ``stem.parquet``.

    Returns the paths actually written.  A parquet request is silently downgraded
    to a warning when pyarrow is missing, so a caller that asked for both still
    gets its CSV.
    """
    requested = _normalise_formats(formats)
    stem.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if "csv" in requested:
        csv_path = stem.with_suffix(".csv")
        # utf-8 (no BOM): the study's analysis tools (pandas, R) read it
        # directly; the Turkish text in free_text/notes survives round-trip.
        frame.to_csv(csv_path, index=False, encoding="utf-8")
        written.append(csv_path)

    if "parquet" in requested:
        if parquet_available():
            parquet_path = stem.with_suffix(".parquet")
            frame.to_parquet(parquet_path, index=False)
            written.append(parquet_path)
        else:
            logger.warning(
                "parquet atlandı (%s): pyarrow kurulu değil — "
                "'pip install pyarrow' ile etkinleşir.",
                stem.name,
            )
    return written


def export_database(
    db: Database,
    out_dir: Path | str,
    *,
    session_id: int | None = None,
    formats: Iterable[str] = ("csv",),
    include_tables: bool = True,
) -> list[Path]:
    """Export the flat view and, for a whole-database export, the raw tables.

    * ``session_id`` set — only that session's flat rows are written; the raw
      tables are skipped, since they would hold the whole database and not match.
    * ``session_id`` None — the flat view and every raw table are written.

    Returns the paths written, CSV first then parquet within each artifact.
    """
    requested = _normalise_formats(formats)
    out_path = Path(out_dir)
    written: list[Path] = []

    flat = read_flat(db, session_id)
    written += write_frame(flat, out_path / "trials_flat", requested)

    if session_id is None and include_tables:
        for table in TABLES:
            written += write_frame(read_table(db, table), out_path / table, requested)

    logger.info("Dışa aktarım tamamlandı: %d dosya -> %s", len(written), out_path)
    return written
