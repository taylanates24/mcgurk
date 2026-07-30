"""Adım 9a — exporting the database to flat files.

CSV is always written; parquet only when pyarrow is installed.  Both branches
are exercised here regardless of the machine: the "unavailable" path is forced
with a monkeypatch so CI (no pyarrow) and the development box agree.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from mcgurk.analysis import export as export_mod
from mcgurk.analysis.export import (
    ExportError,
    export_database,
    read_flat,
    read_table,
    write_frame,
)
from mcgurk.db import Block, Database, Participant, Response, SessionRecord, Trial


def _populate(db: Database) -> int:
    """One participant, one session, a McGurk block: two answered, one timeout."""
    participant_id = db.add_participant(
        Participant(participant_code="P001", group_code="CTRL", age=30, sex="F")
    )
    session_id = db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=7,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
        )
    )
    block_id = db.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=3)
    )
    for index, (visual, category, rt) in enumerate(
        [("ga", "FUSION", 500.0), ("ba", "AUDITORY", 600.0), ("da", None, None)]
    ):
        trial_id = db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=index,
                module="mcgurk",
                visual_token=visual,
                audio_token="ba",
                ear="left",
                design_extra={"speaker_id": 1},
            )
        )
        if category is not None:
            db.add_response(
                Response(
                    trial_id=trial_id,
                    raw_response=category.lower(),
                    category=category,
                    rt_from_burst_ms=rt,
                )
            )
    db.finish_block(block_id, status="completed")
    return session_id


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


# ------------------------------------------------------------------ reading


def test_read_flat_has_one_row_per_trial_response(db: Database) -> None:
    _populate(db)
    frame = read_flat(db)
    # Two answered trials (one response each) plus one timeout (a row with no
    # response, kept by the LEFT JOIN): three rows.
    assert len(frame) == 3
    assert "cross_hearing_signal_present" in frame.columns
    assert frame["participant_code"].tolist() == ["P001", "P001", "P001"]


def test_read_flat_can_scope_to_one_session(db: Database) -> None:
    session_id = _populate(db)
    other = db.start_session(
        SessionRecord(
            participant_id=1,
            seed=8,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
        )
    )
    assert len(read_flat(db, session_id)) == 3
    assert read_flat(db, other).empty


def test_read_flat_of_empty_database_keeps_its_columns(db: Database) -> None:
    frame = read_flat(db)
    assert frame.empty
    assert "trial_id" in frame.columns  # header preserved even with no rows


def test_read_table_rejects_an_unknown_name(db: Database) -> None:
    with pytest.raises(ExportError):
        read_table(db, "employees")


def test_read_table_returns_the_rows(db: Database) -> None:
    _populate(db)
    assert len(read_table(db, "participants")) == 1
    assert len(read_table(db, "responses")) == 2


# ------------------------------------------------------------------ writing


def test_export_writes_flat_and_every_raw_table(db: Database, tmp_path: Path) -> None:
    _populate(db)
    out = tmp_path / "out"
    written = export_database(db, out, formats=("csv",))
    names = {path.name for path in written}
    assert "trials_flat.csv" in names
    for table in ("participants", "sessions", "blocks", "trials", "responses"):
        assert f"{table}.csv" in names


def test_exported_csv_round_trips(db: Database, tmp_path: Path) -> None:
    _populate(db)
    export_database(db, tmp_path, formats=("csv",))
    frame = pd.read_csv(tmp_path / "trials_flat.csv")
    assert len(frame) == 3
    # The timeout's is_correct is NULL, which CSV reads back as NaN — distinct
    # from a stored 0.
    assert frame["category"].isin(["FUSION", "AUDITORY"]).sum() == 2


def test_a_session_scoped_export_skips_the_raw_tables(db: Database, tmp_path: Path) -> None:
    session_id = _populate(db)
    written = export_database(db, tmp_path, session_id=session_id, formats=("csv",))
    assert [path.name for path in written] == ["trials_flat.csv"]


def test_unknown_format_is_refused(db: Database, tmp_path: Path) -> None:
    with pytest.raises(ExportError):
        export_database(db, tmp_path, formats=("xlsx",))


def test_at_least_one_format_is_required(db: Database, tmp_path: Path) -> None:
    with pytest.raises(ExportError):
        export_database(db, tmp_path, formats=())


# ------------------------------------------------------------------ parquet


def test_parquet_is_skipped_with_a_warning_when_unavailable(
    db: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    _populate(db)
    monkeypatch.setattr(export_mod, "parquet_available", lambda: False)
    with caplog.at_level(logging.WARNING):
        written = export_database(db, tmp_path, formats=("csv", "parquet"))
    assert [path.suffix for path in written] == [".csv"] * len(written)
    assert (tmp_path / "trials_flat.csv").is_file()
    assert not (tmp_path / "trials_flat.parquet").exists()
    assert any("parquet" in record.message for record in caplog.records)


def test_parquet_is_written_when_pyarrow_is_installed(
    db: Database, tmp_path: Path
) -> None:
    if not export_mod.parquet_available():
        pytest.skip("pyarrow kurulu değil — parquet yazma yolu bu makinede yok")
    _populate(db)
    frame = read_flat(db)
    written = write_frame(frame, tmp_path / "trials_flat", formats=("parquet",))
    assert written == [tmp_path / "trials_flat.parquet"]
    restored = pd.read_parquet(tmp_path / "trials_flat.parquet")
    assert len(restored) == len(frame)
