"""Running a continuous stimulus stream: schedule, listen, record.

``block.py`` sequences a trial at a time — fixation, stimulus, one forced
choice — and every module that fits that shape shares it.  Oddball and GIN do
not: there is no response screen, the stimuli arrive on a clock of their own,
and one stimulus can collect no press or several.

The two runners here keep their own loop bodies because the shape genuinely
differs — oddball writes one trial per tone and attributes presses to tones,
GIN writes one trial per six-second segment and attributes presses to the gaps
*inside* it — but everything underneath is shared: how a stimulus is scheduled,
how the screen is held while presses are timestamped, and how the backend's
health counters are read.  A third copy of those would drift.

Two things make this file different from ``block.py``:

* **Nothing is locked to the refresh grid.**  There is no video, so the flip
  loop exists only to keep the fixation on screen and the abort key live.  Every
  tone onset is computed once, from one origin, and handed to PsychPortAudio as
  an absolute time (§A.3) — a stream that re-referenced itself every tone would
  accumulate the scheduler's error over five minutes.
* **Responses are attributed, not collected.**  Presses are timestamped as they
  arrive and assigned to tones afterwards by
  ``oddball.attribute_presses``.  The alternative — deciding at press time which
  tone it belongs to — puts the response window inside the loop, where it
  cannot be tested without hardware.

§A.5 still holds: trials are written as they happen and nothing is committed
until the block closes.
"""

from __future__ import annotations

import bisect
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from ..config.calibration import Calibration
from ..config.schema import ExperimentConfig, GINConfig, OddballConfig
from ..db.database import Database
from ..db.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Block,
    Response,
    TrialTiming,
)
from ..engine import AbortSession, EngineError
from ..engine.audio import load_audio, make_sound, playback_health
from ..engine.av_presenter import check_abort
from ..engine.scheduling import TimingParams
from ..engine.window import FrameMonitor
from . import gin as gin_module
from . import oddball as oddball_module
from .base import PlannedTrial, chunk
from .block import BlockOutcome

logger = logging.getLogger(__name__)

#: How far ahead of its onset a tone is handed to the backend.  Far more than
#: PTB needs (``TimingParams.schedule_margin_s``, 20 ms): the margin also has to
#: absorb the block boundary, where a commit happens between two tones.
SCHEDULE_LEAD_S = 0.25

#: Held after the last tone of the run, so a press near the end of its response
#: window is still collected.
TAIL_MARGIN_S = 0.05


class StreamError(EngineError):
    """The stream could not be presented as specified."""


