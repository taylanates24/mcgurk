"""McGurk Experiment — Main entry point.

Usage:
    python main.py
    python main.py --config path/to/config.yaml
"""

# ---------- Platform-specific A/V sync fix ----------
# MovieStim uses ffpyplayer which plays audio through SDL2 directly,
# bypassing PsychoPy's audioLib setting entirely.  On Windows the default
# SDL2 audio driver can introduce 50-150 ms of extra buffering latency,
# causing audible lag relative to the video frames.
#
# Setting SDL_AUDIODRIVER=wasapi (Windows 10+) selects the low-latency
# Windows Audio Session API path inside SDL2.  On Linux this env var is
# ignored (SDL2 picks PulseAudio/ALSA automatically).
import os
import platform

if platform.system() == "Windows":
    os.environ.setdefault("SDL_AUDIODRIVER", "wasapi")

# PsychoPy prefs must be set BEFORE any other psychopy imports
from psychopy import prefs

prefs.hardware["audioLib"] = ["ptb", "sounddevice", "pygame"]

import sys
from pathlib import Path

from src.config import load_config
from src.data.database import Database
from src.dialogs.login import show_login_dialog
from src.dialogs.admin_setup import show_admin_setup_dialog
from src.experiment.engine import run_experiment


def main():
    # Load config
    config_path = None
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        config_path = sys.argv[2]
    config = load_config(config_path)


    # Initialize database
    project_root = Path(__file__).resolve().parent
    db_path = project_root / config.get("database_path", "data/mcgurk.db")
    db = Database(db_path)

    try:
        # Step 1: Participant login
        participant = show_login_dialog()
        if participant is None:
            print("Deney iptal edildi (katılımcı girişi).")
            return

        participant_id = db.add_participant(participant)

        # Step 2: Admin setup (speaker + section selection)
        setup = show_admin_setup_dialog(config)
        if setup is None:
            print("Deney iptal edildi (admin ayarları).")
            return

        # Apply selected audio device before any Sound objects are created
        if setup.audio_device:
            prefs.hardware["audioDevice"] = setup.audio_device

        # Step 3: Run experiment
        run_experiment(
            setup=setup,
            participant_id=participant_id,
            config=config,
            db=db,
        )

        print("Deney başarıyla tamamlandı.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
