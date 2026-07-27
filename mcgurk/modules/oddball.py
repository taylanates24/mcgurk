"""Modül 4 — Oddball: the auditory attention control task.

No PsychoPy here, like ``mcgurk.py``, ``avsr.py`` and ``tbw.py``: the sequence,
the attribution of key presses to tones and the signal-detection measures are
all checkable in CI, against data whose right answer is known.

The task is a continuous stream of short tones.  Most are the standard; a
minority are the target, and the participant presses one key when they hear one.
Nothing about it is audiovisual — it exists so that a group difference in the
other three modules can be told apart from a group difference in *attention*.  A
participant who cannot hold a simple detection task for five minutes has not
demonstrated anything about multisensory integration.

Four things here are easy to get wrong:

* **A stream has no trials, so a trial has to be defined.**  One ``trials`` row
  per tone, and a press belongs to the tone whose onset most recently preceded
  it.  ``response_window_ms`` decides whether that press counts as a response to
  it; the config refuses a window longer than the shortest ISI, so a press can
  never belong to two tones.
* **The window is a design parameter.**  It is in the config and it is fixed
  before data collection: chosen afterwards, it becomes a way of choosing the
  hit and false-alarm rates after seeing them.
* **A press outside every window is still data.**  It is written against the
  preceding tone with ``category = OUTSIDE_WINDOW`` and no correctness, so a
  participant who pressed at random is visible in QC without their presses
  entering the hit or false-alarm count.
* **A miss and a correct rejection produce no row.**  Both are the *absence* of
  a press, and inventing a row for them would put the analyst's interpretation
  into the data.  They are derived from ``v_trials_flat`` — which keeps the
  trial visible through a LEFT JOIN — exactly like a timeout elsewhere.
"""

from __future__ import annotations

import bisect
import logging
import random
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from scipy.stats import norm

from ..config.schema import ExperimentConfig, OddballConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
from ..stimuli.manifest import ManifestError, StimulusManifest
from .base import QUIET, ModuleError, PlannedTrial, derive_seed, row_value

logger = logging.getLogger(__name__)

MODULE_NAME = "oddball"

#: ``trials.design_extra.tone_type``.
STANDARD = "standard"
TARGET = "target"

#: ``responses.category`` for a press that arrived outside the response window
#: of the tone it followed.  It is not scored — ``is_correct`` stays NULL — but
#: it is recorded: a participant pressing at random has to be visible.
OUTSIDE_WINDOW = "OUTSIDE_WINDOW"

#: The four signal-detection outcomes of a trial.  Derived, never stored: two
#: of them are the absence of a response row.
HIT = "HIT"
MISS = "MISS"
FALSE_ALARM = "FALSE_ALARM"
CORRECT_REJECTION = "CORRECT_REJECTION"


# --------------------------------------------------------------------- design


@dataclass(frozen=True)
class Tone:
    """One planned tone."""

    is_target: bool
    frequency_hz: float
    #: Nominal interval from the previous tone's onset; None for the first.
    isi_ms: float | None

    @property
    def tone_type(self) -> str:
        return TARGET if self.is_target else STANDARD

    @property
    def label(self) -> str:
        """``trials.condition_label`` — readable in the operator's log."""
        return f"{self.tone_type} {self.frequency_hz:g} Hz"


