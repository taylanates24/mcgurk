"""Modül 5 — Dikotik dinleme: which ear's syllable gets reported.

No PsychoPy here, for the same reason as ``mcgurk.py``, ``avsr.py`` and
``tbw.py``: the design, the attribution of a response to an ear and the
laterality index all have to be checkable in CI.

Two different syllables are presented at the same instant, one to each ear, and
the participant reports the one they heard.  The instruction does not say that
there were two (``prompts.question`` asks "Hangi heceyi duydunuz?"), so the
report is free rather than directed: which side wins is the measurement, and
telling the participant to attend to one would replace it with a compliance
check.

The module serves two purposes at once (EK_DIKOTIK_DINLEME §6.5):

* **it validates the lateralisation** the SSD hypothesis rests on — Modül 1 and
  Modül 2 send audio to one ear, which only means anything if the deaf ear's
  input does not reach the good cochlea through the skull.  A participant who
  reports the deaf side above chance is cross-hearing, and their spatial-side
  data cannot be read;
* **it measures speech selection under binaural competition**, which Modül 1
  and 2 cannot: there, only one ear is ever given a token.

Three rules shape the file:

* **There is no correct answer** (§A.10).  Reporting the right ear is not a
  success, it is a percept; ``responses.is_correct`` stays NULL and the database
  refuses anything else on a ``dichotic`` trial.
* **A timeout is a missing observation**, as in TBW and for the same reason:
  with no correct answer, assigning an unanswered trial to either ear moves the
  index.  It is counted in ``n_missing`` instead.
* **The category comes from the chosen option, not from the free text.**  A
  participant who picked "DİĞER" declined the syllables that were on the screen;
  reading their typed text back into an ear would invent a report they did not
  give.  The text is stored verbatim for review.

In the SSD groups the presentation is functionally monotic — the deaf ear
supplies nothing — so the index measures the *absence* of competition rather
than hemispheric lateralisation.  That is an interpretation note, not a
computation: the same numbers come out, and §6.5 requires the asymmetry to be
stated whenever the groups are compared.
"""

from __future__ import annotations

import logging
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.schema import DichoticConfig, DichoticPair, ExperimentConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
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

MODULE_NAME = "dichotic"

#: Which ear's token the response matched.  ``OTHER`` is the intrusion rate of
#: §6.5 ("karışım yanıtı"): a report matching neither of the two syllables that
#: were presented — the third syllable, or the free-text option.  ``NONE`` is a
#: timeout and is never written: the absence of the ``responses`` row is the
#: record (Adım 1 decision), and :func:`categorise` returns it so that QC and
#: analysis agree on what a missing row means.
LEFT = "LEFT"
RIGHT = "RIGHT"
OTHER = "OTHER"
NONE = "NONE"

CATEGORIES = (LEFT, RIGHT, OTHER, NONE)


@dataclass(frozen=True)
class Cell:
    """One design cell: one pair of competing syllables.

    Noise and ear are not crossed here.  There is no noise condition — the
    competition between the ears *is* the difficult condition (§6.5) — and the
    ear is not a factor either: both ears receive a token on every trial, and
    which one is in the pair itself.
    """

    pair: DichoticPair

    @property
    def label(self) -> str:
        """``trials.condition_label`` — named after the prepared file."""
        return f"Left-{self.pair.left}/Right-{self.pair.right}"


