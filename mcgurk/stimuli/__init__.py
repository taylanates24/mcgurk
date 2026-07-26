"""Offline stimulus preparation and verification (steps.md §C Adım 2).

Nothing in this package runs during a trial.  §A.12 forbids resampling or
heavy DSP at run time, so every transformation the experiment needs — frame
rate conversion, burst alignment, level normalisation, noise mixing, GIN gap
placement — happens here and is written to ``paths.stimuli`` with a manifest.

Like ``config/`` and ``db/``, this layer must stay importable without PsychoPy:
stimuli get prepared on whatever machine has ffmpeg, not necessarily on the
one that runs sessions.
"""

from __future__ import annotations

__all__ = ["StimulusError"]


class StimulusError(RuntimeError):
    """Any failure in preparing or verifying the stimulus set.

    Preparation never degrades silently (steps.md §C Adım 2: "tolerans dışında
    hata verip çık") — a stimulus that is a little bit wrong produces data that
    looks fine and means nothing.
    """
