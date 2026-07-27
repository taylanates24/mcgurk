"""Fixtures for the mcgurk package tests.

The shipped ``config/experiment.yaml`` is the starting point for every config
test.  Building a synthetic config here instead would let the real one rot
without a single test noticing.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = PROJECT_ROOT / "config" / "experiment.yaml"


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip ``ffmpeg``-marked tests where no ffmpeg binary exists.

    Stimulus preparation is not something CI has to be able to run — it is an
    offline step done once per corpus — but the DSP it is built on is, so only
    the tests that actually shell out are skipped.
    """
    if "ffmpeg" not in item.keywords:
        return
    from mcgurk.stimuli.ffmpeg import FFmpegError, find_ffmpeg

    try:
        find_ffmpeg()
    except FFmpegError as exc:
        pytest.skip(str(exc))

#: Exactly the shape ``kalibrasyon.py hesap`` writes (02_kalibrasyon.md).
CALIBRATION_JSON: dict[str, Any] = {
    "tarih": "2026-07-20T14:30:00",
    "olcum_dbfs": -23.0,
    "spl_sol": 58.2,
    "spl_sag": 57.6,
    "K_sol": 81.2,
    "K_sag": 80.6,
    "K_ortalama": 80.9,
    "kanal_farki_db": 0.6,
    "hedef_spl": 65.0,
    "gereken_dbfs": -15.9,
    "trim_sol_db": -0.3,
    "trim_sag_db": 0.3,
}


@pytest.fixture
def config_dict() -> dict[str, Any]:
    """The shipped configuration as a mutable dictionary."""
    raw = yaml.safe_load(SHIPPED_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return copy.deepcopy(raw)


@pytest.fixture
def write_config(tmp_path: Path):
    """Write a config dictionary to disk and return its path."""

    def _write(data: dict[str, Any], name: str = "experiment.yaml") -> Path:
        path = tmp_path / name
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    return _write


@pytest.fixture
def calibration_data() -> dict[str, Any]:
    return copy.deepcopy(CALIBRATION_JSON)


# ------------------------------------------------------------------- manifest


@pytest.fixture
def manifest_factory() -> Any:
    """Builds a manifest for a given config — see :func:`build_manifest`.

    A factory rather than a manifest, because several tests load a *modified*
    config and need the prepared set to match it.
    """
    return build_manifest


def build_manifest(config: Any) -> Any:
    """A manifest covering everything *config* asks of the prepared set.

    Synthesised rather than read from ``stimuli/``: that directory is
    gitignored and ~70 MB, so a test that needed it would be skipped on CI and
    on any fresh clone — which is exactly where a broken design generator has to
    be caught.  The numbers imitate the real set (77 frames at 30 fps, bursts
    around 1.1 s) because the code reads them, not because they are measured.
    """
    from datetime import datetime

    from mcgurk.stimuli.manifest import (
        MediaFile,
        NoisyTokenEntry,
        SourceRef,
        StimulusManifest,
        TokenEntry,
        ToneEntry,
        VideoEntry,
    )

    def media(path: str) -> MediaFile:
        return MediaFile(path=path, sha256="0" * 64, bytes=1024)

    def source(path: str) -> SourceRef:
        return SourceRef(path=path, sha256="1" * 64, codec="aac", sample_rate=44100)

    tokens = list(config.stimulus_prep.tokens)
    bursts = {token: 1.0 + 0.01 * index for index, token in enumerate(tokens)}
    manifest = StimulusManifest(created_at=datetime(2026, 7, 26, 12, 0, 0))

    for speaker in config.stimulus_prep.speakers:
        for visual in tokens:
            manifest.videos.append(
                VideoEntry(
                    speaker_id=speaker.id,
                    token=visual,
                    file=media(f"video/speaker_{speaker.id}/Vis-{visual}.mp4"),
                    duration_s=2.567,
                    fps=30.0,
                    frame_count=77,
                    width=1920,
                    height=1080,
                    burst_time_s=bursts[visual],
                    source=source(f"assets/speaker_{speaker.id}/Vis-{visual}.mp4"),
                )
            )
            for audio in tokens:
                stem = f"Vis-{visual}_Aud-{audio}"
                manifest.tokens.append(
                    TokenEntry(
                        speaker_id=speaker.id,
                        visual_token=visual,
                        audio_token=audio,
                        file=media(f"audio/speaker_{speaker.id}/{stem}.wav"),
                        duration_s=2.567,
                        sample_rate=config.audio.sample_rate,
                        burst_time_s=bursts[visual],
                        active_level_dbfs=-23.0,
                        peak_dbfs=-6.0,
                        gain_db=1.5,
                        source=source(f"assets/speaker_{speaker.id}/{stem}.mp4"),
                    )
                )
                for snr_db in config.required_snrs():
                    for instance in range(1, config.stimulus_prep.noise.instances + 1):
                        manifest.noisy_tokens.append(
                            NoisyTokenEntry(
                                speaker_id=speaker.id,
                                visual_token=visual,
                                audio_token=audio,
                                snr_db=snr_db,
                                instance=instance,
                                file=media(
                                    f"audio_noisy/speaker_{speaker.id}/"
                                    f"{stem}_ssn{snr_db:g}dB_{instance}.wav"
                                ),
                                duration_s=2.567,
                                sample_rate=config.audio.sample_rate,
                                measured_snr_db=snr_db,
                                peak_dbfs=-3.0,
                            )
                        )

    for frequency in config.required_tones():
        manifest.tones.append(
            ToneEntry(
                frequency_hz=frequency,
                file=media(f"tones/tone_{frequency:g}Hz.wav"),
                duration_s=config.modules.oddball.tone_duration_ms / 1000.0,
                sample_rate=config.audio.sample_rate,
                ramp_ms=config.modules.oddball.tone_ramp_ms,
                level_dbfs=config.stimulus_prep.tones.level_dbfs,
                peak_dbfs=-20.0,
            )
        )
    return manifest


@pytest.fixture
def calibration_file(tmp_path: Path) -> Path:
    path = tmp_path / "kalibrasyon.json"
    path.write_text(
        json.dumps(CALIBRATION_JSON, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path
