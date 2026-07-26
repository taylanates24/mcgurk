"""WAV reading and writing.

``soundfile`` rather than ``scipy.io.wavfile`` because the prepared corpus is
24-bit PCM (config ``stimulus_prep.audio.bit_depth``) and scipy can only write
16- or 32-bit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from . import StimulusError

#: ``bit_depth`` in the config -> libsndfile subtype.
_SUBTYPES = {16: "PCM_16", 24: "PCM_24"}


class WavError(StimulusError):
    """A WAV file could not be read or written."""


def read(path: Path) -> tuple[np.ndarray, int]:
    """Read *path* as float64 samples in [-1, 1] plus its sample rate.

    Shape is ``(n,)`` for mono and ``(n, channels)`` otherwise — the same
    convention soundfile uses.
    """
    try:
        data, sample_rate = sf.read(str(path), dtype="float64", always_2d=False)
    except (OSError, RuntimeError) as exc:
        raise WavError(f"WAV okunamadı: {path} ({exc})") from exc
    return np.asarray(data, dtype=np.float64), int(sample_rate)


def write(path: Path, data: np.ndarray, sample_rate: int, *, bit_depth: int) -> None:
    """Write *data* to *path* as PCM at *bit_depth*.

    Clipping is an error rather than something to be silently limited: a
    normalised token that clips means the level or the SNR calculation is
    wrong, and a limiter would hide it.
    """
    subtype = _SUBTYPES.get(bit_depth)
    if subtype is None:
        raise WavError(f"Desteklenmeyen bit derinliği: {bit_depth}")

    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak > 1.0:
        raise WavError(
            f"Örnekler [-1, 1] aralığını aşıyor (tepe {peak:.4f}): {path}. "
            "Seviye normalizasyonu veya gürültü karışımı hatalı."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write(str(path), data, sample_rate, subtype=subtype)
    except (OSError, RuntimeError) as exc:
        raise WavError(f"WAV yazılamadı: {path} ({exc})") from exc
