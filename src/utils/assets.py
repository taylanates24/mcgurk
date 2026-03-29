"""Asset discovery: auto-detect speakers and parse video filenames."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Pattern for speaker folder names: {gender}_speaker_{number}
_SPEAKER_DIR_PATTERN = re.compile(r"^(female|male)_speaker_(\d+)$")

# Pattern for video filenames: Vis-{visual}_Aud-{audio}.mp4
_VIDEO_FILENAME_PATTERN = re.compile(
    r"^Vis-([a-z]+)_Aud-([a-z]+)\.mp4$", re.IGNORECASE
)


@dataclass
class Speaker:
    """Represents a discovered speaker."""

    folder_name: str
    gender: str
    number: int
    path: Path

    @property
    def display_name(self) -> str:
        gender_tr = "Kadın" if self.gender == "female" else "Erkek"
        return f"{gender_tr} Konuşmacı {self.number}"


@dataclass
class VideoStimulus:
    """Represents a single video stimulus file."""

    path: Path
    visual_syllable: str
    audio_syllable: str
    speaker: Speaker

    @property
    def is_congruent(self) -> bool:
        return self.visual_syllable == self.audio_syllable

    @property
    def is_incongruent(self) -> bool:
        return self.visual_syllable != self.audio_syllable


def get_assets_dir(config: dict[str, Any]) -> Path:
    """Return the assets directory path from config."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / config.get("assets_dir", "assets")


def discover_speakers(assets_dir: Path) -> list[Speaker]:
    """Scan assets directory and return all valid speaker folders.

    Looks for directories matching the pattern {gender}_speaker_{n}.
    """
    speakers = []
    if not assets_dir.is_dir():
        return speakers

    for entry in sorted(assets_dir.iterdir()):
        if not entry.is_dir():
            continue
        match = _SPEAKER_DIR_PATTERN.match(entry.name)
        if match:
            speakers.append(
                Speaker(
                    folder_name=entry.name,
                    gender=match.group(1),
                    number=int(match.group(2)),
                    path=entry,
                )
            )
    return speakers


def discover_videos(speaker: Speaker) -> list[VideoStimulus]:
    """Scan a speaker's folder and return all valid video stimuli."""
    videos = []
    for f in sorted(speaker.path.iterdir()):
        if not f.is_file():
            continue
        match = _VIDEO_FILENAME_PATTERN.match(f.name)
        if match:
            videos.append(
                VideoStimulus(
                    path=f,
                    visual_syllable=match.group(1).lower(),
                    audio_syllable=match.group(2).lower(),
                    speaker=speaker,
                )
            )
    return videos


def get_congruent_videos(speaker: Speaker) -> list[VideoStimulus]:
    """Return only congruent (visual == audio) videos for a speaker."""
    return [v for v in discover_videos(speaker) if v.is_congruent]


def get_incongruent_videos(speaker: Speaker) -> list[VideoStimulus]:
    """Return only incongruent (visual != audio) videos for a speaker."""
    return [v for v in discover_videos(speaker) if v.is_incongruent]


def get_speaker_thumbnail_path(speaker: Speaker) -> Path | None:
    """Return path to a congruent video to use for thumbnail extraction.

    Uses the first congruent video found (e.g., Vis-ba_Aud-ba.mp4).
    """
    congruent = get_congruent_videos(speaker)
    return congruent[0].path if congruent else None
