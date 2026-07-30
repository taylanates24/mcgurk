"""Running trials: fixation, stimulus, response, database.

One loop serves every module that presents a stimulus and takes one
forced-choice response.  What differs between them — the response grid, what a
response *means*, whether there is a correct answer — arrives as a
:class:`TrialPolicy`; the sequencing and the database writes are the same, and
duplicating them per module is how the two copies drift apart.

The loop's shape is set by three rules from §A:

* **§A.12 — no I/O in the presentation.**  The next trial's media are loaded
  *before* its fixation starts, not during it: ``prepare()`` decodes a video
  frame and reads a WAV, and doing that inside a flip loop would drop frames on
  the fixation instead of on the stimulus, which is not an improvement.
* **§A.5 — commits at block boundaries.**  A module of 140 trials is split into
  blocks of at most ``session.break_every_n_trials``.  One block would mean a
  crash costs the whole module; Adım 8 puts its break screens at the same
  boundaries.
* **§A.10 — no correct answer where there is none.**  ``is_correct`` comes from
  the policy, and for ``mcgurk`` the policy never produces one.  The database
  enforces it too.

Everything that decides *what* to present lives in the module files and
everything that decides *when* lives in ``engine/``; this file only sequences
them and writes the result down.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..db.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Block,
    Response,
    Trial,
)
from ..engine import AbortSession
from ..engine.av_presenter import AVPresenter, TimingRecord, check_abort
from . import avsr as avsr_module
from . import dichotic as dichotic_module
from . import mcgurk as mcgurk_module
from . import practice as practice_module
from . import tbw as tbw_module
from .base import PlannedTrial, chunk
from .response import Choice, ResponseGrid, collect_choice, collect_free_text, show_message

logger = logging.getLogger(__name__)

#: What a timeout is counted as in the operator's summary.  No ``responses``
#: row is written for it (Adım 1 decision), so this is a tally, not a category.
TIMEOUT_TALLY = "NONE"


@dataclass(frozen=True)
class Evaluation:
    """What one response means to the module that asked for it.

    ``tally`` is the key it is counted under in the operator's summary; it is
    separate from ``category`` because AVSR has no categories — it has right
    and wrong — and a summary of "None: 135" would say nothing.
    """

    tally: str
    category: str | None = None
    is_correct: bool | None = None


@dataclass(frozen=True)
class TrialPolicy:
    """Everything the loop needs that differs between modules."""

    module: str
    fixation_s: float
    post_response_s: float
    timeout_s: float
    timeout_message: str
    #: The response-set entry that opens a free-text field, or None.
    free_text_label: str | None
    #: What the free-text screen asks.  None wherever ``free_text_label`` is
    #: None: a prompt for a screen that never opens is text nobody reads.
    free_text_prompt: str | None
    #: The grid to show for a given trial.  A callable rather than a single
    #: grid because AVSR asks a different question in V-only, where there is
    #: nothing to have heard.
    grid_for: Callable[[Trial], ResponseGrid]
    evaluate: Callable[[str | None, Trial], Evaluation]


@dataclass
class BlockOutcome:
    """What one block did — the operator-facing summary of a run."""

    block_id: int
    block_index: int
    n_planned: int
    module: str = ""
    n_presented: int = 0
    n_timeouts: int = 0
    categories: Counter[str] = field(default_factory=Counter)
    #: Only meaningful where the module scores responses (AVSR); McGurk leaves
    #: both at zero because there is no correct answer to count (§A.10).
    n_scored: int = 0
    n_correct: int = 0
    dropped_frame_trials: int = 0
    audio_glitch_trials: int = 0
    status: str = SESSION_COMPLETED


# ------------------------------------------------------------------ policies


def mcgurk_policy(config: ExperimentConfig, win: Any) -> TrialPolicy:
    module = config.modules.mcgurk
    grid = ResponseGrid(
        win,
        labels=list(module.response_set),
        keys=list(module.response_keys),
        question=module.prompts.question,
    )

    def evaluate(label: str | None, trial: Trial) -> Evaluation:
        category = mcgurk_module.categorise_for(module, label, trial)
        # §A.10 — and the database refuses anything else here.
        return Evaluation(tally=category, category=category, is_correct=None)

    return TrialPolicy(
        module=mcgurk_module.MODULE_NAME,
        fixation_s=module.fixation_duration_ms / 1000.0,
        post_response_s=module.post_response_ms / 1000.0,
        timeout_s=module.response_timeout_s,
        timeout_message=module.prompts.timeout,
        free_text_label=module.free_text_response,
        free_text_prompt=module.prompts.other,
        grid_for=lambda _trial: grid,
        evaluate=evaluate,
    )


#: Tallies for a scored module.  Turkish, like the rest of the operator's
#: console; they never reach the participant.
CORRECT_TALLY = "DOĞRU"
INCORRECT_TALLY = "YANLIŞ"


def avsr_policy(config: ExperimentConfig, win: Any) -> TrialPolicy:
    module = config.modules.avsr
    avsr_module.check_response_mode(module)

    # One grid per distinct question, built once per block: rebuilding four
    # TextStims per trial would put font work in the inter-trial interval,
    # which is where the next trial's media are being loaded (§A.12).
    grids = {
        mode: ResponseGrid(
            win,
            labels=list(module.response_set),
            keys=list(module.response_keys),
            question=module.question_for(mode),
        )
        for mode in module.presentation_modes
    }

    def evaluate(label: str | None, trial: Trial) -> Evaluation:
        correct = avsr_module.score_for(label, trial)
        return Evaluation(
            tally=CORRECT_TALLY if correct else INCORRECT_TALLY,
            # Scored modules leave `category` empty: is_correct already says
            # it, and one fact in two columns is one fact that can disagree.
            category=None,
            is_correct=correct,
        )

    def grid_for(trial: Trial) -> ResponseGrid:
        mode = trial.presentation_mode or ""
        if mode not in grids:  # pragma: no cover - the design cannot produce it
            raise KeyError(f"AVSR denemesinde bilinmeyen sunum modu: {mode!r}")
        return grids[mode]

    return TrialPolicy(
        module=avsr_module.MODULE_NAME,
        fixation_s=module.fixation_duration_ms / 1000.0,
        post_response_s=module.post_response_ms / 1000.0,
        timeout_s=module.response_timeout_s,
        timeout_message=module.prompts.timeout,
        free_text_label=module.free_text_response,
        free_text_prompt=module.prompts.other,
        grid_for=grid_for,
        evaluate=evaluate,
    )


def tbw_policy(config: ExperimentConfig, win: Any) -> TrialPolicy:
    """Modül 3 — a two-alternative simultaneity judgement.

    The same screen as the other modules with two options instead of nine, and
    the same absence of a correct answer as McGurk: what is recorded is which
    judgement was given (``category``), never whether it was right (§A.10 — and
    the database refuses ``is_correct`` on ``tbw`` trials).
    """
    module = config.modules.tbw
    grid = ResponseGrid(
        win,
        labels=list(module.response_set),
        keys=list(module.response_keys),
        question=module.prompts.question,
        # Two long Turkish labels side by side: they need the room that nine
        # syllables did not.
        columns=2,
        spacing_px=(520.0, 130.0),
    )

    def evaluate(label: str | None, _trial: Trial) -> Evaluation:
        judgement = tbw_module.judge(label, module)
        return Evaluation(
            tally=judgement or TIMEOUT_TALLY, category=judgement, is_correct=None
        )

    return TrialPolicy(
        module=tbw_module.MODULE_NAME,
        fixation_s=module.fixation_duration_ms / 1000.0,
        post_response_s=module.post_response_ms / 1000.0,
        timeout_s=module.response_timeout_s,
        timeout_message=module.prompts.timeout,
        free_text_label=module.free_text_response,
        free_text_prompt=module.prompts.other,
        grid_for=lambda _trial: grid,
        evaluate=evaluate,
    )


def dichotic_policy(config: ExperimentConfig, win: Any) -> TrialPolicy:
    """Modül 5 — one report of a syllable heard under binaural competition.

    The same screen as McGurk with four options instead of nine, and the same
    absence of a correct answer: what is recorded is which ear's syllable was
    reported (``category``), never whether the participant was right (§A.10 —
    and the database refuses ``is_correct`` on ``dichotic`` trials).
    """
    module = config.modules.dichotic
    grid = ResponseGrid(
        win,
        labels=list(module.response_set),
        keys=list(module.response_keys),
        question=module.prompts.question,
    )

    def evaluate(label: str | None, trial: Trial) -> Evaluation:
        category = dichotic_module.categorise_for(label, trial)
        return Evaluation(tally=category, category=category, is_correct=None)

    return TrialPolicy(
        module=dichotic_module.MODULE_NAME,
        fixation_s=module.fixation_duration_ms / 1000.0,
        post_response_s=module.post_response_ms / 1000.0,
        timeout_s=module.response_timeout_s,
        timeout_message=module.prompts.timeout,
        free_text_label=module.free_text_response,
        free_text_prompt=module.prompts.other,
        grid_for=lambda _trial: grid,
        evaluate=evaluate,
    )


def practice_policy(config: ExperimentConfig, win: Any) -> TrialPolicy:
    """The warm-up (Adım 8b-ii) — the McGurk response screen, nothing scored.

    Reuses McGurk's grid so the participant learns the mechanic they will use
    most.  Nothing is derived from the response: no category, no correctness
    (§Don'ts — a warm-up that scored would prime the effect); the raw press is
    recorded and the operator's summary just tallies what was pressed.
    """
    module = config.modules.mcgurk
    grid = ResponseGrid(
        win,
        labels=list(module.response_set),
        keys=list(module.response_keys),
        question=module.prompts.question,
    )

    def evaluate(label: str | None, _trial: Trial) -> Evaluation:
        return Evaluation(tally=label or "?", category=None, is_correct=None)

    return TrialPolicy(
        module=practice_module.MODULE_NAME,
        fixation_s=module.fixation_duration_ms / 1000.0,
        post_response_s=module.post_response_ms / 1000.0,
        timeout_s=module.response_timeout_s,
        timeout_message=module.prompts.timeout,
        free_text_label=module.free_text_response,
        free_text_prompt=module.prompts.other,
        grid_for=lambda _trial: grid,
        evaluate=evaluate,
    )


# -------------------------------------------------------------------- the loop


def run_blocks(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    policy: TrialPolicy,
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """Present *planned* and record every trial.

    Returns one :class:`BlockOutcome` per block.  Raises whatever the engine
    raises: a trial that could not be presented as specified is not a trial to
    salvage, and :class:`AbortSession` propagates so the caller can close the
    session as ``aborted``.

    *on_break*, if given, is called between blocks — after a block is committed
    and before the next one starts, which is the §A.5 commit boundary and so a
    safe point to pause.  It receives ``(blocks_done, blocks_total)``.  The
    session flow (Adım 8) shows its break screen here; the dev harness passes
    nothing and runs straight through.
    """
    outcomes: list[BlockOutcome] = []
    trial_index = 0
    chunks = chunk(planned, config.session.break_every_n_trials)
    for chunk_number, trials in enumerate(chunks):
        block_index = db.next_block_index(session_id)
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module=policy.module,
                block_index=block_index,
                label=f"{policy.module} {chunk_number + 1}",
                n_trials_planned=len(trials),
            )
        )
        outcome = BlockOutcome(
            block_id=block_id,
            block_index=block_index,
            n_planned=len(trials),
            module=policy.module,
        )
        outcomes.append(outcome)
        logger.info(
            "Blok %d (%s): %d deneme", block_index, outcome_label(outcome), len(trials)
        )

        try:
            for item in trials:
                _run_one_trial(
                    db=db,
                    presenter=presenter,
                    win=win,
                    kb=kb,
                    policy=policy,
                    item=item,
                    block_id=block_id,
                    trial_index=trial_index,
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
            "Blok %d tamamlandı: %d deneme, %d zaman aşımı, %s",
            block_index,
            outcome.n_presented,
            outcome.n_timeouts,
            dict(outcome.categories),
        )
        if on_break is not None and chunk_number < len(chunks) - 1:
            on_break(chunk_number + 1, len(chunks))

    return outcomes


def run_mcgurk(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """Modül 1 — see :func:`run_blocks`."""
    return run_blocks(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        policy=mcgurk_policy(config, win),
        on_break=on_break,
    )


def run_avsr(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """Modül 2 — see :func:`run_blocks`."""
    return run_blocks(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        policy=avsr_policy(config, win),
        on_break=on_break,
    )


def run_tbw(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """Modül 3 — see :func:`run_blocks`."""
    return run_blocks(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        policy=tbw_policy(config, win),
        on_break=on_break,
    )


def run_dichotic(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """Modül 5 — see :func:`run_blocks`."""
    return run_blocks(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        policy=dichotic_policy(config, win),
        on_break=on_break,
    )


def run_practice(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    planned: list[PlannedTrial],
    on_break: Callable[[int, int], None] | None = None,
) -> list[BlockOutcome]:
    """The practice warm-up — see :func:`run_blocks`."""
    return run_blocks(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        policy=practice_policy(config, win),
        on_break=on_break,
    )


def outcome_label(outcome: BlockOutcome) -> str:
    return f"{outcome.module} #{outcome.block_index}"


def _run_one_trial(
    *,
    db: Database,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    policy: TrialPolicy,
    item: PlannedTrial,
    block_id: int,
    trial_index: int,
    outcome: BlockOutcome,
) -> None:
    # Loading first, fixation second: the fixation is the participant's cue that
    # a trial is starting, and it should not be the interval that stutters.
    prepared = presenter.prepare(item.spec)
    try:
        _hold_fixation(presenter, win, policy.fixation_s)

        # The design row goes in before the presentation, so a trial that fails
        # to present is visible as a trial with no timing rather than not
        # visible at all.  Nothing is committed until the block closes (§A.5).
        trial = item.for_block(block_id, trial_index)
        trial_id = db.add_trial(trial)

        record = presenter.present(prepared)
        db.set_trial_timing(trial_id, record.to_trial_timing())
        outcome.n_presented += 1
        if record.dropped_frames:
            outcome.dropped_frame_trials += 1
        if record.audio_time_failed or record.audio_xruns:
            outcome.audio_glitch_trials += 1

        grid = policy.grid_for(trial)
        choice = collect_choice(win, grid, kb, timeout_s=policy.timeout_s)
        free_text: str | None = None
        if (
            choice.label is not None
            and policy.free_text_label is not None
            and choice.label.casefold() == policy.free_text_label.casefold()
        ):
            # The config refuses a free-text option without its prompt, so this
            # is a guarantee rather than a fallback.
            assert policy.free_text_prompt is not None
            free_text = collect_free_text(
                win,
                kb,
                prompt=policy.free_text_prompt,
                timeout_s=policy.timeout_s,
            )

        if choice.timed_out:
            outcome.n_timeouts += 1
            outcome.categories[TIMEOUT_TALLY] += 1
            show_message(
                win,
                policy.timeout_message,
                duration_s=min(1.0, policy.post_response_s + 0.7),
            )
        else:
            evaluation = policy.evaluate(choice.label, trial)
            outcome.categories[evaluation.tally] += 1
            if evaluation.is_correct is not None:
                outcome.n_scored += 1
                outcome.n_correct += int(evaluation.is_correct)
            db.add_response(
                Response(
                    trial_id=trial_id,
                    response_index=0,
                    raw_response=choice.label,
                    free_text=free_text or None,
                    category=evaluation.category,
                    is_correct=evaluation.is_correct,
                    rt_from_burst_ms=_rt_from_burst_ms(presenter, record, choice),
                    rt_from_prompt_ms=choice.rt_from_prompt_ms,
                    input_device="keyboard",
                )
            )
    finally:
        presenter.release(prepared)

    _blank(win, policy.post_response_s)


def _rt_from_burst_ms(
    presenter: AVPresenter, record: TimingRecord, choice: Choice
) -> float | None:
    """RT measured from the burst rather than from the prompt.

    Composed from the response's own RT and the known interval between the burst
    and the prompt flip, both on the ptb clock.  ``burst_onset_s`` is relative to
    the presenter's reference time, so it is put back on the absolute clock
    first.  In a V-only trial the "burst" is the visual one (see
    ``TimingRecord.burst_onset_s``).
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
    scored = correct = 0
    for outcome in outcomes:
        total.update(outcome.categories)
        planned += outcome.n_planned
        presented += outcome.n_presented
        timeouts += outcome.n_timeouts
        dropped += outcome.dropped_frame_trials
        glitches += outcome.audio_glitch_trials
        scored += outcome.n_scored
        correct += outcome.n_correct

    lines = [
        f"Blok sayısı            : {len(outcomes)}",
        f"Sunulan / planlanan    : {presented} / {planned}",
        f"Zaman aşımı            : {timeouts}",
        f"Kare düşen deneme      : {dropped}",
        f"Ses zamanlaması bozulan: {glitches}",
    ]
    if scored:
        # Timeouts are outside `scored` because they produce no response; the
        # line above is where they are visible.
        lines.append(
            f"Doğruluk (yanıtlanan)  : {correct} / {scored} "
            f"(%{100 * correct / scored:.1f})"
        )
    lines.append("Yanıtlar:")
    for tally, count in sorted(total.items(), key=lambda item: -item[1]):
        share = 100.0 * count / presented if presented else 0.0
        lines.append(f"  {tally:<12}{count:>5}  (%{share:.1f})")
    return "\n".join(lines)
