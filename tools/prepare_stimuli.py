"""Prepare the stimulus set from the raw recordings (steps.md §C Adım 2).

Reads ``config/experiment.yaml``, produces silent constant-frame-rate video,
burst-aligned and level-normalised audio, speech-shaped noise, the noisy
variants, the dichotic pairs and the GIN segments under ``paths.stimuli``,
and writes ``manifest.json`` describing all of it.

    python tools/prepare_stimuli.py
    python tools/prepare_stimuli.py --force        # rebuild an existing set
    python tools/prepare_stimuli.py --config path/to/experiment.yaml

Exit code 0 = the set is ready, 1 = nothing usable was produced.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.loader import ConfigError, load_config, resolve_path  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.stimuli import StimulusError  # noqa: E402
from mcgurk.stimuli.prepare import prepare  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prepare_stimuli",
        description="Ham kayıtlardan uyaran setini hazırla",
    )
    parser.add_argument("--config", type=Path, default=None, help="Config dosyası")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Mevcut manifest'in üzerine yaz (uyaran seti yeniden üretilir)",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT)
    except ConfigError as exc:
        print(f"KIRMIZI  {exc}", file=sys.stderr)
        return 1

    setup_logging(
        resolve_path(_PROJECT_ROOT, config.paths.logs),
        console_level=args.log_level,
        file_level=config.logging.file_level,
    )

    try:
        result = prepare(config, _PROJECT_ROOT, force=args.force)
    except StimulusError as exc:
        # Every tolerance violation lands here.  Preparing "most of" a stimulus
        # set is not a partial success: the missing part is invisible later.
        print(f"\nKIRMIZI  Uyaran hazırlığı başarısız:\n{exc}", file=sys.stderr)
        return 1

    print()
    print(f"Video           : {len(result.videos)}")
    print(f"Ses (hizalı)    : {len(result.tokens)}")
    print(f"Ses (gürültülü) : {len(result.noisy_tokens)}")
    print(f"Dikotik         : {len(result.dichotic)}")
    print(f"GIN segmenti    : {len(result.gin_segments)}")
    if result.tones:
        frequencies = ", ".join(f"{entry.frequency_hz:g}" for entry in result.tones)
        print(f"Oddball tonu    : {len(result.tones)} ({frequencies} Hz)")
    if result.noise is not None:
        print(
            f"SSN             : 1 (en büyük LTAS sapması "
            f"{result.noise.max_ltas_deviation_db:.2f} dB)"
        )
    print()
    print("SONUÇ: UYARAN SETİ HAZIR")
    print("Doğrulamak için: python tools/verify_stimuli.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
