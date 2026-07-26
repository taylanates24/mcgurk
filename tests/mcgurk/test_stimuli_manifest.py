"""The manifest: persistence, version gate and lookups.

Adım 3 schedules audio against ``burst_time_s`` and Adım 8's checklist decides
whether a session may start from what is listed here, so a manifest that loads
but means something different is worse than one that fails to load.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcgurk.stimuli import manifest


def _media(name: str) -> manifest.MediaFile:
    return manifest.MediaFile(path=name, sha256="0" * 64, bytes=1)


def _manifest() -> manifest.StimulusManifest:
    return manifest.StimulusManifest(
        created_at=datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        provenance={"git_commit": "abc1234"},
        config={"sample_rate": 48000},
        videos=[
            manifest.VideoEntry(
                speaker_id=1, token="ba", file=_media("video/speaker_1/Vis-ba.mp4"),
                duration_s=2.5, fps=30.0, frame_count=75, width=640, height=480,
                burst_time_s=1.09,
                source=manifest.SourceRef(path="assets/x.mp4", sha256="1" * 64),
            )
        ],
        tokens=[
            manifest.TokenEntry(
                speaker_id=1, visual_token="ba", audio_token="ga",
                file=_media("audio/speaker_1/Vis-ba_Aud-ga.wav"),
                duration_s=2.5, sample_rate=48000, burst_time_s=1.09,
                active_level_dbfs=-23.0, peak_dbfs=-9.4, gain_db=-7.4,
                source=manifest.SourceRef(path="assets/y.mp4", sha256="2" * 64),
            )
        ],
        noisy_tokens=[
            manifest.NoisyTokenEntry(
                speaker_id=1, visual_token="ba", audio_token="ga", snr_db=5.0,
                instance=instance, file=_media(f"audio_noisy/n{instance}.wav"),
                duration_s=2.5, sample_rate=48000, measured_snr_db=5.0,
                peak_dbfs=-8.9,
            )
            for instance in (2, 1)
        ],
        dichotic=[
            manifest.DichoticEntry(
                speaker_id=1, left_token="ba", right_token="da",
                file=_media("dichotic/speaker_1/Left-ba_Right-da.wav"),
                duration_s=2.5, sample_rate=48000, burst_time_s=1.1, peak_dbfs=-9.0,
            )
        ],
        gin_segments=[
            manifest.GinSegmentEntry(
                index=1, file=_media("gin/segment_01.wav"), duration_s=6.0,
                sample_rate=48000, gap_onsets_s=[1.5], gap_durations_ms=[10.0],
                level_dbfs=-23.0,
            )
        ],
        noise=manifest.NoiseEntry(
            file=_media("noise/speech_shaped_noise.wav"), duration_s=30.0,
            sample_rate=48000, max_ltas_deviation_db=0.2,
        ),
    )


def test_round_trip(tmp_path: Path) -> None:
    original = _manifest()
    original.save(tmp_path)
    loaded = manifest.load(tmp_path)

    assert loaded.model_dump() == original.model_dump()
    assert loaded.video(1, "ba").burst_time_s == pytest.approx(1.09)


def test_files_lists_everything(tmp_path: Path) -> None:
    paths = {entry.path for entry in _manifest().files()}
    # 1 video + 1 token + 2 noise instances + 1 dichotic + 1 GIN + the SSN.
    assert len(paths) == 7
    assert "noise/speech_shaped_noise.wav" in paths


def test_noise_instances_come_back_in_order() -> None:
    instances = [entry.instance for entry in _manifest().noisy(1, "ba", "ga", 5.0)]
    assert instances == [1, 2]


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.video(2, "ba"),
        lambda m: m.token(1, "ba", "zz"),
        lambda m: m.noisy(1, "ba", "ga", 99.0),
        lambda m: m.dichotic_pair(1, "ga", "ga"),
    ],
)
def test_a_missing_entry_names_what_was_asked_for(call) -> None:
    with pytest.raises(manifest.ManifestError):
        call(_manifest())


def test_a_missing_manifest_says_how_to_make_one(tmp_path: Path) -> None:
    with pytest.raises(manifest.ManifestError, match="prepare_stimuli"):
        manifest.load(tmp_path)


def test_an_older_manifest_is_refused_rather_than_half_read(tmp_path: Path) -> None:
    data = json.loads(_manifest().model_dump_json())
    data["manifest_version"] = manifest.MANIFEST_VERSION - 1
    (tmp_path / manifest.MANIFEST_NAME).write_text(
        json.dumps(data), encoding="utf-8"
    )
    with pytest.raises(manifest.ManifestError, match="Manifest sürümü"):
        manifest.load(tmp_path)


def test_an_unknown_field_is_an_error(tmp_path: Path) -> None:
    data = json.loads(_manifest().model_dump_json())
    data["videos"][0]["definitely_not_a_field"] = 1
    (tmp_path / manifest.MANIFEST_NAME).write_text(
        json.dumps(data), encoding="utf-8"
    )
    with pytest.raises(manifest.ManifestError):
        manifest.load(tmp_path)


def test_checksums_are_content_based(tmp_path: Path) -> None:
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    assert manifest.sha256(first) == manifest.sha256(second)

    second.write_bytes(b"different")
    assert manifest.sha256(first) != manifest.sha256(second)
