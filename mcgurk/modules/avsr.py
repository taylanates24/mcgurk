"""Modül 2 — AVSR: audiovisual speech recognition in three presentation modes.

No PsychoPy here, for the same reason as ``mcgurk.py``: the design, the scoring
and the derived measures all have to be checkable in CI.

What makes this module different from Modül 1 is not the loop but the meaning
of a response.  Here there **is** a correct answer — the item that was
presented — so ``is_correct`` is written (the §A.10 trigger only refuses it for
``mcgurk`` and ``dichotic``).  The measures that come out of it are the ones
the method document asks for:

* **lipreading** — accuracy in V-only;
* **visual benefit** — accuracy(AV) − accuracy(A), in the same noise and ear
  condition, which is the quantity the SSD hypothesis is about.

Two design rules are easy to get wrong:

* **V-only is not crossed with noise or ear.**  A silent video has no SNR and
  no side; crossing them would quadruple the cell for nothing and produce four
  groups of trials that are physically identical (steps.md §C Adım 5).  Those
  trials record NULL rather than "quiet"/"both" — NULL says *not applicable*,
  which is a different statement from "quiet, both ears".
* **``reps`` is per item per cell.**  ``reps: 5`` with three syllables is 15
  presentations in each of the A and AV cells and 15 in V-only altogether.
  ``config.trial_counts()`` is the authority and a test asserts the generator
  matches it.
"""

from __future__ import annotations

import logging
import random
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.schema import AVSRConfig, ExperimentConfig, StimulusSet
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

MODULE_NAME = "avsr"

#: Presentation modes, matching ``trials.presentation_mode``.
AUDIO_ONLY = "A"
VISUAL_ONLY = "V"
AUDIOVISUAL = "AV"

#: Identifies a design cell for the per-cell bookkeeping (noise instances).
CellKey = tuple[str, str, str, float | None, str | None]


class OpenSetNotImplemented(NotImplementedError):
    """``response_mode: open_set`` was asked for.

    A distinct class so the runner and the dry-run can both surface it as the
    same, deliberate gap rather than as a crash (steps.md §C Adım 5).
    """


def check_response_mode(module: AVSRConfig) -> None:
    """Refuse ``open_set`` clearly, before anything is presented."""
    if module.response_mode == "open_set":
        raise OpenSetNotImplemented(
            "modules.avsr.response_mode: open_set henüz gerçeklenmedi. Açık set "
            "yanıt, katılımcının yazdığı metnin puanlanmasını gerektirir "
            "(transkripsiyon kuralları, kısmi kredi, Türkçe klavye) ve bu "
            "kararlar verilmedi. Bugün çalışan mod: closed_set."
        )


@dataclass(frozen=True)
class Cell:
    """One design cell: an item, in one presentation mode, in one condition.

    ``snr_db`` and ``ear`` are None in V-only — not "quiet" and not "both", but
    absent, because there is no audio for them to describe.
    """

    item: str
    stimulus_type: str
    mode: str
    snr_db: float | None
    ear: str | None

    @property
    def key(self) -> CellKey:
        return (self.item, self.stimulus_type, self.mode, self.snr_db, self.ear)

    @property
    def label(self) -> str:
        """``trials.condition_label`` — the presentation mode."""
        return self.mode


def design_cells(module: AVSRConfig) -> tuple[list[Cell], list[int]]:
    """The full crossing, plus the repetition count of each cell."""
    cells: list[Cell] = []
    reps: list[int] = []

    for stimulus_set in module.stimulus_sets:
        if not stimulus_set.enabled:
            continue
        for item in stimulus_set.items():
            for mode in module.presentation_modes:
                for cell in _cells_for(item, stimulus_set, mode, module):
                    cells.append(cell)
                    reps.append(stimulus_set.reps)
    return cells, reps


