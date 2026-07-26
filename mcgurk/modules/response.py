"""Collecting a forced-choice response, and the two reaction times.

Keyboard only.  A mixed keyboard/mouse data set would need the input device as
a covariate in every RT model, and steps.md §C Adım 4 makes the mouse optional
for exactly that reason: ``responses.input_device`` exists so it *can* be added,
not so it has to be.

**Both RTs come from one measurement.**  ``rt_from_prompt_ms`` is read from the
keyboard's own clock, reset at the flip that shows the prompt.  ``rt_from_burst``
is then that number plus the interval between the burst and the prompt flip,
which the caller already knows from the ``TimingRecord``.  The alternative —
subtracting the burst time from the key's absolute timestamp — depends on the
keyboard backend timestamping on the same clock as ``psychtoolbox.GetSecs``.
It does on this machine, and the discrepancy is checked and logged rather than
assumed (see ``_check_clock_agreement``); but nothing is *computed* from it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..engine import AbortSession
from ..engine.av_presenter import ABORT_KEY

logger = logging.getLogger(__name__)

#: Keys the free-text field accepts, besides the letters.  Turkish characters
#: are deliberately absent: the field transcribes syllables ("bga"), and
#: PsychoPy key names for the Turkish layout's dead keys are not dependable.
_TEXT_KEYS = {"space": " ", "minus": "-"}
_TEXT_ACCEPT = "return"
_TEXT_DELETE = "backspace"

#: A key press timestamped more than this far from the prompt flip on the other
#: clock is reported: it means the two time bases are not the same one.
_CLOCK_AGREEMENT_TOLERANCE_MS = 5.0


@dataclass(frozen=True)
class Choice:
    """What the participant answered, or that they did not."""

    #: The ``response_set`` entry, or None on timeout.
    label: str | None
    free_text: str | None
    rt_from_prompt_ms: float | None
    #: ``ptb`` time of the flip that showed the prompt — the second RT
    #: reference is derived from it by the caller.
    prompt_onset_s: float
    key: str | None = None
    #: Presses discarded because they arrived before the prompt.  Responses are
    #: only accepted once the options are on screen; a press during the video
    #: would otherwise be recorded with a near-zero RT.
    early_presses: int = 0

    @property
    def timed_out(self) -> bool:
        return self.label is None


class ResponseGrid:
    """The response options, laid out once and redrawn every trial.

    Built once per block: constructing nine ``TextStim`` objects per trial would
    be file and font work inside the inter-trial interval, which is where the
    next trial's media are being loaded (§A.12).
    """

    def __init__(
        self,
        win: Any,
        *,
        labels: list[str],
        keys: list[str],
        question: str,
        columns: int = 5,
        text_height_px: float = 42.0,
        question_height_px: float = 56.0,
        spacing_px: tuple[float, float] = (300.0, 130.0),
    ) -> None:
        from psychopy import visual

        if len(labels) != len(keys):
            raise ValueError("labels ve keys aynı uzunlukta olmalı")

        self.win = win
        self.labels = labels
        self.keys = keys
        #: Key -> index, so a press resolves to a ``response_set`` entry.
        self.by_key = {key: index for index, key in enumerate(keys)}
        self._highlighted: int | None = None

        rows = -(-len(labels) // columns)  # ceil
        top = (rows - 1) * spacing_px[1] / 2.0

        self.question = visual.TextStim(
            win,
            text=question,
            height=question_height_px,
            color="white",
            pos=(0, top + spacing_px[1] * 1.2),
            units="pix",
            autoLog=False,
        )
        self.options: list[Any] = []
        for index, (label, key) in enumerate(zip(labels, keys, strict=True)):
            row, column = divmod(index, columns)
            in_row = min(columns, len(labels) - row * columns)
            x = (column - (in_row - 1) / 2.0) * spacing_px[0]
            y = top - row * spacing_px[1]
            self.options.append(
                visual.TextStim(
                    win,
                    text=f"{key}\n{label}",
                    height=text_height_px,
                    color="white",
                    pos=(x, y),
                    units="pix",
                    autoLog=False,
                )
            )

    def draw(self, highlight: int | None = None) -> None:
        """Draw the prompt.  *highlight* marks the option just chosen.

        The highlight is confirmation that the press registered — not feedback:
        it says nothing about the response being right, because in this module
        there is no right (§A.10), and telling a participant anything about
        their McGurk responses would teach them the effect mid-session.

        Colours are only assigned when they change: setting ``color`` on a
        ``TextStim`` rebuilds its texture, and doing that for nine options on
        every frame of the response screen would make the prompt sluggish for
        no reason.
        """
        if highlight != self._highlighted:
            for index, option in enumerate(self.options):
                option.color = "yellow" if index == highlight else "white"
            self._highlighted = highlight

        self.question.draw()
        for option in self.options:
            option.draw()


def make_keyboard() -> Any:
    """A PsychoPy keyboard, with its backend logged once.

    The backend decides how precise the timestamps are; recording which one was
    in use is cheaper than wondering later.
    """
    from psychopy.hardware import keyboard

    kb = keyboard.Keyboard()
    logger.info(
        "Klavye: %s (arka uç: %s)",
        type(kb).__name__,
        getattr(kb, "backend", None) or "?",
    )
    return kb


def collect_choice(
    win: Any,
    grid: ResponseGrid,
    kb: Any,
    *,
    timeout_s: float,
    highlight_s: float = 0.15,
) -> Choice:
    """Show the options and wait for one of them.

    Raises:
        AbortSession: if the operator pressed the abort key.
    """
    import psychtoolbox as ptb

    early = len(kb.getKeys(waitRelease=False, clear=True))
    if early:
        logger.debug("Yanıt ekranından önce %d tuş basımı atıldı.", early)

    grid.draw()
    win.flip()
    prompt_onset = float(ptb.GetSecs())
    kb.clock.reset()

    accepted = list(grid.by_key) + [ABORT_KEY]
    deadline = prompt_onset + timeout_s

    while float(ptb.GetSecs()) < deadline:
        presses = kb.getKeys(keyList=accepted, waitRelease=False)
        for press in presses:
            if press.name == ABORT_KEY:
                raise AbortSession()
            index = grid.by_key[press.name]
            _check_clock_agreement(press, prompt_onset)
            if highlight_s > 0:
                grid.draw(highlight=index)
                win.flip()
                while float(ptb.GetSecs()) < prompt_onset + press.rt + highlight_s:
                    grid.draw(highlight=index)
                    win.flip()
            return Choice(
                label=grid.labels[index],
                free_text=None,
                rt_from_prompt_ms=float(press.rt) * 1000.0,
                prompt_onset_s=prompt_onset,
                key=press.name,
                early_presses=early,
            )
        grid.draw()
        win.flip()

    return Choice(
        label=None,
        free_text=None,
        rt_from_prompt_ms=None,
        prompt_onset_s=prompt_onset,
        early_presses=early,
    )


def collect_free_text(
    win: Any,
    kb: Any,
    *,
    prompt: str,
    timeout_s: float,
    max_chars: int = 24,
    text_height_px: float = 48.0,
) -> str:
    """Read a typed answer.  Returns "" if nothing was typed in time.

    Raises:
        AbortSession: if the operator pressed the abort key.
    """
    import psychtoolbox as ptb
    from psychopy import visual

    label = visual.TextStim(
        win, text=prompt, height=text_height_px * 0.7, color="white",
        pos=(0, text_height_px * 1.6), units="pix", autoLog=False,
    )
    typed = visual.TextStim(
        win, text="", height=text_height_px, color="yellow", pos=(0, 0),
        units="pix", autoLog=False,
    )

    kb.getKeys(waitRelease=False, clear=True)
    answer = ""
    shown = ""
    deadline = float(ptb.GetSecs()) + timeout_s
    while float(ptb.GetSecs()) < deadline:
        for press in kb.getKeys(waitRelease=False):
            name = press.name
            if name == ABORT_KEY:
                raise AbortSession()
            if name == _TEXT_ACCEPT:
                return answer.strip()
            if name == _TEXT_DELETE:
                answer = answer[:-1]
            elif name in _TEXT_KEYS:
                answer += _TEXT_KEYS[name]
            elif len(name) == 1 and name.isalnum():
                answer += name
            answer = answer[:max_chars]
        # Only on change: assigning ``text`` re-lays out the stimulus.
        if answer != shown:
            typed.text = answer
            shown = answer
        label.draw()
        typed.draw()
        win.flip()

    logger.info("Serbest metin zaman aşımına uğradı; yazılan: %r", answer)
    return answer.strip()


def show_message(win: Any, text: str, *, duration_s: float, height_px: float = 48.0) -> None:
    """Hold *text* on screen for *duration_s* (abort key stays live)."""
    import psychtoolbox as ptb
    from psychopy import visual

    from ..engine.av_presenter import check_abort

    stim = visual.TextStim(
        win, text=text, height=height_px, color="white", pos=(0, 0),
        units="pix", autoLog=False,
    )
    deadline = float(ptb.GetSecs()) + duration_s
    while float(ptb.GetSecs()) < deadline:
        check_abort()
        stim.draw()
        win.flip()


def _check_clock_agreement(press: Any, prompt_onset_s: float) -> None:
    """Warn when the key's absolute timestamp is on another time base.

    ``press.rt`` is what the RT is computed from, so a disagreement is not a
    data error — but it does mean the keyboard is not timestamping on the ptb
    clock, and the photodiode measurement (docs/01) is interpreted assuming it
    does.  Better said out loud once than discovered in the analysis.
    """
    down = getattr(press, "tDown", None)
    if down is None:
        return
    difference_ms = abs((float(down) - prompt_onset_s) - float(press.rt)) * 1000.0
    if difference_ms > _CLOCK_AGREEMENT_TOLERANCE_MS:
        logger.warning(
            "Klavye zaman damgası ptb saatiyle uyuşmuyor: tDown farkı %.1f ms. "
            "RT'ler klavyenin kendi saatinden hesaplanıyor (etkilenmiyor), ama "
            "mutlak zaman karşılaştırmaları bu makinede güvenilir değil.",
            difference_ms,
        )
