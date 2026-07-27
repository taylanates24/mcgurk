"""Modül 3 — the psychometric fit, against data whose parameters are known.

steps.md §C Adım 6 asks for exactly this: "PSS and TBW are correctly estimated
from simulated data with known parameters", and "a failed fit raises a clear
error".  Simulated rather than real data is the point — with a real
participant's responses there is nothing to compare the estimate against.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from mcgurk.config.loader import load_config
from mcgurk.modules.tbw import (
    DIFFERENT,
    SAME,
    FitError,
    SOAPoint,
    bootstrap_intervals,
    fit,
    fit_curve,
    fit_from_rows,
    psychometric_points,
    summarise_measures,
    window_ms,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: The SOA grid the shipped config uses.
SOAS = [float(value) for value in range(-300, 301, 50)]

TRUE_PSS = 20.0
TRUE_SIGMA = 90.0
TRUE_AMPLITUDE = 0.95


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


def p_same(soa_ms: float, pss: float, sigma: float, amplitude: float) -> float:
    return amplitude * math.exp(-((soa_ms - pss) ** 2) / (2.0 * sigma**2))


def simulate(
    *,
    pss: float = TRUE_PSS,
    sigma: float = TRUE_SIGMA,
    amplitude: float = TRUE_AMPLITUDE,
    soas: list[float] | None = None,
    n_per_soa: int = 60,
    seed: int = 7,
) -> list[SOAPoint]:
    """Binomial responses from a known Gaussian observer."""
    rng = np.random.default_rng(seed)
    return [
        SOAPoint(
            soa_ms=soa,
            n_same=int(rng.binomial(n_per_soa, p_same(soa, pss, sigma, amplitude))),
            n_responded=n_per_soa,
        )
        for soa in (soas if soas is not None else SOAS)
    ]


def as_rows(points: list[SOAPoint], *, module: str = "tbw") -> list[dict[str, Any]]:
    """Trial-level ``v_trials_flat`` rows, the way the database returns them."""
    rows: list[dict[str, Any]] = []
    for point in points:
        for index in range(point.n_responded):
            rows.append(
                {
                    "module": module,
                    "nominal_soa_ms": point.soa_ms,
                    "category": SAME if index < point.n_same else DIFFERENT,
                }
            )
        for _ in range(point.n_missing):
            rows.append(
                {"module": module, "nominal_soa_ms": point.soa_ms, "category": None}
            )
    return rows


# ------------------------------------------------------------------ recovery


def test_a_known_pss_and_sigma_are_recovered() -> None:
    amplitude, pss, sigma = fit_curve(simulate())
    assert pss == pytest.approx(TRUE_PSS, abs=15.0)
    assert sigma == pytest.approx(TRUE_SIGMA, abs=15.0)
    assert amplitude == pytest.approx(TRUE_AMPLITUDE, abs=0.1)


@pytest.mark.parametrize("true_pss", [-60.0, 0.0, 80.0])
def test_the_curve_follows_the_pss_it_was_generated_with(true_pss: float) -> None:
    """A PSS away from zero is the normal case — sound and light do not arrive
    at the cortex together — so an estimator that only works at zero is no
    estimator."""
    _, pss, _ = fit_curve(simulate(pss=true_pss, seed=11))
    assert pss == pytest.approx(true_pss, abs=20.0)


@pytest.mark.parametrize("true_sigma", [50.0, 120.0])
def test_a_wider_observer_gives_a_wider_window(true_sigma: float) -> None:
    _, _, sigma = fit_curve(simulate(sigma=true_sigma, seed=13))
    assert sigma == pytest.approx(true_sigma, rel=0.25)


def test_the_window_definition_is_applied_and_reported() -> None:
    points = simulate()
    fwhm = fit(points, definition="fwhm")
    sigma1 = fit(points, definition="sigma1")

    assert fwhm.sigma_ms == pytest.approx(sigma1.sigma_ms)
    assert fwhm.width_ms == pytest.approx(2.3548200450309493 * fwhm.sigma_ms)
    assert sigma1.width_ms == pytest.approx(2.0 * sigma1.sigma_ms)
    assert fwhm.definition == "fwhm"
    assert sigma1.definition == "sigma1"


def test_an_unknown_window_definition_is_an_error() -> None:
    with pytest.raises(FitError, match="tanım"):
        window_ms(80.0, "half_maximum")


# ----------------------------------------------------------------- bootstrap


def test_the_confidence_interval_covers_the_true_parameters() -> None:
    fitted = fit(simulate(), definition="fwhm", bootstrap_samples=300, seed=3)
    assert fitted.pss_ci is not None
    assert fitted.width_ci is not None
    assert fitted.pss_ci.low <= TRUE_PSS <= fitted.pss_ci.high
    true_width = 2.3548200450309493 * TRUE_SIGMA
    assert fitted.width_ci.low <= true_width <= fitted.width_ci.high
    assert fitted.bootstrap_samples == 300


def test_the_interval_is_reproducible_from_the_seed() -> None:
    """§A.11 — the same data must always give the same interval, or two runs of
    the analysis disagree about the same participant."""
    points = simulate()
    first = fit(points, definition="fwhm", bootstrap_samples=250, seed=42)
    second = fit(points, definition="fwhm", bootstrap_samples=250, seed=42)
    other = fit(points, definition="fwhm", bootstrap_samples=250, seed=43)

    assert first.pss_ci == second.pss_ci
    assert first.width_ci == second.width_ci
    assert first.pss_ci != other.pss_ci


def test_a_wider_interval_comes_from_fewer_trials() -> None:
    tight = fit(simulate(n_per_soa=60), definition="fwhm", bootstrap_samples=300, seed=5)
    loose = fit(simulate(n_per_soa=10), definition="fwhm", bootstrap_samples=300, seed=5)
    assert tight.pss_ci is not None and loose.pss_ci is not None
    assert (tight.pss_ci.high - tight.pss_ci.low) < (loose.pss_ci.high - loose.pss_ci.low)


def test_no_bootstrap_means_no_interval() -> None:
    fitted = fit(simulate(), definition="fwhm", bootstrap_samples=0)
    assert fitted.pss_ci is None
    assert fitted.width_ci is None
    assert fitted.bootstrap_samples == 0


# ------------------------------------------------------------------ refusals


def test_a_participant_who_never_said_same_has_no_window() -> None:
    points = [SOAPoint(soa_ms=soa, n_same=0, n_responded=10) for soa in SOAS]
    with pytest.raises(FitError, match="aynı"):
        fit_curve(points)


def test_a_flat_curve_is_refused_rather_than_reported_as_enormous() -> None:
    """Answering "same" half the time regardless of SOA describes no window;
    the best-fitting Gaussian is arbitrarily wide, and a width of 6000 ms in a
    table looks like a measurement."""
    points = [SOAPoint(soa_ms=soa, n_same=30, n_responded=60) for soa in SOAS]
    with pytest.raises(FitError, match="düz"):
        fit_curve(points)


def test_too_few_soa_points_are_refused() -> None:
    points = [
        SOAPoint(soa_ms=-100.0, n_same=2, n_responded=10),
        SOAPoint(soa_ms=0.0, n_same=9, n_responded=10),
        # Answered by nobody: three parameters need three usable points.
        SOAPoint(soa_ms=100.0, n_same=0, n_responded=0, n_missing=10),
    ]
    with pytest.raises(FitError, match="3 SOA"):
        fit_curve(points)


def test_a_bootstrap_that_mostly_fails_reports_no_interval() -> None:
    """An interval computed only from the resamples that happened to fit is
    biased towards exactly the shape that fits.

    Tested on ``bootstrap_intervals`` directly: for data this degenerate the
    point estimate is refused first, which is the intended order — this guard
    is the backstop for a curve that is just resolvable and whose resamples are
    not.
    """
    flat = [SOAPoint(soa_ms=soa, n_same=2, n_responded=10) for soa in SOAS]
    with pytest.raises(FitError, match="[Bb]ootstrap"):
        bootstrap_intervals(flat, definition="fwhm", samples=200, ci=0.95, seed=9)


# --------------------------------------------------------------- from the db


def test_rows_are_grouped_into_one_point_per_soa() -> None:
    points = psychometric_points(as_rows(simulate(n_per_soa=20, seed=17)))
    assert [point.soa_ms for point in points] == SOAS
    assert {point.n_responded for point in points} == {20}


def test_a_timeout_is_missing_rather_than_a_different_judgement() -> None:
    """Counting it as "different" would narrow the window of exactly the
    participants who could not answer in time (Adım 6 decision)."""
    rows = [
        {"module": "tbw", "nominal_soa_ms": 0.0, "category": SAME},
        {"module": "tbw", "nominal_soa_ms": 0.0, "category": SAME},
        {"module": "tbw", "nominal_soa_ms": 0.0, "category": None},
    ]
    point = psychometric_points(rows)[0]
    assert point.n_responded == 2
    assert point.n_same == 2
    assert point.n_missing == 1
    assert point.p_same == 1.0


def test_rows_from_other_modules_are_ignored() -> None:
    rows = as_rows(simulate(n_per_soa=10, seed=19))
    rows += [{"module": "avsr", "nominal_soa_ms": None, "category": None}]
    assert {point.n_responded for point in psychometric_points(rows)} == {10}


def test_a_trial_with_no_soa_is_an_error() -> None:
    rows = [{"module": "tbw", "nominal_soa_ms": None, "category": SAME}]
    with pytest.raises(FitError, match="nominal_soa_ms"):
        psychometric_points(rows)


def test_an_unknown_category_is_an_error() -> None:
    rows = [{"module": "tbw", "nominal_soa_ms": 0.0, "category": "FUSION"}]
    with pytest.raises(FitError, match="kategori"):
        psychometric_points(rows)


def test_the_config_supplies_the_definition_and_the_bootstrap(config: Any) -> None:
    module = config.modules.tbw
    module.bootstrap_samples = 250
    fitted = fit_from_rows(as_rows(simulate(n_per_soa=30, seed=23)), module, seed=1)
    assert fitted.definition == module.tbw_definition
    assert fitted.bootstrap_samples == 250
    assert fitted.pss_ci is not None
    assert fitted.n_responses == 30 * len(SOAS)


def test_the_same_session_seed_gives_the_same_interval(config: Any) -> None:
    module = config.modules.tbw
    module.bootstrap_samples = 200
    rows = as_rows(simulate(n_per_soa=30, seed=29))
    assert fit_from_rows(rows, module, seed=4).pss_ci == fit_from_rows(
        rows, module, seed=4
    ).pss_ci


# ---------------------------------------------------------------- the report


def test_the_summary_names_the_definition_and_the_numbers(config: Any) -> None:
    module = config.modules.tbw
    module.bootstrap_samples = 0
    text = summarise_measures(as_rows(simulate(n_per_soa=20, seed=31)), module)
    assert "PSS" in text
    assert "TBW genişliği" in text
    assert "FWHM" in text
    assert "p(aynı)" in text


def test_a_failed_fit_is_reported_rather_than_raised(config: Any) -> None:
    """The run itself succeeded; the operator needs to see the points that
    produced the failure, not a traceback instead of the report."""
    module = config.modules.tbw
    module.bootstrap_samples = 0
    rows = [
        {"module": "tbw", "nominal_soa_ms": soa, "category": DIFFERENT}
        for soa in SOAS
    ]
    text = summarise_measures(rows, module)
    assert "Uydurma yapılamadı" in text
    assert "SOA" in text
