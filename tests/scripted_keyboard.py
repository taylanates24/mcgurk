"""A keyboard that presses its own keys, for the hardware trial-loop tests.

Not a test module — a helper both ``test_modules_block*.py`` files import.  The
keyboard is the one part of a real run a test cannot perform, and faking it is
what makes the rest checkable: that the fixation, the presentation, the response
and the database writes happen in that order, that both reaction times are
recorded, and that a timeout leaves no response row.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Press:
    name: str
    rt: float
    #: Left None on purpose: the real ``tDown`` is only used for a consistency
    #: warning, and a made-up value would be testing the fake.
    tDown: float | None = None  # noqa: N815 - PsychoPy's spelling


class Clock:
    def __init__(self) -> None:
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1


class ScriptedKeyboard:
    """Stands in for ``psychopy.hardware.keyboard.Keyboard``.

    One entry per trial: a key name, or None to let the trial time out.  The
    press is delivered on the second poll so at least one flip of the prompt
    happens first, which is what a real press does.
    """

    def __init__(self, script: list[str | None], rt_s: float = 0.25) -> None:
        self.script = list(script)
        self.rt_s = rt_s
        self.clock = Clock()
        self._polls = 0
        self._trial = 0

    def getKeys(  # noqa: N802 - PsychoPy's spelling; this stands in for it
        self,
        keyList: list[str] | None = None,  # noqa: N803
        waitRelease: bool = True,  # noqa: N803
        clear: bool = True,
    ) -> list[Press]:
        if keyList is None:
            # The clearing call the collector makes before the prompt.
            self._polls = 0
            return []
        self._polls += 1
        if self._polls < 2 or self._trial >= len(self.script):
            return []
        key = self.script[self._trial]
        if key is None:
            return []
        self._trial += 1
        self._polls = 0
        return [Press(name=key, rt=self.rt_s)]

    def finish_timed_out_trial(self) -> None:
        self._trial += 1
