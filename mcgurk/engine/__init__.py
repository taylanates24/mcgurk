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

from collections.abc import Callable


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


#: Optional confirmation asked before an abort key actually stops the session.
#: The session flow (Adım 8b-ii) installs one that shows "are you sure?" on the
#: window; with none installed — the dev harness, the tests — an abort is
#: immediate, which is the historical behaviour every abort site was written to.
_abort_confirmer: Callable[[], bool] | None = None


def set_abort_confirmer(confirmer: Callable[[], bool] | None) -> None:
    """Install (or clear) the confirmation asked before an abort takes effect."""
    global _abort_confirmer
    _abort_confirmer = confirmer


def should_abort() -> bool:
    """Whether an observed abort key should really stop the session.

    Called at every abort-key site instead of raising directly.  With no
    confirmer installed it returns True, so the abort is immediate; the session
    flow's confirmer returns False when the operator cancels, and the caller
    then carries on where it was.
    """
    if _abort_confirmer is None:
        return True
    return _abort_confirmer()