def run_oddball(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    planned: list[PlannedTrial],
    win: Any,
    kb: Any,
    params: TimingParams,
    speaker: Any = None,
    calibration: Calibration | None = None,
    fixation: Any = None,
) -> list[BlockOutcome]:
    """Modül 4 — present the tone stream and record every press.

    Returns one :class:`BlockOutcome` per block.  ``categories`` counts *presses*
    (hit, false alarm, outside the window), not detection outcomes: a miss and a
    correct rejection are the absence of a press, and the authoritative tally is
    ``oddball.summarise_measures`` reading the database back afterwards.

    Raises:
        StreamError: a tone could not be scheduled before its own onset, which
            means the stream is no longer the one that was designed.
        AbortSession: the operator pressed the abort key.
    """
    import psychtoolbox as ptb

    if not planned:
        return []
    module = config.modules.oddball
    window = module.response_window_ms
    if module.lead_in_s <= SCHEDULE_LEAD_S:
        # The first tone is scheduled during the lead-in; a lead-in shorter than
        # the scheduling margin would mean asking for it after it was due.
        raise StreamError(
            f"modules.oddball.lead_in_s ({module.lead_in_s:g} s) planlama "
            f"payından ({SCHEDULE_LEAD_S:g} s) büyük olmalı — ilk ton bu payın "
            "içinde planlanıyor."
        )

    sounds = _load_sounds(
        planned,
        calibration=calibration,
        sample_rate=config.audio.sample_rate,
        speaker=speaker,
    )
    health = {key: (0, 0) for key in sounds}

    intervals = [
        float(item.trial.design_extra["isi_ms"]) for item in planned[1:]
    ]
    reference_s = float(ptb.GetSecs())
    onsets = oddball_module.onset_times(intervals, reference_s + module.lead_in_s)
    monitor = FrameMonitor(win, params)

    # One clock reset for the whole run: the RT of a press is its offset from
    # this zero minus the tone's own onset, both on the ptb clock.  Resetting
    # per tone would need the reset to happen *at* the onset, which no loop can
    # promise to the millisecond.
    kb.getKeys(waitRelease=False, clear=True)
    kb.clock.reset()
    clock_zero_s = float(ptb.GetSecs())

    presses: list[float] = []
    trial_ids: list[int] = []
    response_counts: Counter[int] = Counter()
    state = _FlushState()
    outcomes: list[BlockOutcome] = []
    index = 0

    logger.info(
        "Oddball akışı: %d ton, %.1f s giriş, ~%.1f dk",
        len(planned),
        module.lead_in_s,
        oddball_module.stream_duration_s(planned, module) / 60.0,
    )

    for chunk_number, group in enumerate(
        chunk(planned, config.session.break_every_n_trials)
    ):
        block_index = db.next_block_index(session_id)
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module=oddball_module.MODULE_NAME,
                block_index=block_index,
                label=f"{oddball_module.MODULE_NAME} {chunk_number + 1}",
                n_trials_planned=len(group),
            )
        )
        outcome = BlockOutcome(
            block_id=block_id,
            block_index=block_index,
            n_planned=len(group),
            module=oddball_module.MODULE_NAME,
        )
        outcomes.append(outcome)
        logger.info("Blok %d (oddball): %d ton", block_index, len(group))

        try:
            for item in group:
                onset = onsets[index]
                _hold(
                    win, fixation, kb,
                    until_s=onset - SCHEDULE_LEAD_S,
                    key=module.response_key,
                    clock_zero_s=clock_zero_s,
                    presses=presses,
                )

                sound = sounds[_key(item)]
                _schedule(sound, onset, params, outcome)
                trial_ids.append(db.add_trial(item.for_block(block_id, index)))
                monitor.start()

                last = index + 1 >= len(onsets)
                _hold(
                    win, fixation, kb,
                    until_s=(
                        onset + window[1] / 1000.0 + TAIL_MARGIN_S
                        if last
                        else onsets[index + 1] - SCHEDULE_LEAD_S
                    ),
                    key=module.response_key,
                    clock_zero_s=clock_zero_s,
                    presses=presses,
                )

                stats = monitor.stop()
                time_failed, xruns = _health_delta(sound, health, _key(item))
                db.set_trial_timing(
                    trial_ids[index],
                    TrialTiming(
                        # No video, so no video onset and no realised SOA.  The
                        # onset recorded is the scheduled one: on this hardware
                        # PTB reports back exactly what it was asked for, and
                        # calling that a measurement is what Adım 3 refused to
                        # do (engine/audio.reported_start_time).
                        audio_onset_s=onset - reference_s,
                        dropped_frames=stats.dropped_frames,
                        max_frame_interval_ms=stats.max_interval_ms,
                    ),
                )
                outcome.n_presented += 1
                if stats.dropped_frames:
                    outcome.dropped_frame_trials += 1
                if time_failed or xruns:
                    outcome.audio_glitch_trials += 1
                    logger.warning(
                        "Ton %d: ses zamanlaması bozuldu (TimeFailed %d, "
                        "XRuns %d).", index, time_failed, xruns,
                    )
                index += 1
        except AbortSession:
            # The tones that were presented are data; the presses that answered
            # them are written before the block is closed as aborted.
            _flush(db, module, planned, onsets, trial_ids, presses, response_counts,
                   state, outcome)
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            logger.warning(
                "Blok %d kesildi: %d/%d ton sunuldu.",
                block_index, outcome.n_presented, outcome.n_planned,
            )
            raise
        except Exception:
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            raise

        _flush(db, module, planned, onsets, trial_ids, presses, response_counts,
               state, outcome)
        db.finish_block(block_id, SESSION_COMPLETED)
        logger.info(
            "Blok %d tamamlandı: %d ton, %s",
            block_index, outcome.n_presented, dict(outcome.categories),
        )

    if state.before_first:
        logger.info(
            "İlk tondan önce %d tuş basımı: hiçbir denemeye ait değil, "
            "kaydedilmedi.", state.before_first,
        )
    return outcomes


