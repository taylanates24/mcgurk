"""The stimulus manifest — what was prepared, from what, and how.

Every prepared file is listed with its checksum and the measurements that were
made on it.  Three things depend on this being written down rather than
recomputed: the session checklist (Adım 8) has to be able to say the stimulus
set is complete without decoding anything, the presentation engine (Adım 3)
needs the burst time to schedule audio against the flip clock, and a data set
collected over 12 months has to remain traceable to the exact files it used.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError

from ..config.schema import StrictModel
from . import StimulusError

#: Bumped whenever the shape below changes incompatibly.  A manifest from an
#: older version is refused rather than half-read.
MANIFEST_VERSION = 1

MANIFEST_NAME = "manifest.json"


class ManifestError(StimulusError):
    """The manifest is missing, unreadable, or of an unsupported version."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MediaFile(StrictModel):
    """A prepared file, located relative to the stimulus root."""

    path: str
    sha256: str
    bytes: int

    def resolve(self, root: Path) -> Path:
        return root / self.path


def describe(path: Path, root: Path) -> MediaFile:
    return MediaFile(
        path=path.relative_to(root).as_posix(),
        sha256=sha256(path),
        bytes=path.stat().st_size,
    )


class SourceRef(StrictModel):
    """The raw recording a prepared file came from.

    The codec and sample rate are recorded because they bound what the
    prepared set can be: these sources are 44.1 kHz AAC, so the 48 kHz 24-bit
    output carries no more information than they did.
    """

    path: str
    sha256: str
    codec: str | None = None
    sample_rate: int | None = None
    fps: float | None = None


class VideoEntry(StrictModel):
    """A silent, constant-frame-rate video for one visual token."""

    speaker_id: int
    token: str
    file: MediaFile
    duration_s: float
    fps: float
    frame_count: int
    width: int
    height: int
    #: Where the audio burst sits on this video's timeline.  Every audio file
    #: paired with this video is aligned to it (steps.md §C Adım 2).
    burst_time_s: float
    source: SourceRef


class TokenEntry(StrictModel):
    """One aligned, level-normalised audio file: audio token on a video."""

    speaker_id: int
    visual_token: str
    audio_token: str
    file: MediaFile
    duration_s: float
    sample_rate: int
    #: Measured back from the written file, not the intended value.
    burst_time_s: float
    active_level_dbfs: float
    peak_dbfs: float
    gain_db: float
    source: SourceRef


class NoisyTokenEntry(StrictModel):
    """A token mixed with speech-shaped noise at one SNR."""

    speaker_id: int
    visual_token: str
    audio_token: str
    snr_db: float
    #: Several noise waveforms exist per cell so a repeated trial is not a
    #: repeated noise sample.
    instance: int
    file: MediaFile
    duration_s: float
    sample_rate: int
    measured_snr_db: float
    peak_dbfs: float


class DichoticEntry(StrictModel):
    """A stereo file with a different token in each ear."""

    speaker_id: int
    left_token: str
    right_token: str
    file: MediaFile
    duration_s: float
    sample_rate: int
    #: Both ears are aligned to the same burst time: an ear advantage measured
    #: with asynchronous onsets would partly be an onset effect.
    burst_time_s: float
    peak_dbfs: float


class GinSegmentEntry(StrictModel):
    """One GIN noise segment and the gaps cut into it."""

    index: int
    file: MediaFile
    duration_s: float
    sample_rate: int
    gap_onsets_s: list[float]
    gap_durations_ms: list[float]
    level_dbfs: float


class ToneEntry(StrictModel):
    """One pure tone of the oddball module (Adım 7).

    Prepared offline like everything else that is presented: the ramp that keeps
    a 50 ms tone from clicking is exactly the kind of thing that has to be
    measurable off the disk, and ``verify_stimuli.py`` measures it.
    """

    frequency_hz: float
    file: MediaFile
    duration_s: float
    sample_rate: int
    ramp_ms: float
    #: RMS of the whole file, ramps included.
    level_dbfs: float
    peak_dbfs: float


class ThumbnailEntry(StrictModel):
    """One still of a speaker's face, for the operator's session menu.

    Never presented to a participant — it is how the operator recognises who
    "konuşmacı 5" is.  It lives in the prepared set rather than being grabbed at
    run time because a session must not shell out to ffmpeg (§A.12), and because
    a picture of the wrong person is exactly the kind of mistake a manifest and
    a checksum exist to catch.
    """

    speaker_id: int
    file: MediaFile
    #: The prepared video it was taken from, and where in it.
    source_token: str
    time_s: float
    width: int
    height: int


class NoiseEntry(StrictModel):
    """The speech-shaped noise master the noisy tokens are drawn from."""

    file: MediaFile
    duration_s: float
    sample_rate: int
    #: Largest third-octave deviation from the corpus LTAS.
    max_ltas_deviation_db: float