def target_positions(
    n_trials: int, n_targets: int, min_standards: int, rng: random.Random
) -> list[int]:
    """Where the targets go, drawn uniformly from the sequences that are legal.

    Legal means: at least *min_standards* standards before every target,
    including the first one.  The leading run matters — a deviant presented
    before any standard has been established is not a deviant, it is just the
    first tone — and it costs nothing here: 54 targets at a spacing of two need
    162 of the 300 trials.

    The draw is uniform over all legal sequences rather than greedy.  Placing
    targets one at a time and re-rolling on a collision biases them towards the
    end of the stream, where the free space accumulates, and the second half of
    an attention task is precisely where the target rate has to stay constant.

    Returns:
        Target indices, ascending.

    Raises:
        ModuleError: when the constraint cannot be satisfied at all.
    """
    if n_targets < 1:
        raise ModuleError(f"En az bir hedef gerekir (verilen: {n_targets})")
    if min_standards < 0:
        raise ModuleError("min_standards_between_targets negatif olamaz")

    n_standards = n_trials - n_targets
    free = n_standards - n_targets * min_standards
    if free < 0:
        raise ModuleError(
            f"{n_targets} hedefin her birinin önünde {min_standards} standart "
            f"olması için {n_targets * (1 + min_standards)} deneme gerekir, "
            f"{n_trials} var"
        )

    # A uniformly random composition of `free` spare standards into the
    # n_targets + 1 gaps: pick the bar positions of the stars-and-bars picture.
    bars = sorted(rng.sample(range(free + n_targets), n_targets))
    spare = [bars[0]]
    for previous, current in zip(bars, bars[1:], strict=False):
        spare.append(current - previous - 1)

    positions: list[int] = []
    index = 0
    for extra in spare:
        index += extra + min_standards
        positions.append(index)
        index += 1
    return positions


def build_sequence(module: OddballConfig, rng: random.Random) -> list[bool]:
    """The whole stream as ``is_target`` flags."""
    positions = set(
        target_positions(
            module.n_trials,
            module.n_targets(),
            module.min_standards_between_targets,
            rng,
        )
    )
    return [index in positions for index in range(module.n_trials)]


def draw_intervals(module: OddballConfig, rng: random.Random, n: int) -> list[float]:
    """The *n* inter-stimulus intervals of an ``n + 1`` tone stream, in ms.

    Jittered so the stream does not become a rhythm the participant can
    anticipate; ``isi_ms`` in the config is the range.
    """
    low, high = module.isi_ms
    return [round(rng.uniform(low, high), 1) for _ in range(max(0, n))]


def onset_times(intervals_ms: Sequence[float], start_s: float) -> list[float]:
    """Absolute onset of every tone from the interval list.

    The onsets are cumulative from one origin rather than each computed from
    the previous *realised* one: a stream that re-references itself every tone
    accumulates whatever the scheduler was late by, and after 300 tones the
    error is no longer a per-trial one.
    """
    onsets = [start_s]
    for interval in intervals_ms:
        onsets.append(onsets[-1] + interval / 1000.0)
    return onsets