def run_gin(
    *,
    config: ExperimentConfig,
    db: Database,
    session_id: int,
    planned: list[PlannedTrial],
    win: Any,
    kb: Any,
    params: TimingParams,
    speaker: Any = None,
    calibration: Calibration | None = None,
    fixation: Any = None,
) -> list[BlockOutcome]:
    """Modül 6 — present the noise segments and record every press.

    The segment onsets come off one origin like oddball's tones, because the run
    is five minutes long and re-referencing each segment to the previous one's
    realised onset would accumulate the scheduler's error.  What differs is
    where a press lands: inside a segment there can be up to three gaps, and the
    press is attributed to one of them (``gin.attribute_presses``) rather than to
    the trial itself.

    ``categories`` counts *presses* — detections and false alarms.  A missed gap
    is the absence of a press and does not appear there; the authoritative tally
    is ``gin.measures_from_rows`` reading the database back afterwards.

    Raises:
        StreamError: a segment could not be scheduled before its own onset.
        AbortSession: the operator pressed the abort key.
    """
    import psychtoolbox as ptb

    if not planned:
        return []
    module = config.modules.gin
    if module.lead_in_s <= SCHEDULE_LEAD_S:
        raise StreamError(
            f"modules.gin.lead_in_s ({module.lead_in_s:g} s) planlama payından "
            f"({SCHEDULE_LEAD_S:g} s) büyük olmalı — ilk segment bu payın içinde "
            "planlanıyor."
        )

    # One sound at a time, loaded one segment ahead.  Oddball can buffer its two
    # tones for the whole run; thirty six-second segments (sixty with
    # ``ear_selection: both``) would be hundreds of megabytes, and §A.12 puts
    # preparation in the gap between stimuli — which is two seconds long here.
    #
    # The first one is loaded **before the clock starts**, like oddball's whole
    # set: reading six seconds of audio from a cold disk takes long enough to eat
    # the lead-in, and the run would then ask for an onset that had already
    # passed.  ``lead_in_s`` is a fixation period, not a loading window.
    cache = _SegmentCache(
        calibration=calibration, sample_rate=config.audio.sample_rate, speaker=speaker
    )
    cache.load(planned[0])

    step_s = module.segment_duration_s + module.inter_segment_interval_s
    reference_s = float(ptb.GetSecs())
    start_s = reference_s + module.lead_in_s
    onsets = [start_s + index * step_s for index in range(len(planned))]

    monitor = FrameMonitor(win, params)
    kb.getKeys(waitRelease=False, clear=True)
    kb.clock.reset()
    clock_zero_s = float(ptb.GetSecs())

    presses: list[float] = []
    trial_ids: list[int] = []
    # Carried across flushes: a press that arrives after its own block has
    # closed is still written against its own segment, and a response_index
    # that restarted at zero would collide with a row already there.
    response_counts: Counter[int] = Counter()
    state = _FlushState()
    outcomes: list[BlockOutcome] = []
    index = 0

    logger.info(
        "GIN akışı: %d segment, %.1f s giriş, ~%.1f dk",
        len(planned),
        module.lead_in_s,
        gin_module.stream_duration_s(planned, module) / 60.0,
    )

    for chunk_number, group in enumerate(
        chunk(planned, config.session.break_every_n_trials)
    ):
        block_index = db.next_block_index(session_id)
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module=gin_module.MODULE_NAME,
                block_index=block_index,
                label=f"{gin_module.MODULE_NAME} {chunk_number + 1}",
                n_trials_planned=len(group),
            )
        )
        outcome = BlockOutcome(
            block_id=block_id,
            block_index=block_index,
            n_planned=len(group),
            module=gin_module.MODULE_NAME,
        )
        outcomes.append(outcome)
        logger.info("Blok %d (gin): %d segment", block_index, len(group))

        try:
            for item in group:
                onset = onsets[index]
                _hold(
                    win, fixation, kb,
                    until_s=onset - SCHEDULE_LEAD_S,
                    key=module.response_key,
                    clock_zero_s=clock_zero_s,
                    presses=presses,
                )

                sound = cache.get(item)
                _schedule(sound, onset, params, outcome)
                trial_ids.append(db.add_trial(item.for_block(block_id, index)))
                monitor.start()

                # The next segment is read from disk while this one plays: six
                # seconds of slack, and it is over long before the next
                # scheduling margin opens.
                if index + 1 < len(planned):
                    cache.load(planned[index + 1])

                last = index + 1 >= len(onsets)
                _hold(
                    win, fixation, kb,
                    # Through the inter-segment interval, so a press answering a
                    # gap near the end of the segment is still collected — the
                    # config keeps the response window shorter than this.  But
                    # it stops one scheduling margin before the next segment,
                    # or that segment would be asked for after it was due; the
                    # presses of that last quarter second are collected by the
                    # next iteration's leading hold and bucketed by onset at
                    # flush time, so nothing is lost.
                    until_s=(
                        onset + step_s
                        if last
                        else onsets[index + 1] - SCHEDULE_LEAD_S
                    ),
                    key=module.response_key,
                    clock_zero_s=clock_zero_s,
                    presses=presses,
                )

                stats = monitor.stop()
                time_failed, xruns = cache.health_delta(item)
                db.set_trial_timing(
                    trial_ids[index],
                    TrialTiming(
                        # The scheduled onset, not a measured one — the same
                        # statement as everywhere else in the engine
                        # (engine/audio.reported_start_time).
                        audio_onset_s=onset - reference_s,
                        dropped_frames=stats.dropped_frames,
                        max_frame_interval_ms=stats.max_interval_ms,
                    ),
                )
                outcome.n_presented += 1
                if stats.dropped_frames:
                    outcome.dropped_frame_trials += 1
                if time_failed or xruns:
                    outcome.audio_glitch_trials += 1
                    logger.warning(
                        "Segment %d: ses zamanlaması bozuldu (TimeFailed %d, "
                        "XRuns %d).", index, time_failed, xruns,
                    )
                cache.release(item)
                index += 1
        except AbortSession:
            _flush_gin(db, module, planned, onsets, trial_ids, presses,
                       response_counts, state, outcome)
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            logger.warning(
                "Blok %d kesildi: %d/%d segment sunuldu.",
                block_index, outcome.n_presented, outcome.n_planned,
            )
            raise
        except Exception:
            outcome.status = SESSION_ABORTED
            db.finish_block(block_id, SESSION_ABORTED)
            raise

        _flush_gin(db, module, planned, onsets, trial_ids, presses,
                   response_counts, state, outcome)
        db.finish_block(block_id, SESSION_COMPLETED)
        logger.info(
            "Blok %d tamamlandı: %d segment, %s",
            block_index, outcome.n_presented, dict(outcome.categories),
        )

    if state.before_first:
        logger.info(
            "İlk segmentten önce %d tuş basımı: hiçbir denemeye ait değil, "
            "kaydedilmedi.", state.before_first,
        )
    return outcomes


