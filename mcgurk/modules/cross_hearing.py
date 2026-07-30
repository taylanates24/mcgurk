"""Cross-hearing check (steps.md §C Adım 8, §F.3) — Modül for SSD validity.

A tone is lateralised to the participant's **deaf** ear on half the trials; the
other half are silent catch trials.  The participant presses when they hear
something.  In a genuinely single-sided-deaf ear this should sit at chance; if it
is detected above chance the sound is reaching the good cochlea through the skull
and the spatial-direction manipulation (the SSD hypothesis carrier in Modül 1–2)
is invalid for that participant.

This module only *collects* the detections and false alarms.  Whether they are
"above chance" is a reading for the QC report (Adım 9), fixed before data
collection (§F.3) — not decided here from the numbers.

The design (which trials carry the tone, on which ear) is pure and tested in CI;
only :func:`run_cross_hearing` touches PsychoPy.  Catch trials carry no stimulus
at all, so this cannot go through ``AVPresenter`` — it has its own small loop,
built on the same audio-scheduling primitives the streams use.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..db.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Block,
    Response,
    Trial,
    TrialTiming,
)
from ..engine import AbortSession
from ..engine.av_presenter import check_abort
from ..engine.scheduling import TimingParams
from ..stimuli.manifest import ManifestError, StimulusManifest
from .base import ModuleError, derive_seed

logger = logging.getLogger(__name__)

MODULE_NAME = "cross_hearing"

#: Response categories.  A press inside the window is a HIT on a signal trial and
#: a FALSE_ALARM on a catch trial; the absences (MISS, CORRECT_REJECTION) produce
#: no ``responses`` row and are derived.
HIT = "HIT"
MISS = "MISS"
FALSE_ALARM = "FALSE_ALARM"
CORRECT_REJECTION = "CORRECT_REJECTION"

#: How far ahead of its flip the tone is scheduled — comfortable margin for PTB.
_LEAD_S = 0.2


def classify(signal_present: bool, detected: bool) -> str:
    """The outcome of one trial from whether it carried a tone and got a press."""
    if signal_present:
        return HIT if detected else MISS
    return FALSE_ALARM if detected else CORRECT_REJECTION


@dataclass(frozen=True)
class CrossTrial:
    """One detection trial: whether it carries the tone, on which ear."""

    signal_present: bool
    ear: str
    tone_path: Path | None
    tone_burst_s: float
    trial: Trial

    def for_block(self, block_id: int, trial_index: int) -> Trial:
        return replace(self.trial, block_id=block_id, trial_index=trial_index)


def plan_trials(
    config: ExperimentConfig,
    manifest: StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    deaf_ear: str,
) -> list[CrossTrial]:
    """Build the detection trials for *deaf_ear*.

    ``catch_ratio`` of the trials are silent; the rest carry the tone.  At least
    one of each is guaranteed so both a hit rate and a false-alarm rate exist.
    The signal/catch order is shuffled from the session seed.
    """
    check = config.cross_hearing_check
    if not check.enabled:
        raise ModuleError("cross_hearing_check.enabled false — deneme üretilmez")
    if deaf_ear not in ("left", "right"):
        raise ModuleError(
            f"Çapraz dinleme kulağı 'left' veya 'right' olmalı: {deaf_ear!r}"
        )

    n = check.n_trials
    n_catch = round(n * check.catch_ratio)
    n_catch = min(max(n_catch, 1), n - 1)  # at least one catch and one signal
    n_signal = n - n_catch
    flags = [True] * n_signal + [False] * n_catch
    random.Random(derive_seed(seed, MODULE_NAME)).shuffle(flags)

    try:
        tone = manifest.tone(check.tone_hz)
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nÇapraz dinleme tonu hazır değil: python tools/prepare_stimuli.py"
        ) from exc
    tone_path = tone.file.resolve(stimuli_root)

    planned: list[CrossTrial] = []
    for present in flags:
        trial = Trial(
            block_id=0,  # the runner fills this in
            trial_index=0,
            module=MODULE_NAME,
            condition_label="signal" if present else "catch",
            visual_token=None,
            audio_token=None,
            ear=deaf_ear,
            snr_db=None,
            noise_condition=None,
            nominal_soa_ms=None,
            # A-only when a tone plays; a catch trial presents nothing at all.
            presentation_mode="A" if present else None,
            design_extra={"signal_present": present},
        )
        planned.append(
            CrossTrial(
                signal_present=present,
                ear=deaf_ear,
                tone_path=tone_path if present else None,
                tone_burst_s=0.0,
                trial=trial,
            )
        )
    logger.info(
        "Çapraz dinleme tasarımı: %d deneme (%d sinyal, %d catch), sağır kulak %s",
        n,
        n_signal,
        n_catch,
        deaf_ear,
    )
    return planned


@dataclass
class CrossHearingOutcome:
    """The operator-facing summary of the check."""

    n_signal: int = 0
    n_catch: int = 0
    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    correct_rejections: int = 0
    ear: str = ""
    rts_ms: list[float] = field(default_factory=list)

    @property
    def n_trials(self) -> int:
        return self.n_signal + self.n_catch


# ------------------------------------------------------------------- the loop


def run_cross_hearing(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    planned: list[CrossTrial],
    win: Any,
    kb: Any,
    params: TimingParams,
    speaker: Any = None,
    calibration: Any = None,
    fixation: Any = None,
) -> CrossHearingOutcome:
    """Present the detection trials and record the presses.

    Raises whatever the engine raises; :class:`AbortSession` propagates so the
    caller closes the session ``aborted``.
    """
    import psychtoolbox as ptb

    from ..engine.audio import load_audio, make_sound

    check = config.cross_hearing_check
    low_s = check.response_window_ms[0] / 1000.0
    high_s = check.response_window_ms[1] / 1000.0
    key = check.response_key
    fixation_s = check.fixation_duration_ms / 1000.0
    post_s = check.post_response_ms / 1000.0

    ear = planned[0].ear if planned else ""
    outcome = CrossHearingOutcome(ear=ear)

    # One tone, lateralised to the deaf ear, reused by every signal trial.
    sound: Any = None
    for item in planned:
        if item.tone_path is not None:
            stimulus = load_audio(
                item.tone_path,
                ear=item.ear,
                burst_time_s=item.tone_burst_s,
                calibration=calibration,
                expected_sample_rate=config.audio.sample_rate,
            )
            sound = make_sound(stimulus, speaker=speaker)
            break

    block_index = db.next_block_index(session_id)
    block_id = db.add_block(
        Block(
            session_id=session_id,
            module=MODULE_NAME,
            block_index=block_index,
            label="cross_hearing",
            n_trials_planned=len(planned),
        )
    )
    logger.info("Çapraz dinleme bloğu %d: %d deneme, kulak %s", block_index, len(planned), ear)

    try:
        for index, item in enumerate(planned):
            _hold(win, fixation, fixation_s)
            trial_id = db.add_trial(item.for_block(block_id, index))

            kb.getKeys(keyList=[key], waitRelease=False, clear=True)
            win.flip()  # settling flip so getFutureFlipTime has a frame period
            onset = float(win.getFutureFlipTime(clock="ptb")) + _LEAD_S
            kb.clock.reset()
            reset_time = float(ptb.GetSecs())
            if item.signal_present:
                assert sound is not None  # a signal trial always has the tone
                sound.stop()
                sound.play(when=onset)

            presses = _listen(win, fixation, kb, key=key, until_s=onset + high_s,
                              reset_time=reset_time)
            in_window = [p - onset for p in presses if low_s <= (p - onset) <= high_s]
            detected = bool(in_window)

            db.set_trial_timing(
                trial_id,
                TrialTiming(audio_onset_s=onset if item.signal_present else None),
            )
            _tally(outcome, item.signal_present, detected)
            if detected:
                rt_ms = in_window[0] * 1000.0
                outcome.rts_ms.append(rt_ms)
                db.add_response(
                    Response(
                        trial_id=trial_id,
                        response_index=0,
                        raw_response=key,
                        category=HIT if item.signal_present else FALSE_ALARM,
                        is_correct=None,
                        rt_from_burst_ms=rt_ms,
                        rt_from_prompt_ms=None,
                        input_device="keyboard",
                    )
                )
            _blank(win, post_s)

        db.finish_block(block_id, SESSION_COMPLETED)
    except AbortSession:
        db.finish_block(block_id, SESSION_ABORTED)
        logger.warning("Çapraz dinleme kesildi: %d/%d deneme.", outcome.n_trials, len(planned))
        raise
    except Exception:
        db.finish_block(block_id, SESSION_ABORTED)
        raise

    logger.info(
        "Çapraz dinleme: isabet %d/%d, yanlış alarm %d/%d",
        outcome.hits,
        outcome.n_signal,
        outcome.false_alarms,
        outcome.n_catch,
    )
    return outcome


def _tally(outcome: CrossHearingOutcome, signal_present: bool, detected: bool) -> None:
    result = classify(signal_present, detected)
    if signal_present:
        outcome.n_signal += 1
        if result == HIT:
            outcome.hits += 1
        else:
            outcome.misses += 1
    else:
        outcome.n_catch += 1
        if result == FALSE_ALARM:
            outcome.false_alarms += 1
        else:
            outcome.correct_rejections += 1


def _hold(win: Any, fixation: Any, duration_s: float) -> None:
    import psychtoolbox as ptb

    deadline = float(ptb.GetSecs()) + duration_s
    while float(ptb.GetSecs()) < deadline:
        check_abort()
        if fixation is not None:
            fixation.draw()
        win.flip()


def _listen(
    win: Any,
    fixation: Any,
    kb: Any,
    *,
    key: str,
    until_s: float,
    reset_time: float,
) -> list[float]:
    """Flip until *until_s*, returning every press's absolute ptb time."""
    import psychtoolbox as ptb

    presses: list[float] = []

    def drain() -> None:
        for press in kb.getKeys(keyList=[key], waitRelease=False):
            presses.append(reset_time + float(press.rt))

    while float(ptb.GetSecs()) < until_s:
        check_abort()
        drain()
        if fixation is not None:
            fixation.draw()
        win.flip()
    drain()
    return presses


