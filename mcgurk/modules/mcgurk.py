"""Modül 1 — McGurk: what to present, and what a response means.

No PsychoPy here.  Two questions are answered in this file and both have to be
answerable in CI:

* **the design** — the crossing of ``av_pairs × noise_conditions × ears``, the
  seeded order, and which prepared file each cell resolves to;
* **the categorisation** — whether a response is auditory, visual, a fusion, a
  combination, or none of those.

The categorisation maps come from the config (§A.9).  Hard-coding
"Vis-/ga/ + Aud-/ba/ → /da/ is a fusion" would put a theoretical claim in the
source: which responses count as fused is exactly the kind of thing a reviewer
can ask to see changed, and the answer must not be a code edit.

There is no correct answer in this module (§A.10), congruent controls included:
the database refuses ``is_correct`` on every ``mcgurk`` trial, and a congruent
trial answered with its audio token is recorded as ``AUDITORY`` — which is the
same information, expressed as a percept rather than as a score.
"""

from __future__ import annotations

import logging
import random
import statistics
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.schema import AVPair, ExperimentConfig, McGurkConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
from ..stimuli.manifest import ManifestError, NoisyTokenEntry, StimulusManifest
from .base import (
    QUIET,
    ModuleError,
    PlannedTrial,
    balanced_cycle,
    derive_seed,
    order_cells,
    row_value,
)

logger = logging.getLogger(__name__)

MODULE_NAME = "mcgurk"

#: Response categories (steps.md §C Adım 4).  ``NONE`` is what a trial with no
#: response row means; it is never written to the database as a category,
#: because the absence of the row is the record (Adım 1 decision).
AUDITORY = "AUDITORY"
VISUAL = "VISUAL"
FUSION = "FUSION"
COMBINATION = "COMBINATION"
OTHER = "OTHER"
NONE = "NONE"

CATEGORIES = (AUDITORY, VISUAL, FUSION, COMBINATION, OTHER, NONE)

#: Identifies a design cell for the per-cell bookkeeping (noise instances).
CellKey = tuple[str, str, float | None, str]


@dataclass(frozen=True)
class Cell:
    """One design cell: an AV pair, in one noise condition, in one ear."""

    pair: AVPair
    snr_db: float | None
    ear: str

    @property
    def key(self) -> CellKey:
        return (self.pair.visual, self.pair.audio, self.snr_db, self.ear)


