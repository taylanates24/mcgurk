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
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

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
