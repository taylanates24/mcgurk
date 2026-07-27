"""Modül 3 — TBW: the temporal binding window, from simultaneity judgements.

No PsychoPy here, for the same reason as ``mcgurk.py`` and ``avsr.py``: the
design, the judgement mapping and — above all — the psychometric fit have to be
checkable in CI, against data whose true parameters are known.

The method is the method of constant stimuli: one congruent audiovisual token
is presented at each SOA in ``modules.tbw.soa_values_ms``, several times, in a
seeded order, and the participant says whether the two streams were
simultaneous.  The proportion of "same" responses traced against SOA is the
psychometric function; a Gaussian is fitted to it and three numbers come out:

* **PSS** — the point of subjective simultaneity, the SOA the curve peaks at.
  Not zero in general: sound and light have different physical and neural
  latencies, and the window is usually centred on a small positive SOA.
* **sigma** — the spread of the curve.
* **the window** — ``2.355 sigma`` (FWHM) or ``2 sigma`` (the +/-1 sigma
  window), whichever ``modules.tbw.tbw_definition`` names.  Both are used in the
  literature and a width with no definition beside it cannot be compared with
  anything, so the definition travels with the number (steps.md §C Adım 6).

Three things here are easy to get wrong:

* **A timeout is a missing observation, not a "different".**  Unlike AVSR,
  where a timeout is an incorrect answer, there is no correct answer here.
  Filling it in either direction moves the curve; the trial is dropped from the
  proportion and counted in ``n_missing`` instead, so a participant who ran out
  of time is visible rather than silently reshaping their own window.
* **There is no correct answer at any SOA.**  ``responses.is_correct`` stays
  NULL and the database refuses anything else (§A.10, schema version 3): at
  +300 ms the streams really are asynchronous, but what is being measured is
  whether they were *perceived* as one event.
* **A failed fit is an error.**  A flat curve, a curve with no "same" responses
  at all, or an optimiser that did not converge produce no width; returning a
  number anyway would put a fabricated window into the analysis.
"""

from __future__ import annotations

import logging
import math
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from ..config.schema import ExperimentConfig, TBWConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
from ..engine.scheduling import TimingParams
from ..stimuli.manifest import ManifestError, StimulusManifest
from .base import (
    QUIET,
    ModuleError,
    PlannedTrial,
    derive_seed,
    order_cells,
    row_value,
)

logger = logging.getLogger(__name__)

MODULE_NAME = "tbw"

#: What a response means.  Stored in ``responses.category``, like Modül 1's
#: percepts: the raw Turkish label is kept too, but analysis should not have to
#: match strings from a config snapshot to know what was judged.
SAME = "SAME"
DIFFERENT = "DIFFERENT"
JUDGEMENTS = (SAME, DIFFERENT)

#: Width of a Gaussian per unit sigma, by ``tbw_definition``.
WIDTH_FACTORS = {
    # 2 * sqrt(2 * ln 2)
    "fwhm": 2.3548200450309493,
    # the +/-1 sigma window
    "sigma1": 2.0,
}

#: Clip on the modelled probability inside the likelihood.  Without it a
#: perfectly predicted 0 or 1 makes the log-likelihood infinite and the
#: optimiser walks off the edge of the parameter space.
_P_EPS = 1e-6


@dataclass(frozen=True)
class Cell:
    """One design cell: one SOA, in one ear condition."""

    soa_ms: float
    ear: str

    @property
    def label(self) -> str:
        """``trials.condition_label`` — the SOA, readable in the operator's log."""
        return f"SOA {self.soa_ms:+g} ms"


def design_cells(module: TBWConfig) -> tuple[list[Cell], list[int]]:
    """The full crossing, plus the repetition count of each cell."""
    cells: list[Cell] = []
    reps: list[int] = []
    for soa_ms in module.soa_values_ms:
        for ear in module.ears:
            cells.append(Cell(soa_ms=soa_ms, ear=ear))
            reps.append(module.reps_per_soa)
    return cells, reps


