"""Section definitions and trial generation for each experiment section."""

import random
from itertools import permutations
from typing import Any

from ..utils.assets import (
    Speaker,
    VideoStimulus,
    discover_videos,
    get_congruent_videos,
    get_incongruent_videos,
)
from .trial import TrialSpec


def generate_mcgurk_trials(
    speaker: Speaker, noise_condition: str = "clean", snr_db: float | None = None
) -> list[TrialSpec]:
    """Generate McGurk (incongruent) trials for a speaker.

    Uses all incongruent videos where visual != audio.
    """
    videos = get_incongruent_videos(speaker)
    return [
        TrialSpec(
            section_type="mcgurk",
            video_path=v.path,
            audio_path=None,  # audio embedded in video
            visual_syllable=v.visual_syllable,
            audio_syllable=v.audio_syllable,
            noise_condition=noise_condition,
            snr_db=snr_db,
            correct_answer=v.audio_syllable,
            speaker_name=speaker.folder_name,
        )
        for v in videos
    ]


def generate_av_congruent_trials(
    speaker: Speaker, noise_condition: str = "clean", snr_db: float | None = None
) -> list[TrialSpec]:
    """Generate AV congruent trials (visual == audio)."""
    videos = get_congruent_videos(speaker)
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
        for v in videos
    ]


def generate_audio_only_trials(
    speaker: Speaker,
    syllables: list[str],
    noise_condition: str = "clean",
    snr_db: float | None = None,
) -> list[TrialSpec]:
    """Generate audio-only trials. Uses congruent videos for audio extraction."""
    videos = get_congruent_videos(speaker)
    video_map = {v.audio_syllable: v for v in videos}
    trials = []
    for syl in syllables:
        v = video_map.get(syl)
        if v:
            trials.append(
                TrialSpec(
                    section_type="audio_only",
                    video_path=None,
                    audio_path=v.path,  # will play audio from this video
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
    noise_enabled: bool = False,
) -> list[TrialSpec]:
    """Build the complete trial list for an experiment session.

    Generates trials for all selected sections, optionally adds noisy variants,
    applies repetitions, and randomizes order.
    """
    syllables = config.get("syllables", ["ba", "da", "ga"])
    repetitions = config.get("trial_repetitions", 1)
    noise_type = config.get("noise", {}).get("type", "speech_shaped")
    snr_db = config.get("noise", {}).get("snr_db", 5)

    generators = {
        "mcgurk": lambda nc, snr: generate_mcgurk_trials(speaker, nc, snr),
        "av_congruent": lambda nc, snr: generate_av_congruent_trials(speaker, nc, snr),
        "audio_only": lambda nc, snr: generate_audio_only_trials(speaker, syllables, nc, snr),
        "visual_only": lambda nc, snr: generate_visual_only_trials(speaker, syllables),
        "dichotic": lambda nc, snr: generate_dichotic_trials(syllables, speaker),
    }

    all_trials = []
    for section in selected_sections:
        gen = generators.get(section)
        if not gen:
            continue

        # Clean trials
        clean_trials = gen("clean", None)
        all_trials.extend(clean_trials * repetitions)

        # Noisy trials (if enabled and section supports it)
        if noise_enabled and section not in ("visual_only", "dichotic"):
            noisy_trials = gen(noise_type, snr_db)
            all_trials.extend(noisy_trials * repetitions)

    random.shuffle(all_trials)
    return all_trials
