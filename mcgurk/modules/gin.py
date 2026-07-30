"""Modül 6 — GIN (Gaps-In-Noise): auditory temporal resolution.

No PsychoPy here, like every other design/scoring module: the segment order,
the attribution of key presses to gaps and the threshold rule are all checkable
in CI, against data whose answer is known.

The task is a run of broadband noise segments.  Silent gaps of 2–20 ms are cut
into them and the participant presses one key whenever they hear the noise stop.
The measure is the shortest gap duration they detect on at least four of its six
presentations (``threshold_criterion``).

Why it is in this study (EK_GIN §6.6): a wide temporal binding window (Modül 3)
need not be a difference in *multisensory* integration — it can be low-level
auditory temporal acuity.  GIN measures that acuity inside one modality, so the
two explanations can be separated.  Its role is the one oddball plays for
attention: a covariate that keeps the integration measures interpretable.

Four things here are easy to get wrong:

* **The unit of analysis is the gap, not the trial.**  A segment is one
  ``trials`` row and holds up to three gaps, so a hit has to name the gap it
  answered: ``responses.event_index`` indexes ``design_extra.gap_onsets_s``
  (schema version 4).  Without it the threshold could not be recomputed from the
  database.
* **A press is attributed first and scored second**, exactly as in oddball.  It
  belongs to the gap whose onset most recently preceded it;
  ``modules.gin.response_window_ms`` then decides whether it counts as a
  detection.  The config keeps that window shorter than the closest spacing
  between two gaps, so a press can never answer two of them.
* **A press that followed no gap is still written** — with ``event_index``
  NULL and ``category = FALSE_ALARM``.  The prepared set contains a catch
  segment with no gaps at all, and it measures exactly this.
* **A missed gap produces no row.**  It is the *absence* of a press, like an
  oddball miss or a timeout elsewhere; it is derived by comparing the gaps the
  trial carries with the ``event_index`` values that came back.

The segments themselves are not designed here.  They were cut offline in Adım 2
(§A.12) and the manifest records where every gap landed; this module chooses the
order they are presented in and reads the gap positions from the manifest, so
what the participant hears and what the database says cannot disagree.
"""

from __future__ import annotations

import bisect
import logging
import random
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config.schema import ExperimentConfig, GINConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
from ..stimuli.manifest import GinSegmentEntry, ManifestError, StimulusManifest
from .base import ModuleError, PlannedTrial, derive_seed, row_value

logger = logging.getLogger(__name__)

MODULE_NAME = "gin"

#: ``responses.category``.  A hit names the gap it answered through
#: ``event_index``; a false alarm names the gap it followed, or nothing at all
#: when it followed none.
HIT = "HIT"
FALSE_ALARM = "FALSE_ALARM"

#: Derived, never stored: a gap with no press is the absence of a row.
MISS = "MISS"

CATEGORIES = (HIT, FALSE_ALARM)

#: Monaural presentation only — see :func:`resolve_ear`.
MONAURAL_EARS = ("left", "right")


# --------------------------------------------------------------------- design


def resolve_ear(module: GINConfig, ear: str | None = None) -> list[str]:
    """Which ear(s) this participant is tested on.

    GIN is monaural: presenting it to a deaf ear measures nothing, so the side
    is a per-participant decision rather than a design factor.  Adım 8 makes
    that decision and passes it in; this function only says what the config
    allows.

    Raises:
        ModuleError: when ``ear_selection`` is ``good_ear`` and no ear was
            given.  Picking one silently would mean testing whichever side the
            code happened to default to, and the result would look like a
            measurement.
    """
    if ear is not None:
        if ear not in MONAURAL_EARS:
            raise ModuleError(
                f"GIN monaural bir testtir, kulak {MONAURAL_EARS} içinden "
                f"olmalı (verilen: {ear!r})"
            )
        return [ear]
    if module.ear_selection == "fixed":
        assert module.fixed_ear is not None  # the config validation guarantees it
        return [module.fixed_ear]
    if module.ear_selection == "both":
        return list(MONAURAL_EARS)
    raise ModuleError(
        "modules.gin.ear_selection 'good_ear' — hangi kulağın test edileceği "
        "katılımcının iyi kulağına bağlıdır ve oturum akışından gelir "
        "(Adım 8). Bu koşu için kulağı açıkça verin: --ear left|right"
    )