def design_cells(module: DichoticConfig) -> tuple[list[Cell], list[int]]:
    """The pairs, plus the repetition count of each.

    ``reps`` is per pair and nothing is crossed with it, so the module's total
    is simply ``len(pairs) x reps`` — which is what
    :meth:`DichoticConfig.total_trials` says and what a test asserts.
    """
    cells = [Cell(pair=pair) for pair in module.pairs]
    return cells, [module.reps] * len(cells)


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
        seed: The **session** seed; the module's own stream is derived from it
            (:func:`~mcgurk.modules.base.derive_seed`).
        stimuli_root: ``paths.stimuli``, already resolved.
        speaker_id: Overrides ``modules.dichotic.speaker_id`` (Adım 8, §F.4).

    Raises:
        ModuleError: the module is disabled, or the prepared set does not hold a
            pair the design asks for.  Resolving every file here means failing
            before the participant sits down.
    """
    module = config.modules.dichotic
    if not module.enabled:
        raise ModuleError(
            "modules.dichotic.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )

    speaker = speaker_id if speaker_id is not None else module.speaker_id
    rng = random.Random(derive_seed(seed, MODULE_NAME))

    cells, reps = design_cells(module)
    ordered = order_cells(cells, reps, rng, module.randomization)

    planned = [
        _plan_one(manifest, cell, speaker=speaker, stimuli_root=stimuli_root)
        for cell in ordered
    ]

    logger.info(
        "Dikotik tasarımı: %d deneme (%d çift x %d tekrar, %s), konuşmacı %d, "
        "tohum %d",
        len(planned),
        len(cells),
        module.reps,
        module.randomization,
        speaker,
        seed,
    )
    return planned


def _plan_one(
    manifest: StimulusManifest,
    cell: Cell,
    *,
    speaker: int,
    stimuli_root: Path,
) -> PlannedTrial:
    try:
        entry = manifest.dichotic_pair(speaker, cell.pair.left, cell.pair.right)
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nUyaran seti bu tasarımla hazırlanmamış: "
            "python tools/prepare_stimuli.py"
        ) from exc

    # The file is already stereo with a different token per channel, so it is
    # handed over untouched: ``ear='both'`` is what tells the engine not to
    # lateralise it (``engine.audio.prepare_samples`` refuses anything else for
    # a stereo file).  Both channels sit on one burst time — Adım 2 imposes it,
    # because an ear advantage measured with asynchronous onsets would partly be
    # an onset effect.
    spec = TrialSpec(
        label=cell.label,
        audio_path=entry.file.resolve(stimuli_root),
        audio_burst_s=entry.burst_time_s,
        ear="both",
    )
    trial = Trial(
        block_id=0,  # the runner fills this in
        trial_index=0,
        module=MODULE_NAME,
        condition_label=cell.label,
        # No video at all: the screen holds the fixation cross, so the
        # participant cannot lipread their way out of the competition (§6.5).
        visual_token=None,
        # Two simultaneous tokens, so there is no single ``audio_token``; they
        # are in design_extra, and v_trials_flat exposes both as columns.
        audio_token=None,
        # Sound reaches both ears.  *What* each one receives is the pair, not
        # this column; NULL would say "not applicable", which is not true here.
        ear="both",
        snr_db=None,
        noise_condition=QUIET,
        nominal_soa_ms=None,
        presentation_mode="A",
        design_extra={
            "speaker_id": speaker,
            "noise_instance": None,
            "left_token": cell.pair.left,
            "right_token": cell.pair.right,
        },
    )
    return PlannedTrial(spec=spec, trial=trial)


# ------------------------------------------------------------- categorisation


def categorise(response: str | None, *, left_token: str, right_token: str) -> str:
    """Which ear's syllable the report matches.

    The config refuses a pair whose two sides are the same syllable, so a
    response can match at most one of them and the order of the two checks
    cannot matter.

    A free-text answer is not classified from its text (the McGurk rule): the
    label that reaches this function is the option that was chosen, and "DİĞER"
    matches neither token, so it lands in :data:`OTHER` — which is exactly what
    §6.5 counts as an intrusion.
    """
    if response is None or not response.strip():
        return NONE

    answer = response.strip().casefold()
    if answer == left_token.casefold():
        return LEFT
    if answer == right_token.casefold():
        return RIGHT
    return OTHER


def categorise_for(response: str | None, trial: Trial) -> str:
    """:func:`categorise` with the tokens recorded on *trial*."""
    left = trial.design_extra.get("left_token")
    right = trial.design_extra.get("right_token")
    if not isinstance(left, str) or not isinstance(right, str) or not left or not right:
        raise ModuleError(
            "Dikotik denemesinde design_extra['left_token'] ve ['right_token'] "
            "bulunmalı — yanıtın hangi kulağa ait olduğu onlardan türüyor"
        )
    return categorise(response, left_token=left, right_token=right)


# -------------------------------------------------------------------- measures


@dataclass(frozen=True)
class EarAdvantage:
    """Reports per ear, and the index derived from them.

    Rates are proportions of the **answered** trials: a timeout is a missing
    observation here (there is no correct answer to score it against), so it is
    kept in ``n_missing`` and left out of every denominator.  A condition that is
    mostly timeouts is then visible as such rather than as a confident-looking
    index over three trials.
    """

    n_trials: int = 0
    n_left: int = 0
    n_right: int = 0
    n_other: int = 0
    n_missing: int = 0

    @property
    def n_answered(self) -> int:
        return self.n_left + self.n_right + self.n_other

    @property
    def n_lateralised(self) -> int:
        """Reports that matched one of the two presented syllables."""
        return self.n_left + self.n_right

    @property
    def left_rate(self) -> float | None:
        return self._rate(self.n_left)

    @property
    def right_rate(self) -> float | None:
        return self._rate(self.n_right)

    @property
    def intrusion_rate(self) -> float | None:
        """§6.5 "karışım yanıtı oranı" — reports matching neither syllable."""
        return self._rate(self.n_other)

    @property
    def laterality_index(self) -> float | None:
        """KAİ = [(Sağ - Sol) / (Sağ + Sol)] x 100.  Positive = right ear.

        ``None`` when neither ear was ever reported.  Returning 0 there would
        read as "perfectly symmetrical" for a participant who in fact reported
        neither of the syllables that were presented — the one case where the
        index says nothing at all.
        """
        if not self.n_lateralised:
            return None
        return 100.0 * (self.n_right - self.n_left) / self.n_lateralised

    def _rate(self, count: int) -> float | None:
        return count / self.n_answered if self.n_answered else None


#: Shared with the other modules' measures (``base.row_value``).
_field = row_value


def _dichotic_rows(rows: Iterable[Any]) -> list[Any]:
    """Keep the dichotic trials.

    One row per trial: ``v_trials_flat`` LEFT JOINs ``responses``, so a timeout
    is still a row — with no response on it.
    """
    return [
        row
        for row in rows
        if _field(row, "module") is None or _field(row, "module") == MODULE_NAME
    ]


def _tally(rows: Iterable[Any]) -> EarAdvantage:
    counts: Counter[str] = Counter()
    n_trials = 0
    for row in rows:
        n_trials += 1
        category = _field(row, "category")
        if category is None:
            counts[NONE] += 1
            continue
        if category not in CATEGORIES:
            raise ModuleError(
                f"Dikotik denemesinde bilinmeyen kategori: {category!r}. "
                f"Beklenen: {list(CATEGORIES)}"
            )
        counts[str(category)] += 1
    return EarAdvantage(
        n_trials=n_trials,
        n_left=counts[LEFT],
        n_right=counts[RIGHT],
        n_other=counts[OTHER],
        n_missing=counts[NONE],
    )


def ear_advantage(rows: Iterable[Any]) -> EarAdvantage:
    """The module's headline measure, over every dichotic trial."""
    return _tally(_dichotic_rows(rows))