def check_soa_is_schedulable(config: ExperimentConfig) -> float:
    """Verify the widest negative SOA still fits in the presenter's lead.

    A negative SOA needs the audio to start before the video, which the engine
    pays for by pushing the flip target further into the future
    (``scheduling.required_lead_frames``).  Past ``max_lead_s`` it refuses the
    trial — correctly, but at that point the participant is already sitting
    down.  The same arithmetic is done here, at design time, against the
    *expected* refresh rate.

    Returns:
        The lead the widest negative SOA needs, in seconds.

    Raises:
        ModuleError: when that lead exceeds the engine's ceiling.
    """
    module = config.modules.tbw
    params = TimingParams(
        frame_period_s=1.0 / config.display.expected_refresh_hz,
        lead_frames=config.timing.lead_frames,
        system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
        dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
    )
    widest = min(module.soa_values_ms)
    # The audio sits at SOA - D relative to the flip; a negative result is how
    # far before the flip it has to start, and PTB needs its arming margin on
    # top of that.
    offset_s = widest / 1000.0 - params.offset_s
    needed_s = max(0.0, -offset_s) + params.schedule_margin_s
    needed_s = max(needed_s, params.lead_frames * params.frame_period_s)
    if needed_s > params.max_lead_s:
        raise ModuleError(
            f"En geniş negatif SOA ({widest:g} ms) sunum payı olarak "
            f"{needed_s * 1000:.0f} ms istiyor, motorun üst sınırı "
            f"{params.max_lead_s * 1000:.0f} ms. modules.tbw.soa_values_ms "
            "daraltılmalı."
        )
    return needed_s


def plan_trials(
    config: ExperimentConfig,
    manifest: StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    speaker_id: int | None = None,
) -> list[PlannedTrial]:
    """Build the module's trial list from the config and the prepared set.

    Args:
        seed: The **session** seed; the module's own stream is derived from it.
        stimuli_root: ``paths.stimuli``, already resolved.
        speaker_id: Overrides ``modules.tbw.speaker_id`` (Adım 8, §F.4).

    Raises:
        ModuleError: the module is disabled, the prepared set does not contain
            the stimulus, or an SOA cannot be scheduled at all.
    """
    module = config.modules.tbw
    if not module.enabled:
        raise ModuleError(
            "modules.tbw.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )

    speaker = speaker_id if speaker_id is not None else module.speaker_id
    lead_s = check_soa_is_schedulable(config)
    rng = random.Random(derive_seed(seed, MODULE_NAME))

    # One stimulus for the whole module, so it is resolved once: what varies
    # between trials is when the audio starts, not what it is.
    try:
        video = manifest.video(speaker, module.stimulus.visual)
        token = manifest.token(speaker, module.stimulus.visual, module.stimulus.audio)
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nUyaran seti bu tasarımla hazırlanmamış: "
            "python tools/prepare_stimuli.py"
        ) from exc

    video_path = video.file.resolve(stimuli_root)
    audio_path = token.file.resolve(stimuli_root)

    cells, reps = design_cells(module)
    ordered = order_cells(cells, reps, rng, module.randomization)

    planned = [
        PlannedTrial(
            spec=TrialSpec(
                label=cell.label,
                video_path=video_path,
                video_burst_s=video.burst_time_s,
                audio_path=audio_path,
                audio_burst_s=token.burst_time_s,
                ear=cell.ear,
                nominal_soa_ms=cell.soa_ms,
            ),
            trial=Trial(
                block_id=0,  # the runner fills this in
                trial_index=0,
                module=MODULE_NAME,
                condition_label=cell.label,
                visual_token=module.stimulus.visual,
                audio_token=module.stimulus.audio,
                ear=cell.ear,
                snr_db=None,
                noise_condition=QUIET,
                nominal_soa_ms=cell.soa_ms,
                presentation_mode="AV",
                design_extra={"speaker_id": speaker, "noise_instance": None},
            ),
        )
        for cell in ordered
    ]

    logger.info(
        "TBW tasarımı: %d deneme (%d SOA x %d tekrar x %d kulak, %s), "
        "konuşmacı %d, tohum %d, en geniş pay %.0f ms",
        len(planned),
        len(module.soa_values_ms),
        module.reps_per_soa,
        len(module.ears),
        module.randomization,
        speaker,
        seed,
        lead_s * 1000.0,
    )
    return planned