def design_cells(module: McGurkConfig) -> tuple[list[Cell], list[int]]:
    """The full crossing, plus the repetition count of each cell.

    ``reps`` is per cell, not per pair: a pair with ``reps: 10`` is presented
    ten times in *every* noise × ear combination, which is why the module's
    total is ``sum(reps) × len(noise) × len(ears)``.
    """
    cells: list[Cell] = []
    reps: list[int] = []
    for pair in module.av_pairs:
        for snr_db in module.noise_conditions:
            for ear in module.ears:
                cells.append(Cell(pair=pair, snr_db=snr_db, ear=ear))
                reps.append(pair.reps)
    return cells, reps


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
        seed: The **session** seed.  The module's own stream is derived from it
            (:func:`~mcgurk.modules.base.derive_seed`).
        stimuli_root: ``paths.stimuli``, already resolved.
        speaker_id: Overrides ``modules.mcgurk.speaker_id``.  The session flow
            (Adım 8) needs this for the ``balanced``/``random`` speaker
            strategies (§F.4); the module itself has no opinion on which
            speaker a participant gets.

    Raises:
        ModuleError: the module is disabled, or the prepared set does not
            contain something the design asks for.  Failing here means failing
            before the participant sits down, which is the whole point of
            resolving every path up front.
    """
    module = config.modules.mcgurk
    if not module.enabled:
        raise ModuleError(
            "modules.mcgurk.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )

    speaker = speaker_id if speaker_id is not None else module.speaker_id
    noise_name = config.stimulus_prep.noise.type
    rng = random.Random(derive_seed(seed, MODULE_NAME))

    cells, reps = design_cells(module)
    ordered = order_cells(cells, reps, rng, module.randomization)

    # Noise instances are drawn per cell, balanced over that cell's repetitions,
    # and consumed in the order the cell's trials come up.  Drawing them after
    # the ordering keeps the two decisions separable: the same seed gives the
    # same trial order whichever instances the prepared set happens to hold.
    variants: dict[CellKey, list[NoisyTokenEntry]] = {}
    draws: dict[CellKey, list[int]] = {}
    for cell, count in zip(cells, reps, strict=True):
        if cell.snr_db is None:
            continue
        entries = _noisy_variants(manifest, speaker, cell)
        variants[cell.key] = entries
        draws[cell.key] = balanced_cycle(len(entries), count, rng)
    used: Counter[CellKey] = Counter()

    planned: list[PlannedTrial] = []
    for cell in ordered:
        noisy: NoisyTokenEntry | None = None
        if cell.snr_db is not None:
            noisy = variants[cell.key][draws[cell.key][used[cell.key]]]
            used[cell.key] += 1
        planned.append(
            _plan_one(
                manifest,
                cell,
                speaker=speaker,
                stimuli_root=stimuli_root,
                noise_name=noise_name,
                noisy=noisy,
            )
        )

    logger.info(
        "McGurk tasarımı: %d deneme (%d hücre, %s), konuşmacı %d, tohum %d",
        len(planned),
        len(cells),
        module.randomization,
        speaker,
        seed,
    )
    return planned


def _noisy_variants(
    manifest: StimulusManifest, speaker: int, cell: Cell
) -> list[NoisyTokenEntry]:
    assert cell.snr_db is not None
    try:
        return manifest.noisy(speaker, cell.pair.visual, cell.pair.audio, cell.snr_db)
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nUyaran seti bu tasarımla hazırlanmamış: "
            "python tools/prepare_stimuli.py"
        ) from exc


def _plan_one(
    manifest: StimulusManifest,
    cell: Cell,
    *,
    speaker: int,
    stimuli_root: Path,
    noise_name: str,
    noisy: NoisyTokenEntry | None,
) -> PlannedTrial:
    try:
        video = manifest.video(speaker, cell.pair.visual)
        clean = manifest.token(speaker, cell.pair.visual, cell.pair.audio)
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nUyaran seti bu tasarımla hazırlanmamış: "
            "python tools/prepare_stimuli.py"
        ) from exc

    entry = noisy if noisy is not None else clean
    audio_path = entry.file.resolve(stimuli_root)

    # The noisy derivative is the clean token plus a noise excerpt of the same
    # length (Adım 2 mixes, it does not shift), so the burst sits where the
    # clean token's does and the manifest records it only once.
    spec = TrialSpec(
        label=cell.pair.label,
        video_path=video.file.resolve(stimuli_root),
        video_burst_s=video.burst_time_s,
        audio_path=audio_path,
        audio_burst_s=clean.burst_time_s,
        ear=cell.ear,
    )
    trial = Trial(
        block_id=0,  # the runner fills this in
        trial_index=0,
        module=MODULE_NAME,
        condition_label=cell.pair.label,
        visual_token=cell.pair.visual,
        audio_token=cell.pair.audio,
        ear=cell.ear,
        snr_db=cell.snr_db,
        noise_condition=QUIET if cell.snr_db is None else noise_name,
        nominal_soa_ms=None,
        presentation_mode="AV",
        design_extra={
            "speaker_id": speaker,
            "noise_instance": None if noisy is None else noisy.instance,
        },
    )
    return PlannedTrial(spec=spec, trial=trial)


# ------------------------------------------------------------ categorisation


def categorise(
    response: str | None,
    *,
    visual_token: str,
    audio_token: str,
    fusion_map: Mapping[str, list[str]] | None = None,
    combination_map: Mapping[str, list[str]] | None = None,
) -> str:
    """Classify one raw response.

    The order is fixed and the config validation depends on it: the audio and
    visual tokens are checked first, so a map listing one of them would be an
    unreachable rule (``McGurkConfig`` rejects that at load).

    A free-text answer is *not* classified from its text.  The participant chose
    "other" while the option they typed was on the screen; recording that as the
    percept the option would have meant would be inventing a response they
    declined to give.  The text is stored verbatim for review instead.
    """
    if response is None or not response.strip():
        return NONE

    answer = response.strip().casefold()
    if answer == audio_token.casefold():
        return AUDITORY
    if answer == visual_token.casefold():
        return VISUAL

    key = f"{visual_token}|{audio_token}"
    if answer in {value.casefold() for value in (fusion_map or {}).get(key, [])}:
        return FUSION
    if answer in {value.casefold() for value in (combination_map or {}).get(key, [])}:
        return COMBINATION
    return OTHER


def categorise_for(module: McGurkConfig, response: str | None, trial: Trial) -> str:
    """:func:`categorise` with the maps and tokens of an actual trial."""
    if trial.visual_token is None or trial.audio_token is None:
        raise ModuleError(
            "McGurk denemesinde görsel ve işitsel token birlikte bulunmalı"
        )
    return categorise(
        response,
        visual_token=trial.visual_token,
        audio_token=trial.audio_token,
        fusion_map=module.fusion_map,
        combination_map=module.combination_map,
    )


# -------------------------------------------------------------------- measures


#: The order categories are reported in — auditory, visual, then the two McGurk
#: percepts, then the leftovers.  Fixed so a table always reads the same way.
_REPORT_ORDER = (AUDITORY, VISUAL, FUSION, COMBINATION, OTHER, NONE)

#: Turkish labels for the console.  ``NONE`` is a timeout, not a percept.
_CATEGORY_LABELS = {
    AUDITORY: "İşitsel",
    VISUAL: "Görsel baskınlık",
    FUSION: "Füzyon",
    COMBINATION: "Kombinasyon",
    OTHER: "Diğer",
    NONE: "Yanıtsız",
}


@dataclass(frozen=True)
class McGurkRates:
    """The category proportions of one set of McGurk trials, plus RT.

    There is no correct answer here (§A.10): the headline numbers are the rates
    at which each percept was reported, not an accuracy.  ``NONE`` is a timeout
    — a trial with no response row — and it is kept in ``n_trials`` so a
    condition that is mostly timeouts reads as a low fusion rate rather than an
    absent one.  The reaction time is measured only over the trials that were
    answered.
    """

    counts: Mapping[str, int]
    n_trials: int
    mean_rt_ms: float | None = None
    sd_rt_ms: float | None = None
    n_rt: int = 0

    def rate(self, category: str) -> float | None:
        """Proportion of trials in *category*; None when there are no trials."""
        if not self.n_trials:
            return None
        return self.counts.get(category, 0) / self.n_trials

    @property
    def fusion_rate(self) -> float | None:
        return self.rate(FUSION)

    @property
    def visual_rate(self) -> float | None:
        """Visual dominance — the video's token reported over the audio's."""
        return self.rate(VISUAL)

    @property
    def auditory_rate(self) -> float | None:
        return self.rate(AUDITORY)

    @property
    def combination_rate(self) -> float | None:
        return self.rate(COMBINATION)


@dataclass
class _TrialResult:
    snr_db: float | None
    ear: str | None
    category: str = NONE
    rt_ms: float | None = None


def _trial_results(rows: Iterable[Any]) -> list[_TrialResult]:
    """One outcome per McGurk trial, read off ``v_trials_flat`` rows.

    A trial with no response row is a timeout (``NONE``); the LEFT JOIN keeps it
    visible, which is the only reason a timeout can be counted at all.  A row
    whose module is unset is treated as this module's — a synthetic test row
    need not carry it.
    """
    results: dict[int, _TrialResult] = {}
    order: list[int] = []
    for row in rows:
        module = row_value(row, "module")
        if module is not None and module != MODULE_NAME:
            continue
        trial_id = row_value(row, "trial_id")
        if trial_id is None:
            raise ModuleError("McGurk satırında trial_id yok")
        trial_id = int(trial_id)
        if trial_id not in results:
            order.append(trial_id)
            results[trial_id] = _TrialResult(
                snr_db=row_value(row, "snr_db"),
                ear=row_value(row, "ear"),
            )
        if row_value(row, "response_id") is None:
            continue
        category = row_value(row, "category")
        # A response that categorisation did not place is OTHER; it never
        # reaches the database as NULL, but analysis must not trust that.
        results[trial_id].category = category if category in CATEGORIES else OTHER
        rt = row_value(row, "rt_from_burst_ms")
        results[trial_id].rt_ms = None if rt is None else float(rt)
    return [results[trial_id] for trial_id in order]


def _tally(results: Iterable[_TrialResult]) -> McGurkRates:
    counts: Counter[str] = Counter()
    rts: list[float] = []
    n_trials = 0
    for result in results:
        n_trials += 1
        counts[result.category] += 1
        if result.category != NONE and result.rt_ms is not None:
            rts.append(result.rt_ms)
    return McGurkRates(
        counts=dict(counts),
        n_trials=n_trials,
        mean_rt_ms=statistics.fmean(rts) if rts else None,
        sd_rt_ms=statistics.stdev(rts) if len(rts) > 1 else None,
        n_rt=len(rts),
    )


def rates_from_rows(rows: Iterable[Any]) -> McGurkRates:
    """The module's headline rates, pooled over noise and ear."""
    return _tally(_trial_results(rows))


