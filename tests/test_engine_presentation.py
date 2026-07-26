"""End-to-end presentation on real hardware.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.
What it can assert is *structural* — that an onset was measured, that the audio
went where it was asked to go, that the video really ran to its end.  It
deliberately does not assert tight timing: this runs in a small non-fullscreen
window, where vsync is not guaranteed.  Timing quality is what
``tools/timing_selftest.py`` levels 1 and 2 are for, and they need an operator.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import load_config, resolve_path
from mcgurk.config.schema import DisplayConfig
from mcgurk.engine import EngineError
from mcgurk.engine.av_presenter import AVPresenter, TrialSpec
from mcgurk.engine.psychopy_prefs import configure_psychopy
from mcgurk.engine.scheduling import TimingParams
from mcgurk.engine.window import make_fixation, measure_refresh_hz, open_window
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def config() -> Any:
    return load_config(project_root=PROJECT_ROOT)


@pytest.fixture(scope="module")
def manifest(config: Any) -> Any:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    try:
        return manifest_module.load(root)
    except Exception as exc:  # noqa: BLE001 - any failure means "not prepared"
        pytest.skip(f"Hazırlanmış uyaran seti yok: {exc}")


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    """The session's shared device — see ``tests/conftest.py``."""
    return hardware_speaker


@pytest.fixture(scope="module")
def windowed(config: Any) -> Iterator[Any]:
    """A small window: a fullscreen one would take over the operator's screen."""
    display = DisplayConfig(
        fullscreen=False,
        screen=config.display.screen,
        size=(640, 480),
        background=config.display.background,
        expected_refresh_hz=config.display.expected_refresh_hz,
    )
    win = open_window(display, mouse_visible=True)
    try:
        yield win
    finally:
        win.close()


@pytest.fixture(scope="module")
def presenter(config: Any, windowed: Any, speaker: Any) -> AVPresenter:
    refresh_hz = measure_refresh_hz(windowed)
    params = TimingParams(
        frame_period_s=1.0 / refresh_hz,
        lead_frames=config.timing.lead_frames,
        system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
        dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
    )
    return AVPresenter(
        windowed,
        params,
        speaker=speaker,
        sample_rate=config.audio.sample_rate,
        alignment_tolerance_ms=config.stimulus_prep.burst.alignment_tolerance_ms,
        fixation=make_fixation(windowed),
    )


def _spec(manifest: Any, root: Path, **overrides: Any) -> TrialSpec:
    video = manifest.video(1, "ba")
    token = manifest.token(1, "ba", "ba")
    fields: dict[str, Any] = {
        "video_path": video.file.resolve(root),
        "video_burst_s": video.burst_time_s,
        "audio_path": token.file.resolve(root),
        "audio_burst_s": token.burst_time_s,
        "ear": "both",
    }
    fields.update(overrides)
    return TrialSpec(**fields)


def test_configure_psychopy_refuses_a_backend_it_can_no_longer_change(
    speaker: Any,
) -> None:
    """Backend selection freezes when ``psychopy.sound`` is imported.

    Called too late *and* on the wrong backend, this cannot fix anything, and
    the failure it would otherwise hide is silent: the session runs on whatever
    loaded first and no data shows it.  Called too late on the right backend it
    is harmless, which is the other half of this test.
    """
    from psychopy import sound

    assert "psychopy.sound" in sys.modules  # the speaker fixture imported it
    configure_psychopy()  # already ptb — nothing to fix, must not raise

    original = sound.Sound.backend
    sound.Sound.backend = "pygame"
    try:
        with pytest.raises(EngineError, match="donuyor"):
            configure_psychopy()
    finally:
        sound.Sound.backend = original


def test_backend_is_ptb(speaker: Any) -> None:
    from psychopy import sound

    assert sound.Sound.backend == "ptb"


def test_a_device_that_is_not_there_is_an_operator_facing_error(config: Any) -> None:
    """A named device that is absent — a Bluetooth headset switched off, say —
    must produce the engine's own message, not a PsychoPy traceback.

    PsychoPy 2026.1 raises ``DeviceNotConnectedError``, which derives from
    ``BaseException``: before it was caught by name, it escaped ``open_speaker``
    *and* every ``except Exception`` above it.

    Deliberately independent of the ``speaker`` fixture: this test is about the
    device *not* being there, so requiring a working one would make it skip on
    exactly the machine state it describes.
    """
    from mcgurk.engine.audio import AudioError, open_speaker

    configure_psychopy(audio_device=config.audio.device)

    with pytest.raises(AudioError, match="Ses aygıtı açılamadı"):
        open_speaker(
            device_name="Boyle Bir Ses Aygiti Yok",
            latency_class=config.timing.audio_latency_mode,
            sample_rate=config.audio.sample_rate,
        )


def test_av_trial_records_both_onsets(
    presenter: AVPresenter, manifest: Any, config: Any
) -> None:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    prepared = presenter.prepare(_spec(manifest, root))
    try:
        record = presenter.present(prepared)
    finally:
        presenter.release(prepared)

    assert record.video_onset_s is not None
    assert record.audio_onset_s is not None
    assert record.actual_soa_ms is not None
    assert record.burst_onset_s is not None
    # The prepared pair is aligned to well under a millisecond (Adım 2).
    assert abs(record.alignment_error_ms or 0.0) < 1.0
    # The video was played from its first frame, not from wherever the decoder
    # happened to be.
    assert (record.first_frame_pts_s or 0.0) < 0.1
    # It ran for its own duration rather than a fixed one.
    assert record.n_frames > 30


def test_negative_soa_starts_the_audio_first(
    presenter: AVPresenter, manifest: Any, config: Any
) -> None:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    prepared = presenter.prepare(_spec(manifest, root, nominal_soa_ms=-200.0))
    try:
        record = presenter.present(prepared)
    finally:
        presenter.release(prepared)

    assert record.audio_onset_s is not None and record.video_onset_s is not None
    assert record.audio_onset_s < record.video_onset_s
    # The lead had to grow past the configured six frames to make room.
    assert record.lead_frames > config.timing.lead_frames
    assert record.actual_soa_ms == pytest.approx(-200.0, abs=20.0)


def test_audio_only_trial_has_no_video_onset(
    presenter: AVPresenter, manifest: Any, config: Any
) -> None:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    token = manifest.token(1, "ba", "ba")
    spec = TrialSpec(
        audio_path=token.file.resolve(root),
        audio_burst_s=token.burst_time_s,
        ear="right",
    )
    prepared = presenter.prepare(spec)
    try:
        record = presenter.present(prepared)
    finally:
        presenter.release(prepared)

    assert record.video_onset_s is None
    assert record.actual_soa_ms is None
    assert record.audio_onset_s is not None
    assert record.duration_s == pytest.approx(prepared.audio_duration_s)


def test_video_only_trial_makes_no_sound(
    presenter: AVPresenter, manifest: Any, config: Any
) -> None:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    video = manifest.video(1, "ga")
    spec = TrialSpec(video_path=video.file.resolve(root), video_burst_s=video.burst_time_s)
    prepared = presenter.prepare(spec)
    assert prepared.sound is None
    try:
        record = presenter.present(prepared)
    finally:
        presenter.release(prepared)

    assert record.audio_onset_s is None
    assert record.video_onset_s is not None
