#!/usr/bin/env python3
"""Pre-generate noisy video stimuli by overlaying a downloaded noise file.

Place your noise file at:
    assets/noise/{noise_type}.wav   (e.g. assets/noise/speech_shaped.wav)

The script reads each video, mixes the noise at the configured SNR, and
saves the result to:
    assets/noisy/{speaker}/Vis-{vis}_Aud-{aud}_{noise_type}_{snr}dB.mp4

Run once before starting experiments that use the noisy condition.

Usage:
    python scripts/generate_noisy_stimuli.py
    python scripts/generate_noisy_stimuli.py --noise-type white --snr-db 0
    python scripts/generate_noisy_stimuli.py --noise-file path/to/noise.wav
    python scripts/generate_noisy_stimuli.py --overwrite

Requires: numpy, scipy (for WAV I/O), ffmpeg
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import load_config
from src.utils.assets import discover_speakers, discover_videos, get_assets_dir

# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------

def _get_ffmpeg() -> str:
    import shutil as _shutil
    ffmpeg = _shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError("ffmpeg bulunamadı. PATH'e ekleyin veya imageio-ffmpeg kurun.")


def _ffmpeg(*args: str) -> None:
    result = subprocess.run([_get_ffmpeg(), *args], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

_SR = 48000  # target sample rate for all intermediate wavs


def _to_wav(src: Path, dst: Path) -> None:
    """Convert any audio/video file to a 48 kHz stereo PCM wav."""
    _ffmpeg(
        "-i", str(src),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(_SR),
        "-ac", "2",
        str(dst),
        "-y",
    )


def _read_wav(path: Path) -> np.ndarray:
    """Read wav and return float32 array, shape (n_samples, 2)."""
    sr, data = wavfile.read(path)
    if sr != _SR:
        raise RuntimeError(
            f"{path.name}: örnekleme hızı {sr} Hz, beklenen {_SR} Hz. "
            "Lütfen noise dosyasını 48 kHz olarak dönüştürün veya ffmpeg bunu yapacak."
        )
    data = data.astype(np.float32)
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)  # mono → stereo
    return data


def _loop_to_length(noise: np.ndarray, n: int) -> np.ndarray:
    """Tile *noise* until it has at least *n* samples, then trim."""
    repeats = n // len(noise) + 1
    return np.tile(noise, (repeats, 1))[:n]


def _mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Scale *noise* to achieve *snr_db* relative to *speech*, return int16."""
    speech_rms = np.sqrt(np.mean(speech ** 2) + 1e-10)
    noise_rms  = np.sqrt(np.mean(noise ** 2)  + 1e-10)
    # SNR = 20 * log10(rms_speech / rms_noise)  →  rms_noise = rms_speech / 10^(snr/20)
    target_noise_rms = speech_rms / (10 ** (snr_db / 20.0))
    noise_scaled = noise * (target_noise_rms / noise_rms)
    mixed = speech + noise_scaled
    # Normalise to prevent clipping, then convert to int16
    peak = np.abs(mixed).max()
    if peak > 32700:
        mixed = mixed * (32700.0 / peak)
    return mixed.astype(np.int16)


# ---------------------------------------------------------------------------
# Per-video processing
# ---------------------------------------------------------------------------

