"""Trial specification and the timing record it produces.

No PsychoPy: what is tested here is the contract between the presenter and
everything around it — which combinations of media are a valid trial, and how
a ``TimingRecord`` lands in the database.  The presentation itself needs a
screen and a sound card and is covered by ``tests/test_engine_presentation.py``
(psychopy-marked) and by ``tools/timing_selftest.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcgurk.engine.av_presenter import PresentationError, TimingRecord, TrialSpec

VIDEO = Path("stimuli/video/speaker_1/Vis-ga.mp4")
AUDIO = Path("stimuli/audio/speaker_1/Vis-ga_Aud-ba.wav")


def test_av_trial() -> None:
    spec = TrialSpec(video_path=VIDEO, audio_path=AUDIO, ear="left")
    assert spec.mode == "AV"


def test_audio_only_trial() -> None:
    assert TrialSpec(audio_path=AUDIO).mode == "A"


def test_video_only_trial() -> None:
    assert TrialSpec(video_path=VIDEO).mode == "V"


def test_a_trial_with_nothing_in_it_is_refused() -> None:
    with pytest.raises(PresentationError):
        TrialSpec()


def test_unknown_ear_is_refused() -> None:
    with pytest.raises(PresentationError, match="kulak"):
        TrialSpec(audio_path=AUDIO, ear="middle")


def test_soa_needs_both_modalities_audio_only() -> None:
    """There is no asynchrony between one stream and nothing."""
    with pytest.raises(PresentationError, match="SOA"):
        TrialSpec(audio_path=AUDIO, nominal_soa_ms=100.0)


def test_soa_needs_both_modalities_video_only() -> None:
    with pytest.raises(PresentationError, match="SOA"):
        TrialSpec(video_path=VIDEO, nominal_soa_ms=100.0)


def test_timing_record_maps_onto_the_database_row() -> None:
    record = TimingRecord(
        nominal_soa_ms=-200.0,
        video_onset_s=12.5,
        audio_onset_s=12.3,
        actual_soa_ms=-199.4,
        burst_onset_s=13.4,
        dropped_frames=1,
        max_frame_interval_ms=33.4,
        n_frames=154,
        lead_frames=19,
    )
    timing = record.to_trial_timing()

    assert timing.video_onset_s == 12.5
    assert timing.audio_onset_s == 12.3
    assert timing.actual_soa_ms == -199.4
    assert timing.dropped_frames == 1
    assert timing.max_frame_interval_ms == 33.4
    assert timing.presented_at  # stamped by the model


def test_a_silent_trial_stores_no_soa() -> None:
    """V-only has no audio onset, so there is no asynchrony to record."""
    timing = TimingRecord(video_onset_s=1.0).to_trial_timing()
    assert timing.audio_onset_s is None
    assert timing.actual_soa_ms is None
