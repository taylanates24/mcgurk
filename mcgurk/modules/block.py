"""Running McGurk trials: fixation, stimulus, response, database.

The loop's shape is set by three rules from §A:

* **§A.12 — no I/O in the presentation.**  The next trial's media are loaded
  *before* its fixation starts, not during it: ``prepare()`` decodes a video
  frame and reads a WAV, and doing that inside a flip loop would drop frames on
  the fixation instead of on the stimulus, which is not an improvement.
* **§A.5 — commits at block boundaries.**  A module of 140 trials is split into
  blocks of at most ``session.break_every_n_trials``.  One block would mean a
  crash costs the whole module; Adım 8 puts its break screens at the same
  boundaries.
* **§A.10 — no correct answer.**  ``is_correct`` stays None for every trial
  here, congruent controls included.  The database enforces it too.

Everything that decides *what* to present lives in ``mcgurk.py`` and everything
that decides *when* lives in ``engine/``; this file only sequences them and
writes the result down.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..db.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Block,
    Response,
)
from ..engine import AbortSession
from ..engine.av_presenter import AVPresenter, TimingRecord, check_abort
from .base import PlannedTrial, chunk
from .mcgurk import MODULE_NAME, categorise_for
from .response import Choice, ResponseGrid, collect_choice, collect_free_text, show_message

logger = logging.getLogger(__name__)


@dataclass
class BlockOutcome:
    """What one block did — the operator-facing summary of a run."""

    block_id: int
    block_index: int
    n_planned: int
    n_presented: int = 0
    n_timeouts: int = 0
    categories: Counter[str] = field(default_factory=Counter)
    dropped_frame_trials: int = 0
    audio_glitch_trials: int = 0
    status: str = SESSION_COMPLETED


def run_mcgurk(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
) -> list[BlockOutcome]:
    """Present *planned* and record every trial.

    Returns one :class:`BlockOutcome` per block.  Raises whatever the engine
    raises: a trial that could not be presented as specified is not a trial to
    salvage, and :class:`AbortSession` propagates so the caller can close the
    session as ``aborted``.
    """
    module = config.modules.mcgurk
    grid = ResponseGrid(
        win,
        labels=list(module.response_set),
        keys=list(module.response_keys),
        question=module.prompts.question,
    )
    fixation_s = module.fixation_duration_ms / 1000.0
    post_response_s = module.post_response_ms / 1000.0

    outcomes: list[BlockOutcome] = []
    trial_index = 0
    for chunk_number, trials in enumerate(
        chunk(planned, config.session.break_every_n_trials)
    ):
        block_index = db.next_block_index(session_id)
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module=MODULE_NAME,
                block_index=block_index,
                label=f"{MODULE_NAME} {chunk_number + 1}",
                n_trials_planned=len(trials),
            )
        )
        outcome = BlockOutcome(
            block_id=block_id, block_index=block_index, n_planned=len(trials)
        )
        outcomes.append(outcome)
        logger.info(
            "Blok %d (%s): %d deneme", block_index, outcome_label(outcome), len(trials)
        )

        try:
            for item in trials:
                _run_one_trial(
                    config=config,
                    db=db,
                    presenter=presenter,
                    win=win,
                    kb=kb,
                    grid=grid,
                    item=item,
                    block_id=block_id,
                    trial_index=trial_index,
                    fixation_s=fixation_s,
                    post_response_s=post_response_s,
                    outcome=outcome,
                )
                trial_index += 1
        except AbortSession:
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            logger.warning(
                "Blok %d kesildi: %d/%d deneme sunuldu.",
                block_index,
                outcome.n_presented,
                outcome.n_planned,
            )
            raise
        except Exception:
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            raise

        db.finish_block(block_id, SESSION_COMPLETED)
        logger.info(
            "Blok %d tamamlandı: %d deneme, %d zaman aşımı, kategoriler %s",
            block_index,
            outcome.n_presented,
            outcome.n_timeouts,
            dict(outcome.categories),
        )

    return outcomes


def outcome_label(outcome: BlockOutcome) -> str:
    return f"{MODULE_NAME} #{outcome.block_index}"


def _run_one_trial(
    *,
    config: ExperimentConfig,
    db: Database,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    grid: ResponseGrid,
    item: PlannedTrial,
    block_id: int,
    trial_index: int,
    fixation_s: float,
    post_response_s: float,
    outcome: BlockOutcome,
) -> None:
    module = config.modules.mcgurk

    # Loading first, fixation second: the fixation is the participant's cue that
    # a trial is starting, and it should not be the interval that stutters.
    prepared = presenter.prepare(item.spec)
    try:
        _hold_fixation(presenter, win, fixation_s)

        # The design row goes in before the presentation, so a trial that fails
        # to present is visible as a trial with no timing rather than not
        # visible at all.  Nothing is committed until the block closes (§A.5).
        trial_id = db.add_trial(item.for_block(block_id, trial_index))

        record = presenter.present(prepared)
        db.set_trial_timing(trial_id, record.to_trial_timing())
        outcome.n_presented += 1
        if record.dropped_frames:
            outcome.dropped_frame_trials += 1
        if record.audio_time_failed or record.audio_xruns:
            outcome.audio_glitch_trials += 1

        choice = collect_choice(
            win, grid, kb, timeout_s=module.response_timeout_s
        )
        free_text: str | None = None
        if (
            choice.label is not None
            and module.free_text_response is not None
            and choice.label.casefold() == module.free_text_response.casefold()
        ):
            free_text = collect_free_text(
                win,
                kb,
                prompt=module.prompts.other,
                timeout_s=module.response_timeout_s,
            )

        if choice.timed_out:
            outcome.n_timeouts += 1
            outcome.categories["NONE"] += 1
            show_message(
                win, module.prompts.timeout, duration_s=min(1.0, post_response_s + 0.7)
            )
        else:
            category = categorise_for(module, choice.label, item.trial)
            outcome.categories[category] += 1
            db.add_response(
                Response(
                    trial_id=trial_id,
                    response_index=0,
                    raw_response=choice.label,
                    free_text=free_text or None,
                    category=category,
                    # §A.10 — and the database refuses anything else here.
                    is_correct=None,
                    rt_from_burst_ms=_rt_from_burst_ms(presenter, record, choice),
                    rt_from_prompt_ms=choice.rt_from_prompt_ms,
                    input_device="keyboard",
                )
            )
    finally:
        presenter.release(prepared)

    _blank(win, post_response_s)


def _rt_from_burst_ms(
    presenter: AVPresenter, record: TimingRecord, choice: Choice
) -> float | None:
    """RT measured from the acoustic burst rather than from the prompt.

    Composed from the response's own RT and the known interval between the burst
    and the prompt flip, both on the ptb clock.  ``burst_onset_s`` is relative to
    the presenter's reference time, so it is put back on the absolute clock
    first.
    """
    if choice.rt_from_prompt_ms is None or record.burst_onset_s is None:
        return None
    burst_absolute_s = record.burst_onset_s + presenter.reference_time_s
    return choice.rt_from_prompt_ms + (choice.prompt_onset_s - burst_absolute_s) * 1000.0


def _hold_fixation(presenter: AVPresenter, win: Any, duration_s: float) -> None:
    """Fixation cross on the refresh grid, with the abort key live.

    A flip loop rather than ``core.wait``: Adım 0's lesson is that an abort key
    which only works on the response screen is not an abort key, and the side
    benefit is that the interval lands on whole frames.
    """
    import psychtoolbox as ptb

    deadline = float(ptb.GetSecs()) + duration_s
    while float(ptb.GetSecs()) < deadline:
        check_abort()
        if presenter.fixation is not None:
            presenter.fixation.draw()
        win.flip()


def _blank(win: Any, duration_s: float) -> None:
    import psychtoolbox as ptb

    deadline = float(ptb.GetSecs()) + duration_s
    win.flip()
    while float(ptb.GetSecs()) < deadline:
        check_abort()
        win.flip()


def summarise(outcomes: list[BlockOutcome]) -> str:
    """A short report of a run, for the operator's console."""
    total: Counter[str] = Counter()
    presented = timeouts = planned = dropped = glitches = 0
    for outcome in outcomes:
        total.update(outcome.categories)
        planned += outcome.n_planned
        presented += outcome.n_presented
        timeouts += outcome.n_timeouts
        dropped += outcome.dropped_frame_trials
        glitches += outcome.audio_glitch_trials

    lines = [
        f"Blok sayısı            : {len(outcomes)}",
        f"Sunulan / planlanan    : {presented} / {planned}",
        f"Zaman aşımı            : {timeouts}",
        f"Kare düşen deneme      : {dropped}",
        f"Ses zamanlaması bozulan: {glitches}",
        "Kategoriler:",
    ]
    for category, count in sorted(total.items(), key=lambda item: -item[1]):
        share = 100.0 * count / presented if presented else 0.0
        lines.append(f"  {category:<12}{count:>5}  (%{share:.1f})")
    return "\n".join(lines)