# ----------------------------------------------------------------- internals


class _FlushState:
    """How much of the press buffer has already been written."""

    def __init__(self) -> None:
        self.flushed = 0
        self.before_first = 0


def _key(item: PlannedTrial) -> tuple[Path, str]:
    """Which prepared sound a trial needs: the file *and* the ear it goes to."""
    path = item.spec.audio_path
    if path is None:
        raise StreamError(f"Ses akışı denemesi ses dosyası taşımıyor: {item.spec.label}")
    return path, item.spec.ear


def _load_sounds(
    planned: list[PlannedTrial],
    *,
    calibration: Calibration | None,
    sample_rate: int,
    speaker: Any,
) -> dict[tuple[Path, str], Any]:
    """One buffered sound per distinct stimulus, built before the run.

    Two objects for three hundred tones: loading per trial would put file I/O
    into the inter-stimulus interval (§A.12), and there is nothing to gain from
    it — the stream presents the same two tones throughout.
    """
    sounds: dict[tuple[Path, str], Any] = {}
    for item in planned:
        key = _key(item)
        if key in sounds:
            continue
        path, ear = key
        stimulus = load_audio(
            path,
            ear=ear,
            burst_time_s=item.spec.audio_burst_s,
            calibration=calibration,
            expected_sample_rate=sample_rate,
        )
        sounds[key] = make_sound(stimulus, speaker)
    logger.info("Akış için %d ayrı uyaran belleğe alındı", len(sounds))
    return sounds


