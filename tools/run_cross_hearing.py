"""Run *only* the cross-hearing check, to confirm the tone lateralises correctly.

This is a development / manual-test harness for Adım 8b-ii: in a full session the
cross-hearing check runs last, after every module, which makes it awkward to
verify on its own that the tone reaches the intended (deaf) ear.  Here it runs by
itself.

    python tools/run_cross_hearing.py --ear right

``--ear`` is the DEAF ear — the SSD side.  The tone is routed there and the other
channel is exactly zero (``engine.audio.lateralise``); half the trials are catch
trials with no sound at all.  Put the headphones on the right way round, press
SPACE when you hear the tone, and check the sound comes from the ear you passed.
Run it once with ``--ear right`` and once with ``--ear left`` to confirm the side
follows the flag.

Exit code 0 = finished; 1 = a problem to act on; 2 = aborted with ESC.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.calibration import Calibration, load_calibration  # noqa: E402
from mcgurk.config.loader import (  # noqa: E402
    ConfigError,
    load_config,
    resolve_path,
)
from mcgurk.config.schema import ExperimentConfig  # noqa: E402
from mcgurk.db.database import Database, DatabaseError  # noqa: E402
from mcgurk.db.models import (  # noqa: E402
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Participant,
)
from mcgurk.engine import AbortSession, EngineError  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.modules import cross_hearing as cross_hearing_module  # noqa: E402
from mcgurk.modules.base import ModuleError  # noqa: E402
from mcgurk.stimuli import manifest as manifest_module  # noqa: E402
from mcgurk.stimuli.manifest import ManifestError  # noqa: E402

DEV_CODE = "DEV01"


def _calibration(config: ExperimentConfig) -> Calibration | None:
    if config.audio.calibration_file is None:
        return None
    return load_calibration(resolve_path(_PROJECT_ROOT, config.audio.calibration_file))


def _participant_id(db: Database, code: str) -> int:
    existing = db.get_participant_by_code(code)
    if existing is not None:
        return int(existing["participant_id"])
    return db.add_participant(
        Participant(
            participant_code=code,
            group_code="CTRL",
            age=30,
            sex="UNDISCLOSED",
            notes="tools/run_cross_hearing.py geliştirme koşusu",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python tools/run_cross_hearing.py",
        description="Yalnızca çapraz dinleme kontrolünü koştur (Adım 8b-ii)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ear",
        choices=("left", "right"),
        required=True,
        help="SAĞIR kulak — ton bu kulağa yönlendirilir, diğer kanal sessiz",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None, help="config'teki veritabanını ez")
    parser.add_argument("--seed", type=int, default=None, help="tohum (verilmezse üretilir)")
    parser.add_argument("--limit", type=int, default=None, help="yalnızca ilk N deneme")
    parser.add_argument("--device", default=None, help="bu koşu için audio.device'ı ez")
    parser.add_argument("--participant", default=DEV_CODE)
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT)
    except ConfigError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    setup_logging(
        resolve_path(_PROJECT_ROOT, config.paths.logs),
        console_level=config.logging.console_level,
        file_level=config.logging.file_level,
    )
    if args.device is not None:
        config.audio.device = args.device
        print(f"Aygıt bu koşu için ezildi: {args.device!r} (config değişmedi)")

    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**31)
    stimuli_root = resolve_path(_PROJECT_ROOT, config.paths.stimuli)

    try:
        manifest = manifest_module.load(stimuli_root)
        planned = cross_hearing_module.plan_trials(
            config, manifest, seed=seed, stimuli_root=stimuli_root, deaf_ear=args.ear
        )
    except (ManifestError, ModuleError) as exc:
        print(f"\nHATA: {exc}", file=sys.stderr)
        return 1

    if args.limit is not None:
        planned = planned[: args.limit]
    print(
        f"\nÇapraz dinleme: {len(planned)} deneme, SAĞIR kulak = {args.ear}, "
        f"tohum {seed}"
    )
    print(f"  Ton {config.cross_hearing_check.tone_hz:g} Hz, {args.ear} kanala "
          "yönlendirilir; catch denemeleri tümüyle sessizdir.")
    print("  Ton duyduğunuzda BOŞLUK'a basın. ESC ile çıkabilirsiniz.\n")

    from mcgurk.engine.window import make_fixation
    from mcgurk.modules.response import make_keyboard
    from mcgurk.ui.runtime import open_hardware, start_session

    hardware = open_hardware(config)
    db = Database(args.db or resolve_path(_PROJECT_ROOT, config.database.path))
    status = SESSION_COMPLETED
    exit_code = 0
    session_id: int | None = None
    try:
        participant_id = _participant_id(db, args.participant)
        session_id = start_session(
            db,
            config,
            project_root=_PROJECT_ROOT,
            participant_id=participant_id,
            seed=seed,
            hardware=hardware,
            operator_notes=f"tools/run_cross_hearing.py --ear {args.ear}",
        )
        outcome = cross_hearing_module.run_cross_hearing(
            config=config,
            db=db,
            session_id=session_id,
            planned=planned,
            win=hardware.win,
            kb=make_keyboard(),
            params=hardware.params,
            speaker=hardware.speaker,
            calibration=_calibration(config),
            fixation=make_fixation(hardware.win),
        )
        print()
        print(cross_hearing_module.summarise(outcome))
    except AbortSession:
        status = SESSION_ABORTED
        exit_code = 2
        print("\n  Koşu ESC ile kesildi.")
    except EngineError as exc:
        status = SESSION_ABORTED
        print(f"\nHATA: {exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        status = SESSION_ABORTED
        raise
    finally:
        hardware.win.close()
        if session_id is not None:
            db.finish_session(session_id, status)
            if config.database.backup_on_session_end:
                db.backup(
                    resolve_path(_PROJECT_ROOT, config.paths.backups),
                    label=f"session{session_id}",
                )
        db.close()

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DatabaseError as exc:
        print(f"\nHATA: {exc}", file=sys.stderr)
        sys.exit(1)
