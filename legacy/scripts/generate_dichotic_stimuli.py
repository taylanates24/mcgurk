"""Pre-generate dichotic listening stimuli for all speakers.

For each speaker, takes the audio from the congruent videos (ba, da, ga) and
writes a stereo WAV with one syllable per ear for every permutation pair.

Output: assets/dichotic/{speaker_folder}/Left-{left}_Right-{right}.wav

Why WAV and not a video container:
    Dichotic trials have nothing to show.  An earlier version wrapped the
    stereo audio in a 64x64, 1 fps black mp4 purely so the engine could reuse
    its MovieStim path.  That made the trial's end time — one of the two RT
    references — depend on a one-frame-per-second video stream finishing, and
    forced a lossy AAC round trip plus an ffmpeg call per trial at run time.
    The audio is now written straight to PCM and presented without a movie.

Usage:
    python scripts/generate_dichotic_stimuli.py
    python scripts/generate_dichotic_stimuli.py --force   # overwrite existing
"""

import argparse
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
from src.experiment.stimuli import _get_ffmpeg
from src.utils.assets import discover_speakers, get_assets_dir, get_congruent_videos

# Target format.  48 kHz matches the rate the playback path uses, so nothing
# is resampled at run time.  16-bit is deliberate: these tokens are derived
# from lossy AAC sources, and writing 24-bit would imply precision the source
# material does not have.  Adım 2 re-prepares the corpus from raw recordings
# and moves to 24-bit there.
TARGET_SR = 48000


def extract_audio(video_path: Path) -> tuple[int, np.ndarray]:
    """Extract mono audio from *video_path* as a float32 array at TARGET_SR."""
    tmp = Path(tempfile.mktemp(suffix=".wav"))
    try:
        subprocess.run(
            [
                _get_ffmpeg(), "-y", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", str(TARGET_SR), "-ac", "1",
                str(tmp),
            ],
            capture_output=True,
            check=True,
        )
        sr, data = wavfile.read(tmp)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg ses çıkarma hatası ({video_path.name}): {exc.stderr.decode()}"
        ) from exc
    finally:
        tmp.unlink(missing_ok=True)
    return sr, data.astype(np.float32) / 32768.0


def create_dichotic_wav(
    left_audio: np.ndarray,
    right_audio: np.ndarray,
    sr: int,
    output_path: Path,
) -> None:
    """Write a stereo WAV carrying *left_audio* and *right_audio* per channel.

    The shorter token is zero-padded so both ears receive a stimulus of the
    same length; no other processing is applied, which keeps the channels
    fully isolated.
    """
    max_len = max(len(left_audio), len(right_audio))
    left_audio = np.pad(left_audio, (0, max_len - len(left_audio)))
    right_audio = np.pad(right_audio, (0, max_len - len(right_audio)))

    stereo = np.column_stack([left_audio, right_audio])
    peak = np.abs(stereo).max()
    if peak > 1.0:
        # Padding cannot introduce clipping, but a source token might already
        # sit at full scale; scale rather than let int16 conversion wrap.
        stereo = stereo / peak

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(output_path, sr, (stereo * 32767).astype(np.int16))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dikotik uyaran üretici")
    parser.add_argument(
        "--force", action="store_true",
        help="Var olan dosyaların üzerine yaz",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    syllables = get_syllables(config)
    assets_dir = get_assets_dir(config)
    speakers = discover_speakers(assets_dir)

    if not speakers:
        print(f"Hata: '{assets_dir}' klasöründe konuşmacı bulunamadı!")
        return 1

    dichotic_dir = assets_dir / "dichotic"
    written = 0

    for speaker in speakers:
        print(f"\n--- {speaker.display_name} ({speaker.folder_name}) ---")
        congruent = get_congruent_videos(speaker)
        syl_to_video = {v.audio_syllable: v.path for v in congruent}

        missing = [s for s in syllables if s not in syl_to_video]
        if missing:
            print(f"  UYARI: Eksik congruent video: {missing}, atlanıyor.")
            continue

        print("  Ses çıkarılıyor...", end=" ", flush=True)
        audio_cache = {}
        for syl in syllables:
            audio_cache[syl] = extract_audio(syl_to_video[syl])
        print("tamam.")

        out_dir = dichotic_dir / speaker.folder_name
        for left_syl, right_syl in permutations(syllables, 2):
            out_path = out_dir / f"Left-{left_syl}_Right-{right_syl}.wav"
            if out_path.exists() and not args.force:
                print(f"  {out_path.name} zaten var, atlanıyor (--force ile üzerine yaz).")
                continue

            sr_l, left = audio_cache[left_syl]
            _, right = audio_cache[right_syl]
            create_dichotic_wav(left, right, sr_l, out_path)
            written += 1
            print(f"  {out_path.name} oluşturuldu.")

    print(f"\nTamamlandı! {written} dosya yazıldı: {dichotic_dir}")

    legacy = sorted(dichotic_dir.glob("*/Left-*_Right-*.mp4"))
    if legacy:
        print(
            f"\nUYARI: {len(legacy)} adet eski .mp4 dikotik dosyası duruyor. "
            "Bunlar artık kullanılmıyor, silebilirsiniz:"
        )
        for path in legacy[:3]:
            print(f"  {path}")
        if len(legacy) > 3:
            print(f"  ... ve {len(legacy) - 3} tane daha")

    return 0


if __name__ == "__main__":
    sys.exit(main())