class _SegmentCache:
    """Sounds for a stream whose stimuli are too big to buffer all at once.

    GIN presents thirty distinct six-second segments — sixty with
    ``ear_selection: both`` — so the oddball approach of loading every stimulus
    before the run would hold hundreds of megabytes of decoded audio.  Each
    segment is read one trial ahead instead, which puts the file I/O in the
    inter-segment interval where §A.12 allows preparation, and never inside the
    250 ms before an onset.
    """

    def __init__(
        self,
        *,
        calibration: Calibration | None,
        sample_rate: int,
        speaker: Any,
    ) -> None:
        self._calibration = calibration
        self._sample_rate = sample_rate
        self._speaker = speaker
        self._sounds: dict[tuple[Path, str], Any] = {}
        self._health: dict[tuple[Path, str], tuple[int, int]] = {}

    def load(self, item: PlannedTrial) -> None:
        key = _key(item)
        if key in self._sounds:
            return
        path, ear = key
        stimulus = load_audio(
            path,
            ear=ear,
            burst_time_s=item.spec.audio_burst_s,
            calibration=self._calibration,
            expected_sample_rate=self._sample_rate,
        )
        self._sounds[key] = make_sound(stimulus, self._speaker)
        self._health.setdefault(key, (0, 0))

    def get(self, item: PlannedTrial) -> Any:
        key = _key(item)
        sound = self._sounds.get(key)
        if sound is None:  # pragma: no cover - load() is called one ahead
            self.load(item)
            sound = self._sounds[key]
        return sound

    def health_delta(self, item: PlannedTrial) -> tuple[int, int]:
        return _health_delta(self._sounds[_key(item)], self._health, _key(item))

    def release(self, item: PlannedTrial) -> None:
        """Drop a segment's decoded audio once it has been presented.

        The health counters are kept — they are two integers, and dropping them
        would make a reload read the backend's running totals as this segment's.
        """
        self._sounds.pop(_key(item), None)


def _hold(
    win: Any,
    fixation: Any,
    kb: Any,
    *,
    until_s: float,
    key: str,
    clock_zero_s: float,
    presses: list[float],
) -> None:
    """Flip until *until_s*, timestamping every press on the way.

    The flip rate bounds when a press is *noticed*, not when it happened: the
    timestamp comes from the keyboard's own clock, so a press seen one frame
    late is still recorded at the moment it was made.
    """
    import psychtoolbox as ptb

    def drain() -> None:
        for press in kb.getKeys(keyList=[key], waitRelease=False):
            presses.append(clock_zero_s + float(press.rt))

    while float(ptb.GetSecs()) < until_s:
        check_abort()
        drain()
        if fixation is not None:
            fixation.draw()
        win.flip()
    drain()


def _schedule(
    sound: Any, onset_s: float, params: TimingParams, outcome: BlockOutcome
) -> None:
    """Hand one tone to the backend for *onset_s*.

    A schedule that arrives after the onset is not a late tone, it is a
    different stream: PTB starts it immediately and the interval the design
    asked for never existed.  That is refused rather than recorded.
    """
    import psychtoolbox as ptb

    now = float(ptb.GetSecs())
    if now >= onset_s:
        raise StreamError(
            f"Ton planlama anı kaçırıldı: hedef {onset_s:.6f}, şimdi {now:.6f} "
            f"({(now - onset_s) * 1000:.0f} ms geç). Akış tasarlandığı gibi "
            "sunulamıyor."
        )
    if now > onset_s - params.schedule_margin_s:
        outcome.audio_glitch_trials += 1
        logger.warning(
            "Ton yalnızca %.1f ms önceden planlandı (gereken pay %.0f ms).",
            (onset_s - now) * 1000.0,
            params.schedule_margin_s * 1000.0,
        )
    sound.stop()
    sound.play(when=onset_s)


def _health_delta(
    sound: Any, health: dict[tuple[Path, str], tuple[int, int]], key: tuple[Path, str]
) -> tuple[int, int]:
    """``(time_failed, xruns)`` for the last tone only.

    PsychPortAudio's counters belong to the stream, not to one playback, and the
    same sound object serves every tone of its kind — so the difference is taken
    rather than the value.
    """
    total = playback_health(sound)
    previous = health[key]
    health[key] = total
    return total[0] - previous[0], total[1] - previous[1]


