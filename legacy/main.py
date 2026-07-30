"""McGurk Experiment — Main entry point.

Usage:
    python main.py
    python main.py --config path/to/config.yaml
"""

import argparse
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("mcgurk")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcgurk", description="McGurk deney yürütücüsü"
    )
    parser.add_argument("--config", help="Yapılandırma dosyası yolu")
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Günlük ayrıntı düzeyi (varsayılan: INFO)",
    )
    return parser.parse_args(argv)


# Arguments are parsed before PsychoPy is imported: importing psychopy.prefs
# runs PsychoPy's own argument parser, which would otherwise swallow --help
# and print its preferences usage instead of ours.
_ARGS = parse_args()

# ---------- Platform-specific A/V sync fix ----------
# MovieStim uses ffpyplayer which plays audio through SDL2 directly,
# bypassing PsychoPy's audioLib setting entirely.  On Windows the default
# SDL2 audio driver can introduce 50-150 ms of extra buffering latency,
# causing audible lag relative to the video frames.
#
# Setting SDL_AUDIODRIVER=wasapi (Windows 10+) selects the low-latency
# Windows Audio Session API path inside SDL2.  On Linux this env var is
# ignored (SDL2 picks PulseAudio/ALSA automatically).
if platform.system() == "Windows":
    os.environ.setdefault("SDL_AUDIODRIVER", "wasapi")

# PsychoPy prefs must be set BEFORE any other psychopy imports.
from psychopy import prefs  # noqa: E402

# Only Psychtoolbox — no fallback list.  A fallback backend cannot schedule
# playback against the flip clock, and the resulting A/V offset would be
# invisible in the data.
#
# PsychoPy 2026.1 replaced prefs.hardware['audioLib'] with the class attribute
# sound.Sound.backend; the pref is kept here for older releases.  Both are set
# so the intent survives either version, and require_ptb_backend() verifies
# the outcome before any data is collected.
prefs.hardware["audioLib"] = ["ptb"]

from psychopy import sound  # noqa: E402

sound.Sound.backend = "ptb"

from src.config import load_config  # noqa: E402
from src.data.database import Database, SchemaMismatchError  # noqa: E402
from src.data.models import SESSION_COMPLETED  # noqa: E402
from src.dialogs.admin_setup import show_admin_setup_dialog  # noqa: E402
from src.dialogs.login import show_login_dialog  # noqa: E402
from src.experiment.engine import run_experiment  # noqa: E402


def setup_logging(project_root: Path, level: str = "INFO") -> Path:
    """Configure console + file logging and return the log file path."""
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"session_{datetime.now():%Y%m%dT%H%M%S}.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[file_handler, console_handler],
        force=True,
    )
    return log_path


def main(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parent
    log_path = setup_logging(project_root, args.log_level)
    logger.info("Günlük dosyası: %s", log_path)

    config = load_config(args.config)

    db_path = project_root / config.get("database_path", "data/mcgurk.db")
    try:
        db = Database(db_path)
    except SchemaMismatchError as exc:
        logger.error("%s", exc)
        return 1

    try:
        # Step 1: Participant entry (anonymous code only)
        participant = show_login_dialog()
        if participant is None:
            logger.info("Deney iptal edildi (katılımcı girişi).")
            return 0

        participant_id = db.add_participant(participant)
        logger.info(
            "Katılımcı kaydedildi: kod=%s, id=%d, grup=%s",
            participant.participant_code, participant_id, participant.group,
        )

        # Step 2: Admin setup (speaker + section selection)
        setup = show_admin_setup_dialog(config)
        if setup is None:
            logger.info("Deney iptal edildi (admin ayarları).")
            return 0

        # Apply selected audio device before any Sound objects are created
        if setup.audio_device:
            prefs.hardware["audioDevice"] = setup.audio_device
            logger.info("Ses aygıtı: %s", setup.audio_device)

        # Step 3: Run experiment
        status = run_experiment(
            setup=setup,
            participant_id=participant_id,
            config=config,
            db=db,
        )

        # An interrupted session returns normally, so the status has to be
        # checked — reporting success here unconditionally would tell the
        # operator the run was fine when it was cut short.
        if status == SESSION_COMPLETED:
            logger.info("Deney başarıyla tamamlandı.")
            return 0

        logger.warning(
            "Deney tamamlanmadı (durum: %s). Kaydedilen denemeler korundu.",
            status,
        )
        return 1

    except (RuntimeError, FileNotFoundError) as exc:
        # Configuration / asset / backend problems: report clearly instead of
        # dumping a traceback at the operator.
        logger.error("%s", exc)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(_ARGS))
