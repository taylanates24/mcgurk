"""PsychoPy preferences that must be set before ``psychopy.sound`` is imported.

There is exactly one place that does this because getting the order wrong
fails silently: importing ``psychopy.sound`` first freezes the backend choice,
and a later ``prefs.hardware['audioLib'] = ['ptb']`` is simply ignored.  The
session would then run on whatever backend happened to load, with no way to
schedule audio against a flip time — and nothing in the data would show it.

API note for PsychoPy 2026.1, verified against the installed package:

* Backend selection reads ``prefs.hardware['audioLib']``, but what a caller
  should *check* afterwards is ``sound.Sound.backend`` — ``sound.audioLib`` no
  longer exists (this already bit Adım 0).
* ``prefs.hardware['audioLatencyMode']`` is **gone from the preference spec**.
  The latency class is now a ``SpeakerDevice`` constructor argument and
  defaults to 1, so ``timing.audio_latency_mode`` is applied in
  ``audio.open_speaker`` rather than here.  Setting the old preference key
  would be accepted by configobj and quietly ignored.
"""

from __future__ import annotations

import logging
import os
import sys

from . import EngineError

logger = logging.getLogger(__name__)


def configure_psychopy(*, audio_device: str | None = None) -> None:
    """Pin the audio backend to PTB before any sound module is imported.

    Args:
        audio_device: Exact output device name from ``audio.device``.  ``None``
            leaves the choice to PsychoPy, which is allowed in ``development``
            only — ``data_collection`` requires the name (Adım 1).

    Raises:
        EngineError: if ``psychopy.sound`` was already imported *and* settled on
            a backend other than PTB.  Backend selection happens at import
            time, so at that point this call can no longer change it and the
            only honest thing left to do is stop.  (The device name is read
            later, when the speaker is opened, so setting it is still useful.)
    """
    if "psychopy.sound" in sys.modules:
        from psychopy import sound

        backend = getattr(sound.Sound, "backend", None)
        if backend != "ptb":
            raise EngineError(
                f"psychopy.sound bu çağrıdan önce import edilmiş ve backend "
                f"{backend!r} olarak seçilmiş. Backend seçimi import anında "
                "donuyor, bu çağrı artık düzeltemez. configure_psychopy() "
                "giriş noktasında ilk çağrı olmalı."
            )
        logger.debug(
            "psychopy.sound zaten import edilmiş; backend hâlihazırda ptb, "
            "yalnızca aygıt tercihi güncelleniyor."
        )

    if sys.platform == "win32":
        # MovieStim still touches SDL2 during construction (see CLAUDE.md), and
        # the default driver picks a shared-mode path that adds latency.
        os.environ.setdefault("SDL_AUDIODRIVER", "wasapi")

    from psychopy import prefs

    prefs.hardware["audioLib"] = ["ptb"]
    if audio_device is not None:
        prefs.hardware["audioDevice"] = [audio_device]

    logger.debug(
        "PsychoPy tercihleri ayarlandı: audioLib=['ptb'], audioDevice=%r",
        audio_device,
    )