def plan_trials(
    config: ExperimentConfig,
    manifest: StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    speaker_id: int | None = None,
) -> list[PlannedTrial]:
    """Build the stream from the config and the prepared tones.

    Args:
        seed: The **session** seed; the module's own stream is derived from it.
        stimuli_root: ``paths.stimuli``, already resolved.
        speaker_id: Accepted for symmetry with the audiovisual modules and
            ignored — a tone has no speaker.

    Raises:
        ModuleError: the module is disabled or the tones are not prepared.
    """
    module = config.modules.oddball
    if not module.enabled:
        raise ModuleError(
            "modules.oddball.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )
    del speaker_id

    rng = random.Random(derive_seed(seed, MODULE_NAME))
    flags = build_sequence(module, rng)
    intervals = draw_intervals(module, rng, len(flags) - 1)

    try:
        paths = {
            frequency: manifest.tone(frequency).file.resolve(stimuli_root)
            for frequency in module.tone_frequencies()
        }
    except ManifestError as exc:
        raise ModuleError(str(exc)) from exc

    ear = module.ears[0]
    planned: list[PlannedTrial] = []
    for index, is_target in enumerate(flags):
        frequency = module.target_hz if is_target else module.standard_hz
        tone = Tone(
            is_target=is_target,
            frequency_hz=frequency,
            isi_ms=None if index == 0 else intervals[index - 1],
        )
        planned.append(
            PlannedTrial(
                spec=TrialSpec(
                    label=tone.label,
                    audio_path=paths[frequency],
                    # The tone starts at the file's first sample (the ramp is
                    # part of it), so the RT reference is the file onset.
                    audio_burst_s=0.0,
                    ear=ear,
                ),
                trial=Trial(
                    block_id=0,  # the runner fills this in
                    trial_index=0,
                    module=MODULE_NAME,
                    condition_label=tone.label,
                    ear=ear,
                    snr_db=None,
                    noise_condition=QUIET,
                    presentation_mode="A",
                    design_extra={
                        "tone_type": tone.tone_type,
                        "tone_hz": frequency,
                        "isi_ms": tone.isi_ms,
                    },
                ),
            )
        )

    logger.info(
        "Oddball tasarımı: %d ton (%d hedef, %%%.1f), ISI %g-%g ms, "
        "kulak %s, tohum %d",
        len(planned),
        sum(flags),
        100.0 * sum(flags) / len(flags),
        module.isi_ms[0],
        module.isi_ms[1],
        ear,
        seed,
    )
    return planned


# ---------------------------------------------------------------- attribution


@dataclass(frozen=True)
class AttributedPress:
    """One key press, assigned to the tone it followed."""

    trial_index: int
    #: Milliseconds from that tone's onset.
    rt_ms: float
    #: Whether it landed inside ``response_window_ms``.  A press outside it is
    #: recorded but not scored.
    in_window: bool


def attribute_presses(
    onsets_s: Sequence[float],
    press_times_s: Iterable[float],
    *,
    window_ms: tuple[float, float],
) -> tuple[list[AttributedPress], int]:
    """Assign each press to a tone.

    Every press belongs to the tone whose onset most recently preceded it.  That
    is unambiguous because the config keeps the response window shorter than the
    shortest ISI: a press inside a tone's window cannot also be inside the
    previous tone's.

    Returns:
        ``(attributed, n_before_first)`` — presses that arrived before the first
        tone belong to no trial and are only counted.
    """
    low, high = window_ms
    onsets = list(onsets_s)
    attributed: list[AttributedPress] = []
    before_first = 0

    for time_s in press_times_s:
        index = bisect.bisect_right(onsets, time_s) - 1
        if index < 0:
            before_first += 1
            continue
        rt_ms = (time_s - onsets[index]) * 1000.0
        attributed.append(
            AttributedPress(
                trial_index=index,
                rt_ms=rt_ms,
                in_window=low <= rt_ms <= high,
            )
        )
    return attributed, before_first


# ------------------------------------------------------------------- measures


@dataclass(frozen=True)
class TrialOutcome:
    """What one tone produced: one of the four detection outcomes."""

    trial_id: int
    is_target: bool
    outcome: str
    #: RT of the press that counted, in ms from tone onset.  None unless the
    #: outcome is a hit or a false alarm.
    rt_ms: float | None = None
    #: Presses on this tone that fell outside the window.
    n_outside: int = 0


@dataclass(frozen=True)
class Counts:
    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    correct_rejections: int = 0
    outside_window: int = 0

    @property
    def n_targets(self) -> int:
        return self.hits + self.misses

    @property
    def n_standards(self) -> int:
        return self.false_alarms + self.correct_rejections

    @property
    def n_trials(self) -> int:
        return self.n_targets + self.n_standards


@dataclass(frozen=True)
class DetectionMeasures:
    """Sensitivity and bias, with the counts they came from."""

    counts: Counts
    #: Observed proportions, uncorrected — what the counts actually say.
    hit_rate: float
    false_alarm_rate: float
    #: Log-linear corrected, which is what d' and c are computed from.
    d_prime: float
    criterion: float
    mean_rt_ms: float | None = None
    sd_rt_ms: float | None = None
    n_rt: int = 0


def trial_outcomes(rows: Iterable[object]) -> list[TrialOutcome]:
    """Group ``v_trials_flat`` rows into one outcome per tone.

    A tone with no response row is a miss (target) or a correct rejection
    (standard): the two outcomes that consist of *not* pressing produce no row,
    so they are read off the LEFT JOIN's empty response columns.
    """
    order: list[int] = []
    tone_types: dict[int, str] = {}
    scored: dict[int, float | None] = {}
    outside: Counter[int] = Counter()

    for row in rows:
        module = row_value(row, "module")
        if module is not None and module != MODULE_NAME:
            continue
        trial_id = row_value(row, "trial_id")
        if trial_id is None:
            raise ModuleError("Oddball satırında trial_id yok")
        trial_id = int(trial_id)
        if trial_id not in tone_types:
            order.append(trial_id)
            tone_type = row_value(row, "oddball_tone_type")
            if tone_type not in (STANDARD, TARGET):
                raise ModuleError(
                    f"Oddball denemesinde bilinmeyen ton tipi: {tone_type!r}. "
                    f"Beklenen: {STANDARD!r} veya {TARGET!r}"
                )
            tone_types[trial_id] = str(tone_type)

        if row_value(row, "response_id") is None:
            continue
        if row_value(row, "category") == OUTSIDE_WINDOW:
            outside[trial_id] += 1
            continue
        rt = row_value(row, "rt_from_burst_ms")
        # The first press inside the window is the response; a second one adds
        # nothing to a detection outcome that has already happened.
        if trial_id not in scored:
            scored[trial_id] = None if rt is None else float(rt)

    outcomes: list[TrialOutcome] = []
    for trial_id in order:
        is_target = tone_types[trial_id] == TARGET
        pressed = trial_id in scored
        if is_target:
            outcome = HIT if pressed else MISS
        else:
            outcome = FALSE_ALARM if pressed else CORRECT_REJECTION
        outcomes.append(
            TrialOutcome(
                trial_id=trial_id,
                is_target=is_target,
                outcome=outcome,
                rt_ms=scored.get(trial_id),
                n_outside=outside[trial_id],
            )
        )
    return outcomes


def count_outcomes(outcomes: Iterable[TrialOutcome]) -> Counts:
    tally: Counter[str] = Counter()
    outside = 0
    for outcome in outcomes:
        tally[outcome.outcome] += 1
        outside += outcome.n_outside
    return Counts(
        hits=tally[HIT],
        misses=tally[MISS],
        false_alarms=tally[FALSE_ALARM],
        correct_rejections=tally[CORRECT_REJECTION],
        outside_window=outside,
    )


def detection_measures(
    counts: Counts, rts_ms: Sequence[float] | None = None
) -> DetectionMeasures:
    """d' and criterion, with the log-linear correction applied.

    A perfect participant — every target hit, no false alarm — has rates of 1
    and 0, whose z scores are infinite.  The log-linear correction (Hautus,
    1995) adds 0.5 to each count and 1 to each total *always*, not only when a
    rate is extreme: correcting conditionally makes the estimator discontinuous
    exactly where the data is most common in an easy task like this one.

    The reported ``hit_rate`` and ``false_alarm_rate`` are the uncorrected
    proportions, because those are what the counts say; only d' and the
    criterion use the corrected ones.

    One consequence is worth knowing before reading a table of these numbers:
    with unequal totals (54 targets against 246 standards) the correction moves
    the two rates by different amounts, so a participant who pressed at *every*
    tone comes out at a small negative d' rather than exactly zero.  It is the
    criterion, not d', that identifies them.

    Raises:
        ModuleError: when the stream contained no target or no standard, in
            which case neither rate exists.
    """
    if counts.n_targets == 0 or counts.n_standards == 0:
        raise ModuleError(
            f"d' hesaplanamaz: {counts.n_targets} hedef, {counts.n_standards} "
            "standart deneme — iki oran da gerekiyor"
        )

    hit_rate = counts.hits / counts.n_targets
    false_alarm_rate = counts.false_alarms / counts.n_standards
    corrected_hit = (counts.hits + 0.5) / (counts.n_targets + 1)
    corrected_fa = (counts.false_alarms + 0.5) / (counts.n_standards + 1)
    z_hit = float(norm.ppf(corrected_hit))
    z_fa = float(norm.ppf(corrected_fa))

    values = [float(rt) for rt in (rts_ms or [])]
    return DetectionMeasures(
        counts=counts,
        hit_rate=hit_rate,
        false_alarm_rate=false_alarm_rate,
        d_prime=z_hit - z_fa,
        criterion=-0.5 * (z_hit + z_fa),
        mean_rt_ms=statistics.fmean(values) if values else None,
        sd_rt_ms=statistics.stdev(values) if len(values) > 1 else None,
        n_rt=len(values),
    )


def measures_from_rows(rows: Iterable[object]) -> DetectionMeasures:
    """:func:`detection_measures` straight from ``v_trials_flat`` rows."""
    outcomes = trial_outcomes(rows)
    hits = [o.rt_ms for o in outcomes if o.outcome == HIT and o.rt_ms is not None]
    return detection_measures(count_outcomes(outcomes), hits)


def summarise_measures(rows: Iterable[object]) -> str:
    """The module's measures as a block of text, for the operator's console."""
    outcomes = trial_outcomes(rows)
    if not outcomes:
        return "Oddball: kayıtlı deneme yok."
    counts = count_outcomes(outcomes)

    lines = [
        "Sinyal tespiti:",
        f"  {'Isabet':<20}{counts.hits:>5} / {counts.n_targets}",
        f"  {'Kaçırma':<20}{counts.misses:>5}",
        f"  {'Yanlış alarm':<20}{counts.false_alarms:>5} / {counts.n_standards}",
        f"  {'Doğru ret':<20}{counts.correct_rejections:>5}",
        f"  {'Pencere dışı basım':<20}{counts.outside_window:>5}",
    ]
    try:
        measures = detection_measures(
            counts,
            [o.rt_ms for o in outcomes if o.outcome == HIT and o.rt_ms is not None],
        )
    except ModuleError as exc:
        lines.append(f"Ölçüt hesaplanamadı: {exc}")
        return "\n".join(lines)

    lines.extend(
        [
            f"Isabet oranı           : %{100 * measures.hit_rate:.1f}",
            f"Yanlış alarm oranı     : %{100 * measures.false_alarm_rate:.1f}",
            f"d'                     : {measures.d_prime:.2f}",
            f"Kriter (c)             : {measures.criterion:+.2f}",
            # The correction is stated, not implied: a d' of 3.8 from a perfect
            # participant is a bounded estimate, not an infinite sensitivity.
            "  (d' ve c log-lineer düzeltmeli: paylara +0.5, toplamlara +1)",
        ]
    )
    if measures.mean_rt_ms is not None:
        spread = (
            f" (SD {measures.sd_rt_ms:.0f})" if measures.sd_rt_ms is not None else ""
        )
        lines.append(
            f"Isabet RT (ort)        : {measures.mean_rt_ms:.0f} ms{spread}, "
            f"n={measures.n_rt}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- inspection


def target_gaps(planned: Sequence[PlannedTrial]) -> list[int]:
    """Standards between consecutive targets, and before the first one.

    What the ``min_standards_between_targets`` constraint is about, read off the
    plan that will actually run rather than recomputed from the config.
    """
    indices = [
        index
        for index, item in enumerate(planned)
        if item.trial.design_extra.get("tone_type") == TARGET
    ]
    if not indices:
        return []
    gaps = [indices[0]]
    gaps += [
        later - earlier - 1
        for earlier, later in zip(indices, indices[1:], strict=False)
    ]
    return gaps


def stream_duration_s(planned: Sequence[PlannedTrial], module: OddballConfig) -> float:
    """How long the stream lasts, from the drawn intervals."""
    total_ms = sum(
        float(item.trial.design_extra.get("isi_ms") or 0.0) for item in planned
    )
    return module.lead_in_s + total_ms / 1000.0 + module.tone_duration_ms / 1000.0


def cell_counts(planned: Sequence[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(label, stimulus, ear, noise)``."""
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        frequency = trial.design_extra.get("tone_hz")
        counts[
            (
                str(trial.design_extra.get("tone_type")),
                f"{float(frequency or 0.0):g} Hz",
                str(trial.ear),
                QUIET,
            )
        ] += 1
    return dict(counts)
