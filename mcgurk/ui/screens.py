"""On-window screens: instructions, breaks and the operator's checklist confirm.

Every screen advances on the configured key (``screens.advance_key``) and aborts
on ESC, at any point — the Adım 0 lesson is that an abort key which only works on
the response screen is not an abort key.  PsychoPy is imported lazily so this
module imports on a machine without it; nothing here is called except during a
real session.

None of these draw feedback about a response: telling a participant anything
about their answers would teach the effect mid-session (§Don'ts).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..checklist import Check

logger = logging.getLogger(__name__)


def _wait_advance(
    win: Any,
    kb: Any,
    draw: Callable[[], None],
    *,
    advance_key: str,
    timeout_s: float | None = None,
) -> None:
    """Draw *draw* every frame until *advance_key* is pressed or the time runs out.

    Raises:
        AbortSession: if ESC is pressed.
    """
    import psychtoolbox as ptb

    from ..engine import AbortSession, should_abort
    from ..engine.av_presenter import ABORT_KEY

    kb.getKeys(clear=True)  # flush a key held over from the previous screen
    deadline = None if timeout_s is None else float(ptb.GetSecs()) + timeout_s
    while True:
        draw()
        win.flip()
        for press in kb.getKeys(keyList=[advance_key, ABORT_KEY], waitRelease=False):
            if press.name == ABORT_KEY:
                if should_abort():
                    raise AbortSession()
                # Cancelled: redraw and keep waiting for the advance key.
                continue
            if press.name == advance_key:
                return
        if deadline is not None and float(ptb.GetSecs()) >= deadline:
            return


def _text(win: Any, text: str, **kwargs: Any) -> Any:
    from psychopy import visual

    params: dict[str, Any] = {
        "text": text,
        "color": "white",
        "units": "pix",
        "wrapWidth": 1300,
        "autoLog": False,
    }
    params.update(kwargs)
    return visual.TextStim(win, **params)


def show_instruction(
    win: Any,
    kb: Any,
    text: str,
    *,
    advance_key: str,
    hint: str | None = None,
) -> None:
    """Show an instruction (or welcome/end) screen; wait for the advance key."""
    body = _text(win, text, height=40, pos=(0, 40))
    hint_stim = (
        _text(win, hint, height=26, color="gray", pos=(0, -380)) if hint else None
    )

    def draw() -> None:
        body.draw()
        if hint_stim is not None:
            hint_stim.draw()

    _wait_advance(win, kb, draw, advance_key=advance_key)


def show_break(
    win: Any,
    kb: Any,
    *,
    text: str,
    duration_s: float,
    advance_key: str,
    hint: str | None = None,
) -> None:
    """Show a break screen.

    Continues on the advance key, or automatically after *duration_s* so an
    unattended session does not stall.  ESC still aborts.
    """
    body = _text(win, text, height=40, pos=(0, 40))
    hint_stim = (
        _text(win, hint, height=26, color="gray", pos=(0, -380)) if hint else None
    )

    def draw() -> None:
        body.draw()
        if hint_stim is not None:
            hint_stim.draw()

    _wait_advance(win, kb, draw, advance_key=advance_key, timeout_s=duration_s)


def show_checklist(
    win: Any,
    kb: Any,
    checks: list[Check],
    *,
    advance_key: str,
    advance_hint: str,
) -> None:
    """Show the pre-session checklist for the operator to confirm.

    The same GREEN/RED lines the console printed (Adım 8a), on the presentation
    window this time — steps.md Adım 8: the checklist output should appear in the
    interface and the operator should confirm.  ESC aborts before the participant
    starts.
    """
    lines = ["Oturum öncesi kontrol — operatör onayı", ""]
    for check in checks:
        lines.append(f"[{check.status.value}] {check.name}")
        if check.detail:
            lines.append(f"      {check.detail}")
    body = _text(
        win, "\n".join(lines), height=28, pos=(0, 40), alignText="left", wrapWidth=1500
    )
    hint_stim = _text(win, advance_hint, height=26, color="gray", pos=(0, -400))

    def draw() -> None:
        body.draw()
        hint_stim.draw()

    _wait_advance(win, kb, draw, advance_key=advance_key)


#: Keys the quit-confirmation screen reads.  Return confirms, Escape cancels;
#: the participant-facing wording is in ``screens.quit_confirm`` (§A.9) and names
#: these keys.
QUIT_CONFIRM_KEY = "return"
QUIT_CANCEL_KEY = "escape"


def confirm_quit(win: Any, kb: Any, text: str) -> bool:
    """Ask "are you sure you want to quit?"; True = quit, False = continue.

    Installed as the engine's abort confirmer (Adım 8b-ii), so ESC anywhere —
    a screen, the response grid, mid-stimulus — opens this instead of stopping
    the session outright.  Both input queues are drained on the way out so the
    key that answered here does not re-fire the abort check on the next frame.
    """
    from psychopy import event

    prompt = _text(win, text, height=40, pos=(0, 0))
    # waitRelease=False so the ESC that *opened* this dialog is drained too: in a
    # video/stream trial that press was seen through psychopy.event, not the
    # keyboard, so it is still sitting in the keyboard buffer and the default
    # waitRelease=True flush (which ignores a key not yet released) would leave
    # it there — and the loop below would read it immediately as "cancel".
    kb.getKeys(waitRelease=False, clear=True)
    event.clearEvents()
    result: bool | None = None
    while result is None:
        prompt.draw()
        win.flip()
        for press in kb.getKeys(
            keyList=[QUIT_CONFIRM_KEY, QUIT_CANCEL_KEY], waitRelease=False
        ):
            if press.name == QUIT_CONFIRM_KEY:
                result = True
            elif press.name == QUIT_CANCEL_KEY:
                result = False
    kb.getKeys(waitRelease=False, clear=True)
    event.clearEvents()
    return result