class StimulusManifest(StrictModel):
    manifest_version: int = MANIFEST_VERSION
    created_at: datetime
    #: Commit, interpreter and OS the set was built on.
    provenance: dict[str, str | None] = Field(default_factory=dict)
    #: The ``stimulus_prep`` section as it was when this ran, plus the sample
    #: rate and the SNRs derived from the enabled modules.
    config: dict[str, Any] = Field(default_factory=dict)
    videos: list[VideoEntry] = Field(default_factory=list)
    tokens: list[TokenEntry] = Field(default_factory=list)
    noisy_tokens: list[NoisyTokenEntry] = Field(default_factory=list)
    dichotic: list[DichoticEntry] = Field(default_factory=list)
    gin_segments: list[GinSegmentEntry] = Field(default_factory=list)
    #: Added in Adım 7.  The version is deliberately *not* bumped: an older
    #: manifest simply has no tones, and the oddball design says so by name
    #: rather than being refused wholesale — the same treatment as an AVSR word
    #: set that has not been recorded yet.
    tones: list[ToneEntry] = Field(default_factory=list)
    #: Added in Adım 12c-ii, and like ``tones`` without a version bump: an older
    #: set simply has none, and the menu falls back to text rather than refusing
    #: to open.
    thumbnails: list[ThumbnailEntry] = Field(default_factory=list)
    noise: NoiseEntry | None = None

    # -- lookups ----------------------------------------------------------

    def thumbnail(self, speaker_id: int) -> ThumbnailEntry | None:
        """The speaker's still, or None if this set was built without them."""
        for entry in self.thumbnails:
            if entry.speaker_id == speaker_id:
                return entry
        return None

    def video(self, speaker_id: int, token: str) -> VideoEntry:
        for entry in self.videos:
            if entry.speaker_id == speaker_id and entry.token == token:
                return entry
        raise ManifestError(
            f"Manifest'te video yok: konuşmacı {speaker_id}, token {token!r}"
        )

    def token(self, speaker_id: int, visual: str, audio: str) -> TokenEntry:
        for entry in self.tokens:
            if (
                entry.speaker_id == speaker_id
                and entry.visual_token == visual
                and entry.audio_token == audio
            ):
                return entry
        raise ManifestError(
            f"Manifest'te ses yok: konuşmacı {speaker_id}, Vis-{visual}/Aud-{audio}"
        )

    def noisy(
        self, speaker_id: int, visual: str, audio: str, snr_db: float
    ) -> list[NoisyTokenEntry]:
        """All noise instances for one cell, in instance order."""
        found = [
            entry
            for entry in self.noisy_tokens
            if entry.speaker_id == speaker_id
            and entry.visual_token == visual
            and entry.audio_token == audio
            and entry.snr_db == snr_db
        ]
        if not found:
            raise ManifestError(
                f"Manifest'te gürültülü ses yok: konuşmacı {speaker_id}, "
                f"Vis-{visual}/Aud-{audio}, SNR {snr_db} dB"
            )
        return sorted(found, key=lambda entry: entry.instance)

    def dichotic_pair(self, speaker_id: int, left: str, right: str) -> DichoticEntry:
        for entry in self.dichotic:
            if (
                entry.speaker_id == speaker_id
                and entry.left_token == left
                and entry.right_token == right
            ):
                return entry
        raise ManifestError(
            f"Manifest'te dikotik dosya yok: konuşmacı {speaker_id}, "
            f"Left-{left}/Right-{right}"
        )

    def tone(self, frequency_hz: float) -> ToneEntry:
        for entry in self.tones:
            if entry.frequency_hz == frequency_hz:
                return entry
        raise ManifestError(
            f"Manifest'te {frequency_hz:g} Hz tonu yok. Uyaran seti bu tasarımla "
            "hazırlanmamış: python tools/prepare_stimuli.py --force"
        )

    def files(self) -> list[MediaFile]:
        """Every prepared file the manifest refers to."""
        entries: list[MediaFile] = [entry.file for entry in self.videos]
        entries += [entry.file for entry in self.tokens]
        entries += [entry.file for entry in self.noisy_tokens]
        entries += [entry.file for entry in self.dichotic]
        entries += [entry.file for entry in self.gin_segments]
        entries += [entry.file for entry in self.tones]
        entries += [entry.file for entry in self.thumbnails]
        if self.noise is not None:
            entries.append(self.noise.file)
        return entries

    # -- persistence ------------------------------------------------------

    def save(self, root: Path) -> Path:
        path = root / MANIFEST_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2, exclude_none=False), encoding="utf-8"
        )
        return path


def load(root: Path) -> StimulusManifest:
    """Read the manifest under *root*.

    Args:
        root: The stimulus directory (``paths.stimuli``), not the file itself.
    """
    path = root / MANIFEST_NAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(
            f"Uyaran manifest'i okunamadı: {path} ({exc})\n"
            "Uyaranlar hazırlanmamış olabilir: python tools/prepare_stimuli.py"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Uyaran manifest'i geçerli JSON değil: {path}\n{exc}") from exc

    version = raw.get("manifest_version")
    if version != MANIFEST_VERSION:
        raise ManifestError(
            f"Manifest sürümü {version}, beklenen {MANIFEST_VERSION}: {path}. "
            "Uyaran setini yeniden hazırlayın."
        )
    try:
        return StimulusManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"Manifest doğrulanamadı: {path}\n{exc}") from exc