def _cells_for(
    item: str, stimulus_set: StimulusSet, mode: str, module: AVSRConfig
) -> list[Cell]:
    if mode == VISUAL_ONLY:
        return [
            Cell(
                item=item,
                stimulus_type=stimulus_set.type,
                mode=mode,
                snr_db=None,
                ear=None,
            )
        ]
    return [
        Cell(
            item=item,
            stimulus_type=stimulus_set.type,
            mode=mode,
            snr_db=snr_db,
            ear=ear,
        )
        for snr_db in module.noise_conditions
        for ear in module.ears
    ]


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
        speaker_id: Overrides ``modules.avsr.speaker_id`` (Adım 8, §F.4).

    Raises:
        ModuleError: the module is disabled, or the prepared set does not
            contain something the design asks for.
        OpenSetNotImplemented: ``response_mode: open_set``.
    """
    module = config.modules.avsr
    if not module.enabled:
        raise ModuleError(
            "modules.avsr.enabled false — devre dışı bir modül için deneme "
            "listesi üretilmez"
        )
    check_response_mode(module)

    speaker = speaker_id if speaker_id is not None else module.speaker_id
    noise_name = config.stimulus_prep.noise.type
    rng = random.Random(derive_seed(seed, MODULE_NAME))

    cells, reps = design_cells(module)
    ordered = order_cells(cells, reps, rng, module.randomization)

    # Noise instances: balanced within a cell rather than drawn independently,
    # so ten repetitions of one cell are not seven repetitions of one waveform.
    # Drawn after the ordering, so the trial order for a given seed does not
    # depend on how many instances the prepared set happens to hold.
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
        "AVSR tasarımı: %d deneme (%d hücre, modlar %s, %s), konuşmacı %d, tohum %d",
        len(planned),
        len(cells),
        "/".join(module.presentation_modes),
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
        return manifest.noisy(speaker, cell.item, cell.item, cell.snr_db)
    except ManifestError as exc:
        raise ModuleError(_missing(exc, cell)) from exc


def _missing(exc: ManifestError, cell: Cell) -> str:
    hint = (
        "Uyaran seti bu tasarımla hazırlanmamış: python tools/prepare_stimuli.py"
    )
    if cell.stimulus_type == "word":
        hint = (
            f"'{cell.item}' kelimesi hazırlanmış sette yok. Kelime seti "
            "(§F.2) için önce kayıt yapılmalı, kelimeler "
            "stimulus_prep.tokens'a eklenmeli ve "
            "'python tools/prepare_stimuli.py' koşulmalı."
        )
    return f"{exc}\n{hint}"


def _plan_one(
    manifest: StimulusManifest,
    cell: Cell,
    *,
    speaker: int,
    stimuli_root: Path,
    noise_name: str,
    noisy: NoisyTokenEntry | None,
) -> PlannedTrial:
    """Resolve one cell to files and to a database row.

    The stimuli are the **congruent** takes: in this module the visual and the
    acoustic token are the same item, and what varies is which of the two the
    participant gets.
    """
    video_path: Path | None = None
    video_burst_s = 0.0
    audio_path: Path | None = None
    audio_burst_s = 0.0

    try:
        if cell.mode in (VISUAL_ONLY, AUDIOVISUAL):
            video = manifest.video(speaker, cell.item)
            video_path = video.file.resolve(stimuli_root)
            video_burst_s = video.burst_time_s
        if cell.mode in (AUDIO_ONLY, AUDIOVISUAL):
            clean = manifest.token(speaker, cell.item, cell.item)
            entry = noisy if noisy is not None else clean
            audio_path = entry.file.resolve(stimuli_root)
            # The noisy derivative is the clean token plus noise of the same
            # length, so its burst is the clean token's (Adım 2).
            audio_burst_s = clean.burst_time_s
    except ManifestError as exc:
        raise ModuleError(_missing(exc, cell)) from exc

    spec = TrialSpec(
        label=f"{cell.mode}-{cell.item}",
        video_path=video_path,
        video_burst_s=video_burst_s,
        audio_path=audio_path,
        audio_burst_s=audio_burst_s,
        # No audio in V-only, so the ear is not a manipulation there; the
        # presenter still needs a valid value and "both" is the one that
        # changes nothing.
        ear=cell.ear or "both",
    )
    trial = Trial(
        block_id=0,  # the runner fills this in
        trial_index=0,
        module=MODULE_NAME,
        condition_label=cell.label,
        visual_token=cell.item if video_path is not None else None,
        audio_token=cell.item if audio_path is not None else None,
        ear=cell.ear,
        snr_db=cell.snr_db,
        noise_condition=_noise_condition(cell, noise_name),
        nominal_soa_ms=None,
        presentation_mode=cell.mode,
        design_extra={
            "speaker_id": speaker,
            "noise_instance": None if noisy is None else noisy.instance,
            "stimulus_type": cell.stimulus_type,
            "item": cell.item,
        },
    )
    return PlannedTrial(spec=spec, trial=trial)


def _noise_condition(cell: Cell, noise_name: str) -> str | None:
    if cell.mode == VISUAL_ONLY:
        return None  # not applicable — there is no audio to be quiet or noisy
    return QUIET if cell.snr_db is None else noise_name


# --------------------------------------------------------------------- scoring


def score(response: str | None, item: str) -> bool | None:
    """Was *response* the item that was presented?

    None for a no-response, which is what the caller has on a timeout.  How a
    timeout enters an accuracy figure is decided in :func:`tally`, not here.
    """
    if response is None or not response.strip():
        return None
    return response.strip().casefold() == item.casefold()


def score_for(response: str | None, trial: Trial) -> bool | None:
    """:func:`score` against the item recorded on *trial*."""
    item = trial.design_extra.get("item")
    if not isinstance(item, str) or not item:
        raise ModuleError(
            "AVSR denemesinde design_extra['item'] bulunmalı — yanıt neye karşı "
            "puanlanacağı ondan geliyor"
        )
    return score(response, item)


# -------------------------------------------------------------------- measures


@dataclass(frozen=True)
class Accuracy:
    """Correct out of presented, and how many of those were no-responses.

    A timeout counts as **incorrect**, not as a missing observation: excluding
    it would raise the accuracy of exactly the participants who could not
    answer in time, which is the effect the study is looking for.  ``n_missing``
    is carried alongside so a condition that is mostly timeouts is visible
    rather than merely low.
    """

    n_trials: int = 0
    n_correct: int = 0
    n_missing: int = 0

    @property
    def accuracy(self) -> float | None:
        return self.n_correct / self.n_trials if self.n_trials else None

    def __str__(self) -> str:
        if self.accuracy is None:
            return "—"
        return f"%{100 * self.accuracy:.1f} ({self.n_correct}/{self.n_trials})"


def _field(row: Mapping[str, Any] | Any, key: str) -> Any:
    """Read *key* from a mapping or a ``sqlite3.Row``; None when absent."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _avsr_rows(rows: Iterable[Any]) -> list[Any]:
    """Keep the AVSR trials.  One row per trial (``v_trials_flat`` LEFT JOINs,
    so a timeout is still a row — with no response on it)."""
    kept = []
    for row in rows:
        module = _field(row, "module")
        if module is None or module == MODULE_NAME:
            kept.append(row)
    return kept


