"""Pre-generate dichotic listening stimuli for all speakers.

For each speaker, takes audio from congruent videos (ba, da, ga) and creates
stereo mp4 files with one syllable per ear for every permutation pair.

Output: assets/dichotic/{speaker_folder}/Left-{left}_Right-{right}.mp4

Usage:
    python scripts/generate_dichotic_stimuli.py
"""

import subprocess
import sys
import tempfile
from itertools import permutations
from pathlib import Path

import numpy as np
from scipy.io import wavfile

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import get_syllables, load_config
from src.utils.assets import discover_speakers, get_assets_dir, get_congruent_videos


def extract_audio(video_path: Path) -> tuple[int, np.ndarray]:
    """Extract mono audio from video as float32 numpy array."""
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            tmp,
        ],
        capture_output=True,
        check=True,
    )
    sr, data = wavfile.read(tmp)
    Path(tmp).unlink(missing_ok=True)
    return sr, data.astype(np.float32) / 32768.0


def create_dichotic_mp4(
    left_audio: np.ndarray,
    right_audio: np.ndarray,
    sr: int,
    output_path: Path,
):
    """Create an mp4 with black video and stereo audio (left/right channels)."""
    # Pad shorter to match
    max_len = max(len(left_audio), len(right_audio))
    left_audio = np.pad(left_audio, (0, max_len - len(left_audio)))
    right_audio = np.pad(right_audio, (0, max_len - len(right_audio)))

    stereo = np.column_stack([left_audio, right_audio])
    stereo_int16 = (stereo * 32767).astype(np.int16)

    tmp_wav = tempfile.mktemp(suffix=".wav")
    wavfile.write(tmp_wav, sr, stereo_int16)

    duration = max_len / sr
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={duration:.3f}:r=1",
            "-i", tmp_wav,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-shortest", str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    Path(tmp_wav).unlink(missing_ok=True)


def main():
    config = load_config()
    syllables = get_syllables(config)
    assets_dir = get_assets_dir(config)
    speakers = discover_speakers(assets_dir)

    if not speakers:
        print(f"Hata: '{assets_dir}' klasöründe konuşmacı bulunamadı!")
        return

    dichotic_dir = assets_dir / "dichotic"

    for speaker in speakers:
        print(f"\n--- {speaker.display_name} ({speaker.folder_name}) ---")
        congruent = get_congruent_videos(speaker)
        syl_to_video = {v.audio_syllable: v.path for v in congruent}

        # Check all syllables have congruent videos
        missing = [s for s in syllables if s not in syl_to_video]
        if missing:
            print(f"  UYARI: Eksik congruent video: {missing}, atlanıyor.")
            continue

        # Extract audio for each syllable once
        print("  Ses çıkarılıyor...", end=" ", flush=True)
        audio_cache = {}
        for syl in syllables:
            sr, audio = extract_audio(syl_to_video[syl])
            audio_cache[syl] = (sr, audio)
        print("tamam.")

        # Generate all permutation pairs
        out_dir = dichotic_dir / speaker.folder_name
        pairs = list(permutations(syllables, 2))
        for left_syl, right_syl in pairs:
            out_path = out_dir / f"Left-{left_syl}_Right-{right_syl}.mp4"
            if out_path.exists():
                print(f"  {out_path.name} zaten var, atlanıyor.")
                continue

            sr_l, left = audio_cache[left_syl]
            sr_r, right = audio_cache[right_syl]
            create_dichotic_mp4(left, right, sr_l, out_path)
            print(f"  {out_path.name} oluşturuldu.")

    print(f"\nTamamlandı! Dikotik stimuluslar: {dichotic_dir}")


if __name__ == "__main__":
    main()