def _flush_gin(
    db: Database,
    module: GINConfig,
    planned: list[PlannedTrial],
    onsets: list[float],
    trial_ids: list[int],
    presses: list[float],
    response_counts: Counter[int],
    state: _FlushState,
    outcome: BlockOutcome,
) -> None:
    """Write the presses collected so far, each against the gap it answered.

    Two levels of attribution.  A press first belongs to the *segment* whose
    onset most recently preceded it — including one made during the
    inter-segment interval, which still answers the segment that just played.
    Inside that segment it belongs to the gap whose onset most recently preceded
    it (``gin.attribute_presses``), and the response window decides whether that
    is a detection.

    A press that followed no gap — every press of a catch segment — is written
    with ``event_index`` NULL and ``category = FALSE_ALARM``.  Dropping it would
    hide the participant the catch segments exist to find.

    A press in the interval *after* a gap's window has closed is a false alarm
    on that segment, not on the next one: the next segment has not started, and
    the participant pressed while there was nothing to detect.
    """
    known = onsets[: len(trial_ids)]
    for press_s in presses[state.flushed :]:
        index = bisect.bisect_right(known, press_s) - 1
        if index < 0:
            state.before_first += 1
            continue

        trial = planned[index].trial
        attributed = gin_module.attribute_presses(
            trial.design_extra["gap_onsets_s"],
            [press_s - known[index]],
            window_ms=module.response_window_ms,
        )[0]
        category = gin_module.category_of(attributed)
        outcome.categories[category] += 1

        trial_id = trial_ids[index]
        db.add_response(
            Response(
                trial_id=trial_id,
                response_index=response_counts[trial_id],
                # Which gap this answered.  NULL when it followed none, which is
                # what a press in a catch segment looks like.
                event_index=attributed.gap_index if attributed.in_window else None,
                raw_response=module.response_key,
                category=category,
                # There is no correct answer to record here: a detection is
                # already named by the category, and a false alarm is not an
                # incorrect answer to anything — it answers no gap at all.
                is_correct=None,
                # From the gap's own onset, and None for a press that followed
                # no gap: with nothing to measure from, a number would be an
                # interval to something the participant was not answering.
                rt_from_burst_ms=attributed.rt_ms if attributed.in_window else None,
                # A stream has no response prompt.
                rt_from_prompt_ms=None,
                input_device="keyboard",
            )
        )
        response_counts[trial_id] += 1
    state.flushed = len(presses)


def _flush(
    db: Database,
    module: OddballConfig,
    planned: list[PlannedTrial],
    onsets: list[float],
    trial_ids: list[int],
    presses: list[float],
    response_counts: Counter[int],
    state: _FlushState,
    outcome: BlockOutcome,
) -> None:
    """Write the presses collected so far as response rows.

    Attribution runs against the *whole* onset list, not the block's slice, so a
    press that arrived after its own block closed still lands on its own tone —
    it is simply committed with the next block.  A response row is a row; which
    block's commit carries it does not change what it says.
    """
    attributed, before_first = oddball_module.attribute_presses(
        onsets[: len(trial_ids)],
        presses[state.flushed :],
        window_ms=module.response_window_ms,
    )
    state.flushed = len(presses)
    state.before_first += before_first

    for press in attributed:
        trial_id = trial_ids[press.trial_index]
        is_target = (
            planned[press.trial_index].trial.design_extra.get("tone_type")
            == oddball_module.TARGET
        )
        if press.in_window:
            tally = oddball_module.HIT if is_target else oddball_module.FALSE_ALARM
        else:
            tally = oddball_module.OUTSIDE_WINDOW
        outcome.categories[tally] += 1

        db.add_response(
            Response(
                trial_id=trial_id,
                response_index=response_counts[trial_id],
                raw_response=module.response_key,
                # A press outside the window is not scored — it is neither a
                # hit nor a false alarm, and calling it either would move a
                # rate the participant did not produce.
                category=None if press.in_window else oddball_module.OUTSIDE_WINDOW,
                is_correct=is_target if press.in_window else None,
                # From the tone's onset.  There is no response prompt in a
                # stream, so the second reference is not applicable rather than
                # zero.
                rt_from_burst_ms=press.rt_ms,
                rt_from_prompt_ms=None,
                input_device="keyboard",
            )
        )
        response_counts[trial_id] += 1