# ------------------------------------------------------------------- judgement


def judge(response: str | None, module: TBWConfig) -> str | None:
    """Map a raw response onto :data:`SAME` / :data:`DIFFERENT`.

    None for a no-response, which is what the caller has on a timeout.  What a
    timeout does to the psychometric function is decided in
    :func:`psychometric_points`, not here.
    """
    if response is None or not response.strip():
        return None
    answer = response.strip().casefold()
    if answer == module.response_labels["same"].casefold():
        return SAME
    if answer == module.response_labels["different"].casefold():
        return DIFFERENT
    # The config validation makes response_set and response_labels the same two
    # strings, so this is unreachable from a loaded config; it stays because a
    # silent OTHER here would quietly drop trials out of the curve.
    raise ModuleError(
        f"TBW yanıtı response_labels ile eşleşmiyor: {response!r}. "
        f"Tanımlı yanıtlar: {sorted(module.response_labels.values())}"
    )


# ----------------------------------------------------------------- the curve


class FitError(ModuleError):
    """The psychometric function could not be fitted.

    Its own class so a caller can tell "this participant's curve is degenerate"
    from "this module could not build its design" — the first is a finding
    about the data, the second is a configuration problem.
    """


@dataclass(frozen=True)
class SOAPoint:
    """One point of the psychometric function."""

    soa_ms: float
    n_same: int
    n_responded: int
    n_missing: int = 0

    @property
    def p_same(self) -> float | None:
        """Proportion of "same" among the trials that were answered."""
        return self.n_same / self.n_responded if self.n_responded else None


@dataclass(frozen=True)
class Interval:
    """A percentile confidence interval."""

    low: float
    high: float

    def __str__(self) -> str:
        return f"[{self.low:.1f}, {self.high:.1f}]"


@dataclass(frozen=True)
class TBWFit:
    """The fitted window, and what it was fitted to."""

    pss_ms: float
    sigma_ms: float
    amplitude: float
    width_ms: float
    definition: str
    n_points: int
    n_responses: int
    n_missing: int
    pss_ci: Interval | None = None
    sigma_ci: Interval | None = None
    width_ci: Interval | None = None
    bootstrap_samples: int = 0
    bootstrap_failures: int = 0


def psychometric_points(rows: Iterable[object]) -> list[SOAPoint]:
    """Group ``v_trials_flat`` rows into one point per SOA.

    A trial with no response row (a timeout) is counted in ``n_missing`` and
    left out of the proportion: it is a missing observation, and scoring it
    either way would move the curve in a direction chosen by the analyst rather
    than by the participant.
    """
    same: Counter[float] = Counter()
    answered: Counter[float] = Counter()
    missing: Counter[float] = Counter()

    for row in rows:
        module = row_value(row, "module")
        if module is not None and module != MODULE_NAME:
            continue
        soa = row_value(row, "nominal_soa_ms")
        if soa is None:
            raise FitError(
                "TBW denemesinde nominal_soa_ms boş — psikometrik eğri hangi "
                "SOA'da olduğunu bilmeden kurulamaz"
            )
        soa_ms = float(soa)
        category = row_value(row, "category")
        if category is None:
            missing[soa_ms] += 1
            continue
        if category not in JUDGEMENTS:
            raise FitError(
                f"TBW denemesinde bilinmeyen kategori: {category!r}. "
                f"Beklenen: {list(JUDGEMENTS)}"
            )
        answered[soa_ms] += 1
        if category == SAME:
            same[soa_ms] += 1

    return [
        SOAPoint(
            soa_ms=soa_ms,
            n_same=same[soa_ms],
            n_responded=answered[soa_ms],
            n_missing=missing[soa_ms],
        )
        for soa_ms in sorted(set(answered) | set(missing))
    ]