def _blank(win: Any, duration_s: float) -> None:
    import psychtoolbox as ptb

    deadline = float(ptb.GetSecs()) + duration_s
    win.flip()
    while float(ptb.GetSecs()) < deadline:
        check_abort()
        win.flip()


def summarise(outcome: CrossHearingOutcome) -> str:
    """A short report of the check, for the operator's console."""
    hit_rate = outcome.hits / outcome.n_signal if outcome.n_signal else 0.0
    fa_rate = (
        outcome.false_alarms / outcome.n_catch if outcome.n_catch else 0.0
    )
    lines = [
        f"Çapraz dinleme (sağır kulak: {outcome.ear or '?'})",
        f"  Sinyal denemesi   : {outcome.n_signal}",
        f"  Catch denemesi    : {outcome.n_catch}",
        f"  İsabet            : {outcome.hits}/{outcome.n_signal} (%{100 * hit_rate:.0f})",
        f"  Kaçırma           : {outcome.misses}",
        f"  Yanlış alarm      : {outcome.false_alarms}/{outcome.n_catch} (%{100 * fa_rate:.0f})",
        f"  Doğru ret         : {outcome.correct_rejections}",
    ]
    if outcome.rts_ms:
        mean_rt = sum(outcome.rts_ms) / len(outcome.rts_ms)
        lines.append(f"  İsabet RT (ort.)  : {mean_rt:.0f} ms (n={len(outcome.rts_ms)})")
    lines.append(
        "  Not: şans üstü tespit -> lateralizasyon geçersiz olabilir (§F.3, "
        "yorum Adım 9)."
    )
    return "\n".join(lines)