def _tally(rows: Iterable[Any]) -> Accuracy:
    n_trials = n_correct = n_missing = 0
    for row in rows:
        n_trials += 1
        correct = _field(row, "is_correct")
        if correct is None:
            n_missing += 1
        elif correct:
            n_correct += 1
    return Accuracy(n_trials=n_trials, n_correct=n_correct, n_missing=n_missing)


def accuracy_by_mode(rows: Iterable[Any]) -> dict[str, Accuracy]:
    """Accuracy per presentation mode — the module's headline numbers."""
    grouped: dict[str, list[Any]] = {}
    for row in _avsr_rows(rows):
        grouped.setdefault(str(_field(row, "presentation_mode")), []).append(row)
    return {mode: _tally(group) for mode, group in grouped.items()}


def accuracy_by_condition(
    rows: Iterable[Any],
) -> dict[tuple[str, float | None, str | None], Accuracy]:
    """Accuracy per ``(mode, snr_db, ear)``.

    V-only lands in ``("V", None, None)``: it has no noise level and no side,
    which is the whole reason it is not crossed with them.
    """
    grouped: dict[tuple[str, float | None, str | None], list[Any]] = {}
    for row in _avsr_rows(rows):
        key = (
            str(_field(row, "presentation_mode")),
            _field(row, "snr_db"),
            _field(row, "ear"),
        )
        grouped.setdefault(key, []).append(row)
    return {key: _tally(group) for key, group in grouped.items()}


