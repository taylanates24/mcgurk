"""Section definitions and trial generation for each experiment section."""

import logging
import random
from dataclasses import replace
from itertools import permutations
from typing import Any

from ..utils.assets import (
    Speaker,
    get_assets_dir,
    get_congruent_videos,
    get_incongruent_videos,
)
from .trial import TrialSpec

logger = logging.getLogger(__name__)


def generate_mcgurk_trials(
    speaker: Speaker, noise_condition: str = "clean", snr_db: float | None = None
) -> list[TrialSpec]:
    """Generate McGurk (incongruent) trials for a speaker.

    Uses all incongruent videos where visual != audio.
    Noise is mixed at runtime by the engine using assets/noise/.
    """
    return [
        TrialSpec(
            section_type="mcgurk",
            video_path=v.path,
            audio_path=None,
            visual_syllable=v.visual_syllable,
            audio_syllable=v.audio_syllable,
            noise_condition=noise_condition,
            snr_db=snr_db,
            correct_answer=v.audio_syllable,
            speaker_name=speaker.folder_name,
        )
        for v in get_incongruent_videos(speaker)
    ]


def generate_av_congruent_trials(
    speaker: Speaker, noise_condition: str = "clean", snr_db: float | None = None
) -> list[TrialSpec]:
    """Generate AV congruent trials (visual == audio).

    Noise is mixed at runtime by the engine using assets/noise/.
    """
    return [
        TrialSpec(
            section_type="av_congruent",
            video_path=v.path,
            audio_path=None,
            visual_syllable=v.visual_syllable,
            audio_syllable=v.audio_syllable,
            noise_condition=noise_condition,
            snr_db=snr_db,
            correct_answer=v.audio_syllable,
            speaker_name=speaker.folder_name,
        )
        for v in get_congruent_videos(speaker)
    ]


def generate_audio_only_trials(
    speaker: Speaker,
    syllables: list[str],
    noise_condition: str = "clean",
    snr_db: float | None = None,
) -> list[TrialSpec]:
    """Generate audio-only trials. Uses congruent videos for audio extraction.

    Noise is mixed at runtime by the engine using assets/noise/.
    """
    video_map = {v.audio_syllable: v for v in get_congruent_videos(speaker)}
    trials = []
    for syl in syllables:
        v = video_map.get(syl)
        if v is None:
            continue
        trials.append(
            TrialSpec(
                section_type="audio_only",
                video_path=None,
                audio_path=v.path,  # audio will be extracted from this video
                visual_syllable="",
                audio_syllable=syl,
                noise_condition=noise_condition,
                snr_db=snr_db,
                correct_answer=syl,
                speaker_name=speaker.folder_name,
            )
        )
    return trials


def generate_visual_only_trials(
    speaker: Speaker, syllables: list[str]
) -> list[TrialSpec]:
    """Generate visual-only trials. Uses congruent videos with audio muted."""
    videos = get_congruent_videos(speaker)
    video_map = {v.visual_syllable: v for v in videos}
    trials = []
    for syl in syllables:
        v = video_map.get(syl)
        if v:
            trials.append(
                TrialSpec(
                    section_type="visual_only",
                    video_path=v.path,
                    audio_path=None,
                    visual_syllable=syl,
                    audio_syllable=syl,
                    noise_condition="clean",
                    snr_db=None,
                    correct_answer=syl,
                    speaker_name=speaker.folder_name,
                )
            )
    return trials


def generate_dichotic_trials(
    syllables: list[str],
    speaker: Speaker,
) -> list[TrialSpec]:
    """Generate dichotic listening trials.

    Uses pre-generated stereo mp4 files from assets/dichotic/{speaker}/.
    Each file has one syllable per ear. Run scripts/generate_dichotic_stimuli.py first.
    """
    dichotic_dir = speaker.path.parent / "dichotic" / speaker.folder_name

    trials = []
    pairs = list(permutations(syllables, 2))
    for left_syl, right_syl in pairs:
        mp4_path = dichotic_dir / f"Left-{left_syl}_Right-{right_syl}.mp4"
        if not mp4_path.exists():
            continue
        trials.append(
            TrialSpec(
                section_type="dichotic",
                video_path=mp4_path,
                audio_path=None,
                visual_syllable="",
                audio_syllable=f"{left_syl}_L_{right_syl}_R",
                noise_condition="clean",
                snr_db=None,
                correct_answer=f"{left_syl}|{right_syl}",
                speaker_name=speaker.folder_name,
                ear_side="both",
            )
        )
    return trials


def build_trial_list(
    speaker: Speaker,
    selected_sections: list[str],
    config: dict[str, Any],
    seed: int,
    noisy_sections: list[str] | None = None,
) -> list[TrialSpec]:
    """Build the complete trial list for an experiment session.

    Args:
        speaker: Selected speaker.
        selected_sections: Sections to run in clean mode.
        config: Experiment config dict.
        seed: RNG seed for the trial shuffle.  The same seed always yields
            the same order, which is what makes a session reproducible.
        noisy_sections: Subset of sections that also run in noisy mode.
    """
    syllables = config.get("syllables", ["ba", "da", "ga"])
    repetitions = config.get("trial_repetitions", 1)
    snr_db = config.get("noise", {}).get("snr_db", 5)
    noisy_set = set(noisy_sections or [])

    # Discover all noise types from assets/noise/ (e.g. white, cocktail)
    noise_dir = get_assets_dir(config) / "noise"
    noise_types = [
        f.stem[: -len("_noise")]
        for f in sorted(noise_dir.iterdir())
        if f.is_file() and f.stem.endswith("_noise")
    ] if noise_dir.is_dir() else []
    if not noise_types:
        # Fallback to config value if no files found
        noise_types = [config.get("noise", {}).get("type", "white")]

    generators = {
        "mcgurk": lambda nc, snr: generate_mcgurk_trials(speaker, nc, snr),
        "av_congruent": lambda nc, snr: generate_av_congruent_trials(speaker, nc, snr),
        "audio_only": lambda nc, snr: generate_audio_only_trials(speaker, syllables, nc, snr),
        "visual_only": lambda nc, snr: generate_visual_only_trials(speaker, syllables),
        "dichotic": lambda nc, snr: generate_dichotic_trials(syllables, speaker),
    }

    # Collect all sections to run (union of clean + noisy)
    all_sections = list(dict.fromkeys(list(selected_sections) + list(noisy_set)))

    def _repeat(specs: list[TrialSpec]) -> list[TrialSpec]:
        """Return *specs* repeated ``repetitions`` times as distinct objects.

        ``specs * repetitions`` would repeat the *same* objects, and TrialSpec
        is mutable (the engine writes ``ear_side`` back into it), so repeated
        trials would overwrite each other's data.
        """
        return [replace(spec) for _ in range(repetitions) for spec in specs]

    all_trials: list[TrialSpec] = []
    for section in all_sections:
        gen = generators.get(section)
        if not gen:
            continue

        # Clean trials (run if section is in selected_sections)
        if section in selected_sections:
            all_trials.extend(_repeat(gen("clean", None)))

        # Noisy trials — one set per noise type (white, cocktail, …)
        if section in noisy_set:
            for nt in noise_types:
                all_trials.extend(_repeat(gen(nt, snr_db)))

    # Seeded RNG — a global random.shuffle() would make the trial order
    # impossible to reconstruct from the stored session record.
    random.Random(seed).shuffle(all_trials)
    return all_trials