def rates_by_condition(
    rows: Iterable[Any],
) -> dict[tuple[float | None, str | None], McGurkRates]:
    """Rates within each ``(snr_db, ear)`` cell — the form the SSD hypothesis
    is tested in: fusion is expected to depend on the noise level and on which
    ear the audio was sent to."""
    grouped: dict[tuple[float | None, str | None], list[_TrialResult]] = {}
    for result in _trial_results(rows):
        grouped.setdefault((result.snr_db, result.ear), []).append(result)
    return {key: _tally(group) for key, group in grouped.items()}


def summarise_measures(rows: Iterable[Any]) -> str:
    """The module's measures as a block of text, for the operator's console."""
    rows = list(rows)
    rates = rates_from_rows(rows)
    if not rates.n_trials:
        return "McGurk: kayıtlı deneme yok."

    lines = [f"McGurk kategorileri (n={rates.n_trials}):"]
    for category in _REPORT_ORDER:
        count = rates.counts.get(category, 0)
        rate = rates.rate(category)
        shown = "—" if rate is None else f"%{100 * rate:.1f}"
        lines.append(f"  {_CATEGORY_LABELS[category]:<16}: {shown} ({count})")

    if rates.mean_rt_ms is not None:
        sd = "" if rates.sd_rt_ms is None else f" (SD {rates.sd_rt_ms:.0f})"
        lines.append(
            f"Ortalama RT (patlama)  : {rates.mean_rt_ms:.0f} ms{sd}, "
            f"{rates.n_rt} yanıt"
        )

    by_condition = rates_by_condition(rows)
    if len(by_condition) > 1:
        lines.append("Füzyon oranı (gürültü × kulak):")
        for (snr_db, ear), stats in sorted(
            by_condition.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
        ):
            noise = QUIET if snr_db is None else f"{snr_db:g} dB"
            fusion = stats.fusion_rate
            shown = "—" if fusion is None else f"%{100 * fusion:.1f}"
            lines.append(f"  {noise:<8} {str(ear):<6}: {shown} ({stats.n_trials})")
    return "\n".join(lines)


# ---------------------------------------------------------------- inspection


def cell_counts(planned: list[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(label, ear, noise, instance-free)``.

    The design summary the operator checks before a session: it is built from
    the plan that will actually run, not recomputed from the config, so a bug in
    the generator shows up as a wrong table rather than as a matching one.
    """
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        counts[
            (
                trial.condition_label,
                f"Vis-{trial.visual_token}/Aud-{trial.audio_token}",
                str(trial.ear),
                QUIET if trial.snr_db is None else f"{trial.snr_db:g} dB",
            )
        ] += 1
    return dict(counts)