def lipreading_accuracy(rows: Iterable[Any]) -> float | None:
    """Accuracy in V-only — how much the participant gets from the face alone."""
    return accuracy_by_mode(rows).get(VISUAL_ONLY, Accuracy()).accuracy


def visual_benefit(rows: Iterable[Any]) -> float | None:
    """AV − A, pooled over noise and ear.

    None when either mode is missing from *rows*: a benefit index computed
    against no baseline would be a number with no meaning.
    """
    by_mode = accuracy_by_mode(rows)
    audiovisual = by_mode.get(AUDIOVISUAL, Accuracy()).accuracy
    audio = by_mode.get(AUDIO_ONLY, Accuracy()).accuracy
    if audiovisual is None or audio is None:
        return None
    return audiovisual - audio


def visual_benefit_by_condition(
    rows: Iterable[Any],
) -> dict[tuple[float | None, str | None], float]:
    """AV − A within each ``(snr_db, ear)`` cell.

    This is the form the SSD hypothesis is tested in: the benefit is expected
    to depend on the noise level and on which ear the audio was sent to.
    """
    by_condition = accuracy_by_condition(rows)
    benefits: dict[tuple[float | None, str | None], float] = {}
    for (mode, snr_db, ear), stats in by_condition.items():
        if mode != AUDIOVISUAL or stats.accuracy is None:
            continue
        baseline = by_condition.get((AUDIO_ONLY, snr_db, ear))
        if baseline is None or baseline.accuracy is None:
            continue
        benefits[(snr_db, ear)] = stats.accuracy - baseline.accuracy
    return benefits


def summarise_measures(rows: Iterable[Any]) -> str:
    """The module's measures as a block of text, for the operator's console."""
    rows = list(rows)
    by_mode = accuracy_by_mode(rows)
    lines = ["Doğruluk (mod):"]
    for mode in (AUDIO_ONLY, VISUAL_ONLY, AUDIOVISUAL):
        stats = by_mode.get(mode)
        if stats is None:
            continue
        missing = f", {stats.n_missing} yanıtsız" if stats.n_missing else ""
        lines.append(f"  {mode:<4}{stats}{missing}")

    benefit = visual_benefit(rows)
    lines.append(
        "Görsel fayda (AV - A)  : "
        + ("—" if benefit is None else f"%{100 * benefit:+.1f}")
    )
    lipreading = lipreading_accuracy(rows)
    lines.append(
        "Lipreading (V)         : "
        + ("—" if lipreading is None else f"%{100 * lipreading:.1f}")
    )

    by_condition = visual_benefit_by_condition(rows)
    if by_condition:
        lines.append("Görsel fayda (gürültü × kulak):")
        for (snr_db, ear), value in sorted(
            by_condition.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
        ):
            noise = "sessiz" if snr_db is None else f"{snr_db:g} dB"
            lines.append(f"  {noise:<10}{str(ear):<8}%{100 * value:+.1f}")
    return "\n".join(lines)


# ---------------------------------------------------------------- inspection


def cell_counts(planned: Sequence[PlannedTrial]) -> dict[tuple[str, str, str, str], int]:
    """Trials per cell, keyed by ``(mode, item, ear, noise)``.

    Built from the plan that will actually run rather than recomputed from the
    config, so a bug in the generator shows up as a wrong table.
    """
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for item in planned:
        trial = item.trial
        counts[
            (
                trial.condition_label,
                str(trial.design_extra.get("item")),
                "—" if trial.ear is None else str(trial.ear),
                _noise_label(trial.snr_db, trial.presentation_mode),
            )
        ] += 1
    return dict(counts)


def _noise_label(snr_db: float | None, mode: str | None) -> str:
    if mode == VISUAL_ONLY:
        return "—"
    return QUIET if snr_db is None else f"{snr_db:g} dB"