def ear_advantage_by_pair(rows: Iterable[Any]) -> dict[str, EarAdvantage]:
    """The same tally per stimulus pair, keyed by ``condition_label``.

    Not a reported measure — §6.5 computes the index over all trials — but the
    one place a stimulus artefact would show: if every pair containing /ga/ is
    reported as /ga/ regardless of the side it came from, the asymmetry is in
    the tokens rather than in the ears.
    """
    grouped: dict[str, list[Any]] = {}
    for row in _dichotic_rows(rows):
        grouped.setdefault(str(_field(row, "condition_label")), []).append(row)
    return {label: _tally(group) for label, group in sorted(grouped.items())}


def mean_rt_ms(rows: Iterable[Any], column: str = "rt_from_burst_ms") -> float | None:
    """Mean reaction time over the answered dichotic trials.

    Both references are recorded per response (``rt_from_burst_ms`` from the
    acoustic burst, ``rt_from_prompt_ms`` from the moment the options appear);
    which one is summarised here is the caller's choice, and the analysis in
    Adım 9 reads them from the database rather than from this helper.
    """
    values = [
        float(value)
        for row in _dichotic_rows(rows)
        if (value := _field(row, column)) is not None
    ]
    return sum(values) / len(values) if values else None


def summarise_measures(rows: Iterable[Any]) -> str:
    """The module's measures as a block of text, for the operator's console."""
    rows = list(rows)
    stats = ear_advantage(rows)
    lines = [
        f"Deneme                 : {stats.n_trials} "
        f"({stats.n_answered} yanıtlanan, {stats.n_missing} yanıtsız)",
        f"Sol kulak bildirimi    : {_percent(stats.left_rate)} ({stats.n_left})",
        f"Sağ kulak bildirimi    : {_percent(stats.right_rate)} ({stats.n_right})",
        f"Karışım yanıtı         : {_percent(stats.intrusion_rate)} ({stats.n_other})",
    ]
    index = stats.laterality_index
    lines.append(
        "Kulak avantajı (KAİ)   : "
        + ("—" if index is None else f"{index:+.1f}  [(Sağ-Sol)/(Sağ+Sol)]x100")
    )
    if index is None:
        lines.append(
            "  (hiçbir denemede sunulan hecelerden biri bildirilmedi — indeks "
            "tanımsız)"
        )
    burst = mean_rt_ms(rows, "rt_from_burst_ms")
    prompt = mean_rt_ms(rows, "rt_from_prompt_ms")
    lines.append(
        "Ortalama RT            : "
        + ("—" if burst is None else f"{burst:.0f} ms (patlamadan)")
        + ("" if prompt is None else f", {prompt:.0f} ms (yanıt ekranından)")
    )

    by_pair = ear_advantage_by_pair(rows)
    if by_pair:
        lines.append("Çift bazında (sol / sağ / karışım / yanıtsız):")
        for label, pair_stats in by_pair.items():
            lines.append(
                f"  {label:<24}{pair_stats.n_left:>4}{pair_stats.n_right:>6}"
                f"{pair_stats.n_other:>10}{pair_stats.n_missing:>10}"
            )
    return "\n".join(lines)


def _percent(value: float | None) -> str:
    return "—" if value is None else f"%{100 * value:.1f}"


# ---------------------------------------------------------------- inspection


def cell_counts(planned: Sequence[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(label, tokens, ear, noise)``.

    Built from the plan that will actually run rather than recomputed from the
    config, so a bug in the generator shows up as a wrong table.
    """
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        left = str(trial.design_extra.get("left_token"))
        right = str(trial.design_extra.get("right_token"))
        counts[
            (
                trial.condition_label,
                f"L-{left}/R-{right}",
                str(trial.ear),
                QUIET,
            )
        ] += 1
    return dict(counts)
