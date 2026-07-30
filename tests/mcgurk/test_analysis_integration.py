"""Adım 9b — end-to-end: a fake participant through every module, then export,
measures and QC, all the way from the database to the analysis output.

This is the automated end-to-end gate of steps.md Adım 9 (the *prova* session
with a real person is Adım 9c).  It does not re-check each module's numbers —
that is each module's own test — but that a session touching every module can be
exported, measured and QC'd without crashing, and that nothing is silently
dropped along the way.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from mcgurk.analysis.export import export_database, read_flat
from mcgurk.analysis.measures import session_measures
from mcgurk.analysis.qc_report import session_qc
from mcgurk.config.loader import load_config
from mcgurk.db import Block, Database, Participant, Response, SessionRecord, Trial
from mcgurk.db.models import TrialTiming


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


def _block(db: Database, session_id: int, module: str) -> int:
    return db.add_block(
        Block(session_id=session_id, module=module,
              block_index=db.next_block_index(session_id), n_trials_planned=0)
    )


def _populate_all_modules(db: Database, config: Any) -> int:
    """One participant, one session, a few trials in every module."""
    pid = db.add_participant(
        Participant(participant_code="FULL01", group_code="SSD_R", age=45, sex="M")
    )
    sid = db.start_session(SessionRecord(
        participant_id=pid, seed=11,
        config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
        config_mode="development", python_version="3.10", os_name="win",
    ))

    # practice
    pb = _block(db, sid, "practice")
    pt = db.add_trial(Trial(block_id=pb, trial_index=0, module="practice",
                            visual_token="ba", audio_token="ba", ear="left"))
    db.add_response(Response(trial_id=pt, raw_response="ba"))
    db.finish_block(pb, status="completed")

    # mcgurk
    mb = _block(db, sid, "mcgurk")
    for i, (v, a, cat) in enumerate([("ga", "ba", "FUSION"), ("ba", "ba", "AUDITORY")]):
        t = db.add_trial(Trial(block_id=mb, trial_index=i, module="mcgurk",
                               visual_token=v, audio_token=a, ear="left",
                               nominal_soa_ms=0.0, design_extra={"speaker_id": 1}))
        db.set_trial_timing(t, TrialTiming(actual_soa_ms=1.0, dropped_frames=0))
        db.add_response(Response(trial_id=t, raw_response=cat.lower(), category=cat,
                                 rt_from_burst_ms=500.0))
    db.finish_block(mb, status="completed")

    # avsr (AV correct, A incorrect, V correct)
    ab = _block(db, sid, "avsr")
    for i, (mode, correct) in enumerate([("AV", True), ("A", False), ("V", True)]):
        t = db.add_trial(Trial(block_id=ab, trial_index=i, module="avsr",
                               audio_token=None if mode == "V" else "ba",
                               presentation_mode=mode, ear=None if mode == "V" else "left",
                               design_extra={"speaker_id": 1, "stimulus_type": "syllable",
                                             "item": "ba"}))
        db.add_response(Response(trial_id=t, raw_response="ba", is_correct=correct))
    db.finish_block(ab, status="completed")

    # tbw (a few SOA points; the fit may or may not succeed — both are tolerated)
    tb = _block(db, sid, "tbw")
    for i, (soa, cat) in enumerate([(-100.0, "DIFFERENT"), (0.0, "SAME"), (100.0, "DIFFERENT")]):
        t = db.add_trial(Trial(block_id=tb, trial_index=i, module="tbw",
                               visual_token="ba", audio_token="ba", ear="both",
                               nominal_soa_ms=soa, design_extra={"speaker_id": 1}))
        db.set_trial_timing(t, TrialTiming(actual_soa_ms=soa + 1.0))
        db.add_response(Response(trial_id=t, raw_response=cat, category=cat))
    db.finish_block(tb, status="completed")

    # oddball (1 target hit, 2 standards -> a valid d')
    ob = _block(db, sid, "oddball")
    tg = db.add_trial(Trial(block_id=ob, trial_index=0, module="oddball",
                            design_extra={"tone_type": "target", "tone_hz": 1500.0}))
    db.add_response(
        Response(trial_id=tg, raw_response="space", category="HIT", rt_from_burst_ms=400.0)
    )
    for i in range(1, 3):
        db.add_trial(Trial(block_id=ob, trial_index=i, module="oddball",
                           design_extra={"tone_type": "standard", "tone_hz": 1000.0}))
    db.finish_block(ob, status="completed")

    # dichotic
    db_ = _block(db, sid, "dichotic")
    for i, (left, right, cat) in enumerate([("ba", "ga", "LEFT"), ("da", "ba", "RIGHT")]):
        t = db.add_trial(Trial(block_id=db_, trial_index=i, module="dichotic", ear="both",
                               design_extra={"speaker_id": 1, "left_token": left,
                                             "right_token": right}))
        db.add_response(Response(trial_id=t, raw_response=left, category=cat))
    db.finish_block(db_, status="completed")

    # gin (one segment, one gap detected)
    gb = _block(db, sid, "gin")
    gt = db.add_trial(Trial(block_id=gb, trial_index=0, module="gin", ear="right",
                            presentation_mode="A",
                            design_extra={"segment_index": 3, "gap_onsets_s": [1.5],
                                          "gap_durations_ms": [8.0]}))
    db.add_response(Response(trial_id=gt, event_index=0, raw_response="space",
                             category="HIT", rt_from_burst_ms=300.0))
    db.finish_block(gb, status="completed")

    # cross_hearing (signal hit + catch correct rejection)
    cb = _block(db, sid, "cross_hearing")
    ct = db.add_trial(Trial(block_id=cb, trial_index=0, module="cross_hearing",
                            ear="right", design_extra={"signal_present": True}))
    db.add_response(Response(trial_id=ct, raw_response="space", category="HIT"))
    db.add_trial(Trial(block_id=cb, trial_index=1, module="cross_hearing",
                       ear="right", design_extra={"signal_present": False}))
    db.finish_block(cb, status="completed")
    return sid


def test_a_full_session_exports_measures_and_qcs(
    db: Database, config: Any, tmp_path: Path
) -> None:
    session_id = _populate_all_modules(db, config)

    # export
    out = tmp_path / "export"
    written = export_database(db, out, formats=("csv",))
    assert written  # flat view + every raw table
    assert (out / "trials_flat.csv").is_file()
    flat = pd.read_csv(out / "trials_flat.csv")
    # 1 practice + 2 mcgurk + 3 avsr + 3 tbw + 3 oddball + 2 dichotic + 1 gin
    # + 2 cross_hearing = 17 trials; the LEFT JOIN gives one row per trial here
    # (no trial has more than one response).
    assert len(flat) == 17
    assert "cross_hearing_signal_present" in flat.columns

    # measures — the six measurement modules are all present
    measures = session_measures(db, session_id)
    measured = {m.module for m in measures.modules}
    assert measured == {"mcgurk", "avsr", "tbw", "oddball", "dichotic", "gin"}
    for measure in measures.modules:
        assert measure.summary  # every module produced a console block
    measures.summary_text().encode("cp1254")

    # qc — timing, modules, cross-hearing all assembled
    qc = session_qc(db, session_id)
    assert qc.cross_hearing is not None
    assert qc.cross_hearing.hits == 1
    qc_modules = {m.module for m in qc.modules}
    assert "practice" in qc_modules and "cross_hearing" in qc_modules
    qc.summary_text().encode("cp1254")


def test_reading_an_empty_session_does_not_crash(db: Database, config: Any) -> None:
    """A session that aborted before any trial still has to export, measure and
    QC cleanly — an empty result, not an exception."""
    pid = db.add_participant(
        Participant(participant_code="EMPTY", group_code="CTRL", age=25, sex="F")
    )
    sid = db.start_session(SessionRecord(
        participant_id=pid, seed=1,
        config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
        config_mode="development", python_version="3.10", os_name="win",
    ))
    assert read_flat(db, sid).empty
    assert session_measures(db, sid).modules == ()
    report = session_qc(db, sid)
    assert report.timing.n_trials == 0
    assert report.cross_hearing is None
