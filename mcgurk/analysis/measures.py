"""Per-session, per-module measures, read from the database.

The measurement mathematics is not here.  Every module already computes its own
headline numbers from ``v_trials_flat`` rows — McGurk's category rates, AVSR's
accuracy and visual benefit, TBW's psychometric fit, oddball's d', the dichotic
laterality index, GIN's gap threshold — and each is tested in CI against
hand-computed values.  Re-deriving any of them here would be a second source of
truth that could disagree with the first.

This module does three things instead:

* reads a session's flat rows and its **config snapshot** (§G) — not the current
  ``config/experiment.yaml``, so a later edit cannot change how already-collected
  data is read;
* groups the rows by module and dispatches each group to the module that owns
  its measures;
* collects the results, tolerating a module whose data is too degenerate to
  measure (a session with a failed TBW fit still has five other modules worth
  reporting).

There is no PsychoPy here: analysis runs on a machine that need not have it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..config.loader import config_from_snapshot
from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..modules import avsr, dichotic, gin, mcgurk, oddball, tbw
from ..modules.base import ModuleError, row_value
from ..modules.tbw import FitError

#: The six measurement modules, in the order a report reads them.  ``practice``
#: and ``cross_hearing`` are session-flow steps, not measurements (the latter is
#: scored by the QC report, which reads whether the tone was heard in the deaf
#: ear rather than a percept).
MEASUREMENT_MODULES = ("mcgurk", "avsr", "tbw", "oddball", "dichotic", "gin")


class MeasuresError(RuntimeError):
    """Raised when a session cannot be located or its snapshot is unreadable."""


@dataclass(frozen=True)
class AvsrSummary:
    """AVSR's headline numbers, composed from the module's own functions.

    Unlike the other modules, AVSR exposes its measures as separate functions
    rather than one object; this gathers the three an operator reads first.
    """

    by_mode: dict[str, avsr.Accuracy]
    visual_benefit: float | None
    lipreading: float | None


@dataclass(frozen=True)
class ModuleMeasure:
    """One module's measures within a session.

    ``data`` is the module's own structured result (``McGurkRates``, ``TBWFit``,
    ``DetectionMeasures``, ``EarAdvantage``, ``GINMeasures`` or
    :class:`AvsrSummary`), or ``None`` when the data was too degenerate to
    measure — in which case ``error`` says why.  ``summary`` is always present:
    even a failed fit produces a readable block for the operator's console.
    """

    module: str
    n_trials: int
    summary: str
    data: object | None = None
    error: str | None = None


@dataclass(frozen=True)
class SessionMeasures:
    """Every measurement module's results for one session."""

    session_id: int
    participant_code: str | None
    group_code: str | None
    modules: tuple[ModuleMeasure, ...]

    def summary_text(self) -> str:
        """A block of text for the operator's console, one section per module."""
        header = (
            f"Katılımcı {self.participant_code} ({self.group_code}) "
            f"— oturum {self.session_id}"
        )
        blocks = [header, "=" * len(header)]
        for measure in self.modules:
            blocks.extend(["", measure.summary])
        if not self.modules:
            blocks.extend(["", "Ölçülebilir modül verisi yok."])
        return "\n".join(blocks)


def _structured(
    module: str, rows: list[object], config: ExperimentConfig, seed: int
) -> object:
    """The module's structured measures object.  May raise on degenerate data."""
    if module == "mcgurk":
        return mcgurk.rates_from_rows(rows)
    if module == "avsr":
        return AvsrSummary(
            by_mode=avsr.accuracy_by_mode(rows),
            visual_benefit=avsr.visual_benefit(rows),
            lipreading=avsr.lipreading_accuracy(rows),
        )
    if module == "tbw":
        return tbw.fit_from_rows(rows, config.modules.tbw, seed=seed)
    if module == "oddball":
        return oddball.measures_from_rows(rows)
    if module == "dichotic":
        return dichotic.ear_advantage(rows)
    if module == "gin":
        return gin.measures_from_rows(rows, config.modules.gin)
    raise MeasuresError(f"Bilinmeyen ölçüm modülü: {module!r}")


def _summary_text(
    module: str, rows: list[object], config: ExperimentConfig, seed: int
) -> str:
    """The module's console text.  Each module's summariser reports a failed
    measure as text rather than raising, so this is safe on degenerate data."""
    if module == "mcgurk":
        return mcgurk.summarise_measures(rows)
    if module == "avsr":
        return avsr.summarise_measures(rows)
    if module == "tbw":
        return tbw.summarise_measures(rows, config.modules.tbw, seed=seed)
    if module == "oddball":
        return oddball.summarise_measures(rows)
    if module == "dichotic":
        return dichotic.summarise_measures(rows)
    if module == "gin":
        return gin.summarise_measures(rows, config.modules.gin)
    raise MeasuresError(f"Bilinmeyen ölçüm modülü: {module!r}")


def _distinct_trials(rows: list[object]) -> int:
    return len(
        {
            row_value(row, "trial_id")
            for row in rows
            if row_value(row, "trial_id") is not None
        }
    )


def measure_module(
    module: str, rows: list[object], config: ExperimentConfig, *, seed: int = 0
) -> ModuleMeasure:
    """Measure one module's rows.  Pure — no database, for direct testing."""
    n_trials = _distinct_trials(rows)
    data: object | None
    try:
        data = _structured(module, rows, config, seed)
        error = None
    except (ModuleError, FitError) as exc:
        data = None
        error = str(exc)
    try:
        summary = _summary_text(module, rows, config, seed)
    except (ModuleError, FitError) as exc:  # pragma: no cover - malformed rows
        summary = f"{module}: ölçüm özeti üretilemedi ({exc})"
    return ModuleMeasure(
        module=module, n_trials=n_trials, summary=summary, data=data, error=error
    )


def _group_by_module(rows: Sequence[object]) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    for row in rows:
        module = row_value(row, "module")
        if module is None:
            continue
        grouped.setdefault(str(module), []).append(row)
    return grouped


def session_measures(db: Database, session_id: int) -> SessionMeasures:
    """Measure every measurement module of one session.

    The config and the seed come from the session row, so the numbers are the
    ones the session's own design produces.  A module that did not run (disabled,
    or the session aborted before it) is simply absent from the result.
    """
    session = db.get_session(session_id)
    if session is None:
        raise MeasuresError(f"Oturum bulunamadı: {session_id}")
    config = config_from_snapshot(str(session["config_snapshot"]))
    seed = int(session["seed"])

    rows = db.flat_rows(session_id)
    by_module = _group_by_module(rows)
    measures = [
        measure_module(module, by_module[module], config, seed=seed)
        for module in MEASUREMENT_MODULES
        if module in by_module
    ]

    participant_code = row_value(rows[0], "participant_code") if rows else None
    group_code = row_value(rows[0], "group_code") if rows else None
    return SessionMeasures(
        session_id=session_id,
        participant_code=None if participant_code is None else str(participant_code),
        group_code=None if group_code is None else str(group_code),
        modules=tuple(measures),
    )