def process_video(
    video_path: Path,
    noise_data: np.ndarray,
    output_path: Path,
    snr_db: float,
    tmp_dir: Path,
) -> None:
    speech_wav  = tmp_dir / f"{video_path.stem}_speech.wav"
    mixed_wav   = tmp_dir / f"{video_path.stem}_mixed.wav"

    _to_wav(video_path, speech_wav)
    speech = _read_wav(speech_wav)

    noise = _loop_to_length(noise_data, len(speech))
    mixed = _mix_at_snr(speech, noise, snr_db)

    wavfile.write(mixed_wav, _SR, mixed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(
        "-i", str(video_path),
        "-i", str(mixed_wav),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vcodec", "copy",
        "-acodec", "aac",
        "-b:a", "192k",
        str(output_path),
        "-y",
    )


# ---------------------------------------------------------------------------
# SNR formatting — must match sections.py
# ---------------------------------------------------------------------------

def _snr_str(snr_db: float) -> str:
    return f"{int(snr_db)}dB" if snr_db == int(snr_db) else f"{snr_db}dB"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _discover_noise_files(noise_dir: Path) -> list[tuple[str, Path]]:
    """Return [(noise_type, path), ...] for all *_noise.* files in noise_dir."""
    results = []
    for f in sorted(noise_dir.iterdir()):
        if not f.is_file():
            continue
        # e.g. white_noise.mp3  →  noise_type = "white"
        if f.stem.endswith("_noise"):
            noise_type = f.stem[: -len("_noise")]
            results.append((noise_type, f))
    return results


def _process_noise_type(
    noise_type: str,
    noise_file: Path,
    snr_db: float,
    speakers: list,
    assets_dir: Path,
    overwrite: bool,
    tmp_dir: Path,
) -> tuple[int, int, int]:
    """Process all videos for one noise type. Returns (ok, skip, err)."""
    print(f"=== {noise_type} ({noise_file.name}, {snr_db} dB) ===")

    # Load and convert noise file once
    print("  Noise dosyası okunuyor...", end="", flush=True)
    noise_conv = tmp_dir / f"{noise_type}_src.wav"
    _to_wav(noise_file, noise_conv)
    noise_data = _read_wav(noise_conv)
    print(f" {len(noise_data) / _SR:.1f} sn")

    ok = skip = err = 0
    for speaker in speakers:
        videos = discover_videos(speaker)
        print(f"\n  --- {speaker.display_name} ({len(videos)} video) ---")
        for video in videos:
            out_name = (
                f"Vis-{video.visual_syllable}_Aud-{video.audio_syllable}"
                f"_{noise_type}_{_snr_str(snr_db)}.mp4"
            )
            out_path = assets_dir / "noisy" / speaker.folder_name / out_name

            if out_path.exists() and not overwrite:
                print(f"  [atlanıyor]  {out_name}")
                skip += 1
                continue

            print(f"  [işleniyor]  {out_name} ...", end="", flush=True)
            try:
                process_video(video.path, noise_data, out_path, snr_db, tmp_dir)
                print(" OK")
                ok += 1
            except Exception as exc:
                print(f" HATA: {exc}")
                err += 1

    print()
    return ok, skip, err


def main() -> None:
    parser = argparse.ArgumentParser(
        description="assets/noise/ klasöründeki tüm noise dosyalarını videolara bindir"
    )
    parser.add_argument("--config", metavar="PATH", help="Config dosyası yolu")
    parser.add_argument(
        "--snr-db", type=float, metavar="DB",
        help="SNR dB cinsinden (config'i override eder)",
    )
    parser.add_argument(
        "--noise-type", metavar="TYPE",
        help="Sadece bu noise tipini işle (varsayılan: tümü)",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Var olan çıktı dosyalarını yeniden üret",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    snr_db = args.snr_db if args.snr_db is not None else config.get("noise", {}).get("snr_db", 5)

    assets_dir = get_assets_dir(config)
    noise_dir  = assets_dir / "noise"

    if not noise_dir.is_dir():
        print(f"Hata: '{noise_dir}' klasörü bulunamadı.", file=sys.stderr)
        sys.exit(1)

    noise_files = _discover_noise_files(noise_dir)
    if not noise_files:
        print(
            f"Hata: '{noise_dir}' içinde '*_noise.*' dosyası bulunamadı.\n"
            f"  Örnek: white_noise.mp3, cocktail_noise.mp3",
            file=sys.stderr,
        )
        sys.exit(1)

    # Filter to a specific type if requested
    if args.noise_type:
        noise_files = [(t, f) for t, f in noise_files if t == args.noise_type]
        if not noise_files:
            print(f"Hata: '{args.noise_type}_noise.*' bulunamadı.", file=sys.stderr)
            sys.exit(1)

    speakers = discover_speakers(assets_dir)
    if not speakers:
        print(f"Hata: '{assets_dir}' klasöründe konuşmacı bulunamadı.", file=sys.stderr)
        sys.exit(1)

    print(f"Noise tipleri : {', '.join(t for t, _ in noise_files)}")
    print(f"SNR           : {snr_db} dB")
    print(f"Konuşmacılar  : {len(speakers)}")
    print()

    total_ok = total_skip = total_err = 0

    with tempfile.TemporaryDirectory(prefix="mcgurk_noise_") as tmp_str:
        tmp_dir = Path(tmp_str)
        for noise_type, noise_file in noise_files:
            ok, skip, err = _process_noise_type(
                noise_type, noise_file, snr_db, speakers, assets_dir, args.overwrite, tmp_dir
            )
            total_ok   += ok
            total_skip += skip
            total_err  += err

    print(f"Toplam — üretildi: {total_ok}, atlandı: {total_skip}, hata: {total_err}")
    if total_err:
        sys.exit(1)


if __name__ == "__main__":
    main()
