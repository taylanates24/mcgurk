"""Presentation engine — A/V synchronisation core (steps.md §C Adım 3).

Four layers, deliberately separated by what they need in order to run:

``scheduling.py``
    The timing arithmetic.  Pure Python, no PsychoPy, no I/O — which is what
    makes the part that decides when a sound starts testable on a machine with
    no sound card (steps.md §C Adım 3: "sentetik zaman damgalarıyla,
    PsychoPy'sız").
``audio.py``
    Turning a prepared WAV into the samples that are actually played:
    lateralisation and calibration trim.  The array work is pure numpy; only
    the ``sound.Sound`` construction touches PsychoPy, and it imports it
    lazily.
``window.py``
    Window setup, measured refresh rate, frame-interval bookkeeping.
``av_presenter.py``
    ``TrialSpec`` in, ``TimingRecord`` out.  A thin PsychoPy shell over the
    three modules above.

``psychopy_prefs.py`` sits underneath all of them: PsychoPy's audio
preferences only take effect if they are set before ``psychopy.sound`` is
imported, so there is exactly one place that does it.
"""

from __future__ import annotations


class EngineError(RuntimeError):
    """Base class for presentation problems the operator has to act on.

    Everything in this package fails loudly.  A trial that cannot be presented
    with the timing it was asked for is not a trial to be salvaged: the error
    would be invisible in the recorded data.
    """


class AbortSession(Exception):
    """The operator pressed the abort key.

    Not an ``EngineError``: nothing went wrong, the session was stopped on
    purpose.  Callers unwind, mark the session ``aborted`` and exit cleanly.
    """
