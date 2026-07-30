"""The practice warm-up (steps.md §C Adım 8).

Congruent audiovisual trials (Vis == Aud) that let the participant learn the
forced-choice response before any measurement begins.  Nothing here is analysed:
the trials are written to a ``practice`` block so the session stays reproducible,
but they carry no correct answer and no categorisation — the point is the
mechanic, not the percept.  No feedback is shown (§Don'ts): a warm-up that told
the participant they were right would prime them for the McGurk effect.

PsychoPy-free, like every design module — the warm-up list is built from the
config and the manifest and tested in CI.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from ..config.schema import ExperimentConfig
from ..db.models import Trial
from ..engine.av_presenter import TrialSpec
from ..stimuli.manifest import ManifestError, StimulusManifest
from .base import QUIET, ModuleError, PlannedTrial, balanced_cycle, derive_seed

logger = logging.getLogger(__name__)

MODULE_NAME = "practice"


def plan_trials(
    config: ExperimentConfig,
    manifest: StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    speaker_id: int | None = None,
) -> list[PlannedTrial]:
    """Build ``session.practice_trials`` congruent AV warm-up trials.

    The tokens are cycled through balanced (``balanced_cycle``) and shuffled from
    the session seed, so the same seed gives the same warm-up.  ``speaker_id``
    defaults to McGurk's speaker, since the warm-up mirrors that response screen.
    """
    n = config.session.practice_trials
    if n <= 0:
        return []
    speaker = speaker_id if speaker_id is not None else config.modules.mcgurk.speaker_id
    tokens = list(config.stimulus_prep.tokens)
    rng = random.Random(derive_seed(seed, MODULE_NAME))
    order = balanced_cycle(len(tokens), n, rng)
    planned = [
        _plan_one(manifest, tokens[index], speaker=speaker, stimuli_root=stimuli_root)
        for index in order
    ]
    logger.info(
        "Alıştırma tasarımı: %d uyumlu deneme, konuşmacı %d, tohum %d",
        len(planned),
        speaker,
        seed,
    )
    return planned


def _plan_one(
    manifest: StimulusManifest, token: str, *, speaker: int, stimuli_root: Path
) -> PlannedTrial:
    try:
        video = manifest.video(speaker, token)
        clean = manifest.token(speaker, token, token)  # congruent take
    except ManifestError as exc:
        raise ModuleError(
            f"{exc}\nAlıştırma için uyaran hazır değil: python tools/prepare_stimuli.py"
        ) from exc

    spec = TrialSpec(
        label=f"practice_{token}",
        video_path=video.file.resolve(stimuli_root),
        video_burst_s=video.burst_time_s,
        audio_path=clean.file.resolve(stimuli_root),
        audio_burst_s=clean.burst_time_s,
        ear="both",
    )
    trial = Trial(
        block_id=0,  # the runner fills this in
        trial_index=0,
        module=MODULE_NAME,
        condition_label=f"practice_{token}",
        visual_token=token,
        audio_token=token,
        ear="both",
        snr_db=None,
        noise_condition=QUIET,
        nominal_soa_ms=None,
        presentation_mode="AV",
        design_extra={},  # practice fits the shared columns (NoExtra)
    )
    return PlannedTrial(spec=spec, trial=trial)