def plan_trials(
    config: ExperimentConfig,
    manifest: StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    ear: str | None = None,
    speaker_id: int | None = None,
) -> list[PlannedTrial]:
    """Build the module's trial list from the config and the prepared set.

    Args:
        seed: The **session** seed; the module's own stream is derived from it.
        stimuli_root: ``paths.stimuli``, already resolved.
        ear: Which ear to present to.  Required while ``ear_selection`` is
            ``good_ear`` (see :func:`resolve_ear`).
        speaker_id: Accepted and ignored — the noise segments have no speaker.
            The signature matches the other modules so the runner can treat
            them alike.

    Raises:
        ModuleError: the module is disabled, the prepared set does not hold the
            segments the design asks for, or the ear is undetermined.
    """
    del speaker_id  # noise has no speaker; kept for a uniform call signature
    module = config.modules.gin
    if not module.enabled:
        raise ModuleError(
            "modules.gin.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )

    ears = resolve_ear(module, ear)
    segments = _segments(manifest, module)
    rng = random.Random(derive_seed(seed, MODULE_NAME))

    planned: list[PlannedTrial] = []
    for side in ears:
        # Shuffled per ear rather than once: with ``ear_selection: both`` the
        # same order twice would let the second run be answered from memory of
        # the first, and the gaps sit at fixed positions inside each segment.
        order = list(segments)
        rng.shuffle(order)
        planned.extend(
            _plan_one(entry, ear=side, stimuli_root=stimuli_root) for entry in order
        )

    logger.info(
        "GIN tasarımı: %d segment x %d kulak = %d deneme, %d boşluk, kulak %s, "
        "tohum %d",
        len(segments),
        len(ears),
        len(planned),
        sum(len(item.trial.design_extra["gap_onsets_s"]) for item in planned),
        "/".join(ears),
        seed,
    )
    return planned


def _segments(
    manifest: StimulusManifest, module: GINConfig
) -> list[GinSegmentEntry]:
    """The prepared segments, checked against the design they have to satisfy.

    The gaps were cut offline and measured from disk (Adım 2), so the design is
    verified against the *set* rather than regenerated: a mismatch means the
    config changed after the stimuli were prepared, and presenting them anyway
    would put one design in the report and another in the participant's ears.
    """
    segments = sorted(manifest.gin_segments, key=lambda entry: entry.index)
    if not segments:
        raise ModuleError(
            "Manifest'te GIN segmenti yok. Uyaran seti bu tasarımla "
            "hazırlanmamış: python tools/prepare_stimuli.py"
        )
    if len(segments) != module.n_segments:
        raise ModuleError(
            f"Hazırlanmış sette {len(segments)} GIN segmenti var, config "
            f"{module.n_segments} istiyor. Uyaran seti yeniden hazırlanmalı: "
            "python tools/prepare_stimuli.py --force"
        )

    counted: Counter[float] = Counter(
        duration for entry in segments for duration in entry.gap_durations_ms
    )
    expected = {
        duration: module.reps_per_gap for duration in module.gap_durations_ms
    }
    if dict(counted) != expected:
        raise ModuleError(
            "Hazırlanmış setteki boşluk dağılımı config ile uyuşmuyor.\n"
            f"  sette : {dict(sorted(counted.items()))}\n"
            f"  config: {dict(sorted(expected.items()))}\n"
            "Uyaran seti yeniden hazırlanmalı: python tools/prepare_stimuli.py "
            "--force"
        )
    return segments


def _plan_one(
    entry: GinSegmentEntry, *, ear: str, stimuli_root: Path
) -> PlannedTrial:
    try:
        path = entry.file.resolve(stimuli_root)
    except ManifestError as exc:  # pragma: no cover - MediaFile.resolve is total
        raise ModuleError(str(exc)) from exc

    # The gap count is not in the label: it is in ``design_extra`` already, and
    # ``condition_label`` is what the operator's log and the cell table print.
    label = f"segment {entry.index:02d}"
    spec = TrialSpec(
        label=label,
        audio_path=path,
        # The stimulus is noise: there is no acoustic burst to align anything
        # to, and nothing is aligned to it — the events are the gaps, and their
        # onsets are measured from the start of the segment.
        audio_burst_s=0.0,
        ear=ear,
    )
    trial = Trial(
        block_id=0,  # the runner fills this in
        trial_index=0,
        module=MODULE_NAME,
        condition_label=label,
        visual_token=None,
        audio_token=None,
        ear=ear,
        snr_db=None,
        # NULL, not "quiet": the stimulus *is* noise, so "presented in noise"
        # does not describe a condition here.  NULL means not applicable, the
        # same as on an AVSR V-only trial.
        noise_condition=None,
        nominal_soa_ms=None,
        presentation_mode="A",
        design_extra={
            "segment_index": entry.index,
            "gap_onsets_s": list(entry.gap_onsets_s),
            "gap_durations_ms": list(entry.gap_durations_ms),
        },
    )
    return PlannedTrial(spec=spec, trial=trial)


def gap_onsets(planned: Sequence[PlannedTrial]) -> list[list[float]]:
    """Gap onsets per trial, in seconds from that segment's start."""
    return [list(item.trial.design_extra["gap_onsets_s"]) for item in planned]


def ears_presented(planned: Sequence[PlannedTrial]) -> list[str]:
    """Which ears the plan actually presents to, in presentation order."""
    seen: list[str] = []
    for item in planned:
        ear = item.trial.ear
        if ear is not None and ear not in seen:
            seen.append(ear)
    return seen


def stream_duration_s(planned: Sequence[PlannedTrial], module: GINConfig) -> float:
    """How long the run takes, from the design rather than from a stopwatch."""
    per_trial = module.segment_duration_s + module.inter_segment_interval_s
    return module.lead_in_s + len(planned) * per_trial


# ---------------------------------------------------------------- attribution


@dataclass(frozen=True)
class AttributedPress:
    """One key press, assigned to the gap it followed inside one segment."""

    #: Index into that trial's ``gap_onsets_s``; None when the press arrived
    #: before the segment's first gap — or in a catch segment, which has none.
    gap_index: int | None
    #: Milliseconds from that gap's onset.  None when there is no gap to
    #: measure from.
    rt_ms: float | None
    #: Whether it landed inside ``response_window_ms``.  Only then is it a
    #: detection of that gap.
    in_window: bool


def attribute_presses(
    onsets_s: Sequence[float],
    press_times_s: Iterable[float],
    *,
    window_ms: tuple[float, float],
) -> list[AttributedPress]:
    """Assign each press inside one segment to a gap.

    *press_times_s* and *onsets_s* are both measured from the segment's own
    onset.  A press belongs to the gap whose onset most recently preceded it,
    which is unambiguous because the config keeps the response window shorter
    than the closest spacing between two gaps.

    A press before the first gap — every press of a catch segment — is returned
    with ``gap_index=None``.  It is a false alarm and it is recorded as one:
    dropping it would hide the participant this task is designed to find.
    """
    low, high = window_ms
    onsets = list(onsets_s)
    attributed: list[AttributedPress] = []
    for time_s in press_times_s:
        index = bisect.bisect_right(onsets, time_s) - 1
        if index < 0:
            attributed.append(
                AttributedPress(gap_index=None, rt_ms=None, in_window=False)
            )
            continue
        rt_ms = (time_s - onsets[index]) * 1000.0
        attributed.append(
            AttributedPress(
                gap_index=index,
                rt_ms=rt_ms,
                in_window=low <= rt_ms <= high,
            )
        )
    return attributed


def category_of(press: AttributedPress) -> str:
    """What one attributed press is: a detection, or a false alarm.

    There is no third case.  Unlike oddball — where a press outside the window
    is recorded as ``OUTSIDE_WINDOW`` because the tone it followed may well have
    deserved a response — a GIN press outside every gap's window answered no
    gap, and "the participant pressed when there was nothing to hear" is the
    definition of a false alarm here (EK_GIN §"Ölçülen Değişkenler").
    """
    return HIT if press.in_window else FALSE_ALARM


# -------------------------------------------------------------------- measures


@dataclass(frozen=True)
class GapDetection:
    """One gap duration: how often it was presented, how often it was detected."""

    duration_ms: float
    n_presented: int = 0
    n_detected: int = 0

    @property
    def detection_rate(self) -> float | None:
        return self.n_detected / self.n_presented if self.n_presented else None


@dataclass(frozen=True)
class GINMeasures:
    """Everything EK_GIN §"Ölçülen Değişkenler" asks for.

    ``threshold_ms`` is None when no duration met the criterion — an honest
    "not reached" rather than the longest gap, which would be a threshold the
    data never showed.  It is always reported next to ``n_false_alarms``: a
    participant who presses often detects short gaps by chance, and a threshold
    read without the false-alarm count would flatter exactly them (EK_GIN
    §"Yorumlama Sınırları").
    """

    by_duration: tuple[GapDetection, ...] = ()
    threshold_ms: float | None = None
    criterion: str = ""
    n_gaps: int = 0
    n_detected: int = 0
    n_false_alarms: int = 0
    n_trials: int = 0
    mean_rt_ms: float | None = None
    sd_rt_ms: float | None = None
    ears: tuple[str, ...] = ()

    @property
    def detection_rate(self) -> float | None:
        """Detected gaps over presented gaps — EK_GIN's "toplam saptama yüzdesi"."""
        return self.n_detected / self.n_gaps if self.n_gaps else None


#: Shared with the other modules' measures (``base.row_value``).
_field = row_value


@dataclass
class _TrialGaps:
    """One segment's gaps and the presses that came back for them."""

    durations_ms: list[float] = field(default_factory=list)
    detected: set[int] = field(default_factory=set)
    false_alarms: int = 0
    rts: list[float] = field(default_factory=list)
    ear: str | None = None


def _collect(rows: Iterable[Any]) -> dict[Any, _TrialGaps]:
    """Group ``v_trials_flat`` rows by trial, keeping each trial's gaps.

    ``v_trials_flat`` LEFT JOINs ``responses``, so a segment that got no press
    at all is still one row — with every response column NULL.  That row is what
    makes its gaps count as missed rather than vanish.
    """
    trials: dict[Any, _TrialGaps] = {}
    for row in rows:
        module = _field(row, "module")
        if module is not None and module != MODULE_NAME:
            continue
        trial_id = _field(row, "trial_id")
        state = trials.get(trial_id)
        if state is None:
            state = _TrialGaps(
                durations_ms=_gap_durations(row), ear=_field(row, "ear")
            )
            trials[trial_id] = state

        category = _field(row, "category")
        if category is None:
            continue
        if category not in CATEGORIES:
            raise ModuleError(
                f"GIN denemesinde bilinmeyen kategori: {category!r}. "
                f"Beklenen: {list(CATEGORIES)}"
            )
        if category == FALSE_ALARM:
            state.false_alarms += 1
            continue

        index = _field(row, "event_index")
        if index is None:
            raise ModuleError(
                "GIN isabetinde event_index boş — hangi boşluğun saptandığı "
                "kaydedilmemiş, eşik hesaplanamaz"
            )
        index = int(index)
        if not 0 <= index < len(state.durations_ms):
            raise ModuleError(
                f"GIN isabetinin event_index'i ({index}) denemenin boşluk "
                f"sayısının ({len(state.durations_ms)}) dışında"
            )
        state.detected.add(index)
        rt = _field(row, "rt_from_burst_ms")
        if rt is not None:
            state.rts.append(float(rt))
    return trials


def _gap_durations(row: Any) -> list[float]:
    """``gap_durations_ms`` from a flat row, whose value is JSON text."""
    import json

    raw = _field(row, "gin_gap_durations_ms")
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModuleError(
                f"GIN denemesinin gap_durations_ms alanı JSON değil: {raw!r}"
            ) from exc
    if not isinstance(raw, list):
        raise ModuleError(f"GIN denemesinin gap_durations_ms alanı liste değil: {raw!r}")
    return [float(value) for value in raw]


def detection_by_duration(rows: Iterable[Any]) -> list[GapDetection]:
    """Presented and detected counts per gap duration, shortest first."""
    presented: Counter[float] = Counter()
    detected: Counter[float] = Counter()
    for state in _collect(rows).values():
        for index, duration in enumerate(state.durations_ms):
            presented[duration] += 1
            if index in state.detected:
                detected[duration] += 1
    return [
        GapDetection(
            duration_ms=duration,
            n_presented=presented[duration],
            n_detected=detected[duration],
        )
        for duration in sorted(presented)
    ]


def threshold_ms(
    by_duration: Sequence[GapDetection], *, hits: int, presentations: int
) -> float | None:
    """The shortest gap duration detected on at least *hits* of its presentations.

    The rule is the standard one (``4_of_6``) and it is applied to the shortest
    qualifying duration rather than to the shortest run of qualifying durations:
    a participant can miss 4 ms and catch 3 ms by chance, and taking the longer
    one instead would be a different, undocumented criterion.  The non-monotonic
    case is visible in the per-duration table beside the number.

    Returns None when no duration qualifies — the threshold was not reached
    inside the tested range, which is a finding rather than a number.
    """
    for point in sorted(by_duration, key=lambda item: item.duration_ms):
        if point.n_presented < presentations:
            # An incomplete run cannot meet a criterion defined over a fixed
            # number of presentations; a partial run is reported, not scored.
            continue
        if point.n_detected >= hits:
            return point.duration_ms
    return None


def measures_from_rows(rows: Iterable[Any], module: GINConfig) -> GINMeasures:
    """Every measure of the module, from ``v_trials_flat`` rows."""
    rows = list(rows)
    trials = _collect(rows)
    by_duration = detection_by_duration(rows)
    hits, presentations = module.threshold_rule()

    all_rts = [rt for state in trials.values() for rt in state.rts]
    ears = sorted({state.ear for state in trials.values() if state.ear is not None})
    return GINMeasures(
        by_duration=tuple(by_duration),
        threshold_ms=threshold_ms(
            by_duration, hits=hits, presentations=presentations
        ),
        criterion=module.threshold_criterion,
        n_gaps=sum(point.n_presented for point in by_duration),
        n_detected=sum(point.n_detected for point in by_duration),
        n_false_alarms=sum(state.false_alarms for state in trials.values()),
        n_trials=len(trials),
        mean_rt_ms=statistics.fmean(all_rts) if all_rts else None,
        sd_rt_ms=statistics.stdev(all_rts) if len(all_rts) > 1 else None,
        ears=tuple(ears),
    )


def summarise_measures(rows: Iterable[Any], module: GINConfig) -> str:
    """The module's measures as a block of text, for the operator's console."""
    measures = measures_from_rows(rows, module)
    hits, presentations = module.threshold_rule()

    lines = ["Boşluk saptama (süre başına):"]
    lines.append(f"  {'süre (ms)':>10}{'saptanan':>10}{'sunulan':>9}{'oran':>8}")
    for point in measures.by_duration:
        rate = point.detection_rate
        shown = "—" if rate is None else f"%{100 * rate:.0f}"
        marker = "  <-- eşik" if point.duration_ms == measures.threshold_ms else ""
        lines.append(
            f"  {point.duration_ms:>10.0f}{point.n_detected:>10}"
            f"{point.n_presented:>9}{shown:>8}{marker}"
        )

    threshold = measures.threshold_ms
    lines.append(
        "Eşik                   : "
        + ("ulaşılamadı" if threshold is None else f"{threshold:g} ms")
        + f"  ({presentations} sunumun en az {hits}'inde saptanan en kısa süre)"
    )
    if threshold is None:
        lines.append(
            f"  (test edilen aralıkta hiçbir süre {module.threshold_criterion} "
            "ölçütünü sağlamadı — eşik bu aralığın dışında)"
        )
    rate = measures.detection_rate
    lines.append(
        "Toplam saptama         : "
        + ("—" if rate is None else f"%{100 * rate:.1f}")
        + f" ({measures.n_detected}/{measures.n_gaps})"
    )
    # Always beside the threshold: a participant who presses often detects short
    # gaps by chance, and the threshold alone would flatter exactly them.
    lines.append(f"Yanlış alarm           : {measures.n_false_alarms}")
    if measures.mean_rt_ms is None:
        lines.append("Saptama RT             : —")
    else:
        sd = "" if measures.sd_rt_ms is None else f" (SD {measures.sd_rt_ms:.0f})"
        lines.append(
            f"Saptama RT             : {measures.mean_rt_ms:.0f} ms{sd}, "
            f"n={measures.n_detected}"
        )
    lines.append(f"Test edilen kulak      : {'/'.join(measures.ears) or '—'}")
    return "\n".join(lines)


# ---------------------------------------------------------------- inspection


def cell_counts(planned: Sequence[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(gap count, stimulus, ear, noise)``.

    Grouped by how many gaps a segment holds rather than by segment: thirty rows
    of one would not be a table anyone reads, and what the operator checks here
    is that the catch segments and the three-gap segments are both there.
    """
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        n_gaps = len(trial.design_extra["gap_onsets_s"])
        counts[
            (
                f"{n_gaps} boşluk",
                "geniş bantlı gürültü",
                str(trial.ear),
                "—",
            )
        ] += 1
    return dict(counts)