def _arrays(points: Sequence[SOAPoint]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    usable = [point for point in points if point.n_responded > 0]
    if len(usable) < 3:
        raise FitError(
            f"Gauss uydurma en az 3 SOA noktasında yanıt gerektirir (üç "
            f"parametre kestiriliyor); yanıtlanan nokta: {len(usable)}"
        )
    x = np.array([point.soa_ms for point in usable], dtype=float)
    k = np.array([point.n_same for point in usable], dtype=float)
    n = np.array([point.n_responded for point in usable], dtype=float)
    return x, k, n


def _gaussian(x: np.ndarray, amplitude: float, pss: float, sigma: float) -> np.ndarray:
    return amplitude * np.exp(-((x - pss) ** 2) / (2.0 * sigma**2))


def fit_curve(points: Sequence[SOAPoint]) -> tuple[float, float, float]:
    """Fit ``p(same) = A exp(-(SOA - PSS)^2 / 2 sigma^2)`` by maximum likelihood.

    Binomial likelihood rather than least squares on the proportions: each point
    carries a different number of trials once timeouts are dropped, and a
    proportion of 10/10 is not as informative as it looks under a squared-error
    loss.

    Returns:
        ``(amplitude, pss_ms, sigma_ms)``.

    Raises:
        FitError: too few answered points, no "same" responses at all, an
            optimiser that did not converge, or a window wider than half the
            tested SOA range — none of those has a width worth reporting.
    """
    x, k, n = _arrays(points)
    span = float(x.max() - x.min())
    if span <= 0:
        raise FitError("Tüm yanıtlar tek bir SOA'da — eğri kurulamaz")

    def negative_log_likelihood(theta: np.ndarray) -> float:
        amplitude, pss, sigma = theta
        p = np.clip(_gaussian(x, amplitude, pss, sigma), _P_EPS, 1.0 - _P_EPS)
        return float(-np.sum(k * np.log(p) + (n - k) * np.log1p(-p)))

    proportions = k / n
    weights = proportions * n
    total = float(weights.sum())
    if total <= 0:
        raise FitError(
            "Hiçbir denemede 'aynı' yanıtı yok — eşzamanlılık penceresi "
            "kestirilemez (katılımcı her SOA'da 'farklı' dedi)"
        )
    start_pss = float(np.sum(weights * x) / total)
    start_var = float(np.sum(weights * (x - start_pss) ** 2) / total)
    start_sigma = math.sqrt(start_var) if start_var > 0 else span / 4.0
    start = np.array(
        [
            float(np.clip(proportions.max(), 0.05, 1.0)),
            start_pss,
            float(np.clip(start_sigma, span / 50.0, span)),
        ]
    )

    sigma_bounds = (span / 100.0, 10.0 * span)
    bounds = [
        (0.01, 1.0),
        (float(x.min()) - span, float(x.max()) + span),
        sigma_bounds,
    ]
    result = minimize(
        negative_log_likelihood, start, method="L-BFGS-B", bounds=bounds
    )
    if not result.success:
        raise FitError(
            f"Psikometrik uydurma yakınsamadı: {result.message}. "
            "Veri yetersiz ya da eğri dejenere."
        )

    amplitude, pss, sigma = (float(value) for value in result.x)
    # A window wider than the grid it was measured on is an extrapolation, not
    # an estimate: at sigma = span/2 the curve has fallen by only ~12% at the
    # outermost SOA, so the data is compatible with almost any larger width and
    # the optimiser picks one anyway.  Reporting it would put a number like
    # "TBW 6500 ms" in a table, where it reads as a measurement.
    if sigma >= span / 2.0:
        raise FitError(
            f"Uydurulan sigma ({sigma:.0f} ms) test edilen SOA aralığının "
            f"({span:.0f} ms) yarısından geniş — eğri bu aralıkta düz, pencere "
            "genişliği ölçülmüş değil kestirilmiş olur. Daha geniş SOA aralığı "
            "ya da daha çok deneme gerekir."
        )
    if amplitude <= 0.011:
        raise FitError(
            "Uydurulan eğrinin tepesi sıfıra yakın — 'aynı' yanıtı yok denecek "
            "kadar az, pencere kestirilemez"
        )
    return amplitude, pss, sigma


def window_ms(sigma_ms: float, definition: str) -> float:
    """Window width from sigma, by ``modules.tbw.tbw_definition``."""
    try:
        return WIDTH_FACTORS[definition] * sigma_ms
    except KeyError as exc:
        raise FitError(
            f"Bilinmeyen TBW tanımı: {definition!r}. "
            f"Tanımlı olanlar: {sorted(WIDTH_FACTORS)}"
        ) from exc


def bootstrap_intervals(
    points: Sequence[SOAPoint],
    *,
    definition: str,
    samples: int,
    ci: float,
    seed: int,
) -> tuple[Interval, Interval, Interval, int]:
    """Percentile confidence intervals for PSS, sigma and the window.

    Trials are resampled within each SOA — binomial draws at the observed
    proportion, which is the same thing as resampling that point's responses
    with replacement — and the curve is refitted on each resample.  The RNG is
    seeded from the session seed, so the same data always yields the same
    interval (§A.11).

    Resamples that cannot be fitted are counted and skipped; if more than half
    of them fail, no interval is reported at all, because an interval computed
    from the resamples that happened to be well behaved is biased towards
    exactly the shape that fits.

    Returns:
        ``(pss_ci, sigma_ci, width_ci, n_failures)``.
    """
    if samples <= 0:
        raise FitError("bootstrap_samples pozitif olmalı")

    usable = [point for point in points if point.n_responded > 0]
    rng = np.random.default_rng(seed)
    pss_draws: list[float] = []
    sigma_draws: list[float] = []
    failures = 0

    for _ in range(samples):
        resampled = [
            SOAPoint(
                soa_ms=point.soa_ms,
                n_same=int(
                    rng.binomial(point.n_responded, point.n_same / point.n_responded)
                ),
                n_responded=point.n_responded,
                n_missing=point.n_missing,
            )
            for point in usable
        ]
        try:
            _, pss, sigma = fit_curve(resampled)
        except FitError:
            failures += 1
            continue
        pss_draws.append(pss)
        sigma_draws.append(sigma)

    if len(pss_draws) < samples / 2:
        raise FitError(
            f"Bootstrap örneklerinin {failures}/{samples} tanesi uydurulamadı — "
            "güven aralığı yalnızca uyan örneklerden hesaplanamaz (yanlı olur). "
            "Deneme sayısı ya da SOA aralığı yetersiz."
        )

    tail = (1.0 - ci) / 2.0 * 100.0
    pss_low, pss_high = np.percentile(pss_draws, [tail, 100.0 - tail])
    sigma_low, sigma_high = np.percentile(sigma_draws, [tail, 100.0 - tail])
    return (
        Interval(float(pss_low), float(pss_high)),
        Interval(float(sigma_low), float(sigma_high)),
        Interval(
            window_ms(float(sigma_low), definition),
            window_ms(float(sigma_high), definition),
        ),
        failures,
    )


def fit(
    points: Sequence[SOAPoint],
    *,
    definition: str,
    bootstrap_samples: int = 0,
    bootstrap_ci: float = 0.95,
    seed: int = 0,
) -> TBWFit:
    """Fit the curve and, when asked, bootstrap its confidence intervals."""
    amplitude, pss, sigma = fit_curve(points)
    fitted = TBWFit(
        pss_ms=pss,
        sigma_ms=sigma,
        amplitude=amplitude,
        width_ms=window_ms(sigma, definition),
        definition=definition,
        n_points=sum(1 for point in points if point.n_responded > 0),
        n_responses=sum(point.n_responded for point in points),
        n_missing=sum(point.n_missing for point in points),
    )
    if bootstrap_samples <= 0:
        return fitted

    pss_ci, sigma_ci, width_ci, failures = bootstrap_intervals(
        points,
        definition=definition,
        samples=bootstrap_samples,
        ci=bootstrap_ci,
        seed=seed,
    )
    return TBWFit(
        pss_ms=fitted.pss_ms,
        sigma_ms=fitted.sigma_ms,
        amplitude=fitted.amplitude,
        width_ms=fitted.width_ms,
        definition=fitted.definition,
        n_points=fitted.n_points,
        n_responses=fitted.n_responses,
        n_missing=fitted.n_missing,
        pss_ci=pss_ci,
        sigma_ci=sigma_ci,
        width_ci=width_ci,
        bootstrap_samples=bootstrap_samples,
        bootstrap_failures=failures,
    )


def fit_from_rows(
    rows: Iterable[object], module: TBWConfig, *, seed: int = 0
) -> TBWFit:
    """:func:`fit` on ``v_trials_flat`` rows, with the config's own settings."""
    return fit(
        psychometric_points(rows),
        definition=module.tbw_definition,
        bootstrap_samples=module.bootstrap_samples,
        bootstrap_ci=module.bootstrap_ci,
        seed=derive_seed(seed, f"{MODULE_NAME}_bootstrap"),
    )


# -------------------------------------------------------------------- measures


def summarise_points(points: Sequence[SOAPoint]) -> str:
    """The raw psychometric function, one line per SOA."""
    lines = [f"  {'SOA (ms)':>9}{'aynı':>8}{'yanıt':>8}{'p(aynı)':>10}{'yanıtsız':>10}"]
    for point in points:
        proportion = point.p_same
        shown = "—" if proportion is None else f"{proportion:.2f}"
        lines.append(
            f"  {point.soa_ms:>9.0f}{point.n_same:>8}{point.n_responded:>8}"
            f"{shown:>10}{point.n_missing:>10}"
        )
    return "\n".join(lines)


def summarise_measures(
    rows: Iterable[object], module: TBWConfig, *, seed: int = 0
) -> str:
    """The module's measures as a block of text, for the operator's console.

    A failed fit is reported as a failed fit rather than raised: the run itself
    succeeded, and the operator needs to see the points that produced the
    failure.
    """
    points = psychometric_points(rows)
    lines = ["Psikometrik fonksiyon:", summarise_points(points)]
    try:
        fitted = fit_from_rows(rows, module, seed=seed)
    except FitError as exc:
        lines.append(f"Uydurma yapılamadı: {exc}")
        return "\n".join(lines)

    short = "FWHM" if fitted.definition == "fwhm" else "+/-1 sigma"
    formula = (
        "FWHM = 2.355 x sigma" if fitted.definition == "fwhm" else "2 x sigma"
    )
    lines.extend(
        [
            f"PSS                    : {fitted.pss_ms:+.1f} ms"
            + (f"  GA {fitted.pss_ci}" if fitted.pss_ci else ""),
            f"Sigma                  : {fitted.sigma_ms:.1f} ms"
            + (f"  GA {fitted.sigma_ci}" if fitted.sigma_ci else ""),
            f"TBW genişliği ({short:<10}): {fitted.width_ms:.1f} ms"
            + (f"  GA {fitted.width_ci}" if fitted.width_ci else ""),
            # The definition travels with the number: the literature uses both,
            # and a width with no definition beside it cannot be compared.
            f"Genişlik tanımı        : {formula}",
            f"Eğri tepesi            : {fitted.amplitude:.2f}",
            f"Yanıtlanan / yanıtsız  : {fitted.n_responses} / {fitted.n_missing}",
        ]
    )
    if fitted.bootstrap_failures:
        lines.append(
            f"Bootstrap: {fitted.bootstrap_failures}/{fitted.bootstrap_samples} "
            "örnek uydurulamadı"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- inspection


def cell_counts(planned: Sequence[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(label, stimulus, ear, noise)``.

    Built from the plan that will actually run rather than recomputed from the
    config, so a bug in the generator shows up as a wrong table.
    """
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        counts[
            (
                trial.condition_label,
                f"Vis-{trial.visual_token}/Aud-{trial.audio_token}",
                str(trial.ear),
                QUIET,
            )
        ] += 1
    return dict(counts)
