"""Run one assessment module on its own (steps.md §C Adım 4–5).

This is a **development harness**, not the session flow.  Adım 8 owns the real
thing — participant login, the pre-session checklist, instructions, practice,
module ordering, breaks and resumption.  What this tool does is the minimum a
module needs in order to be exercised and reviewed before that exists:

    python tools/run_module.py --module mcgurk --dry-run
        No PsychoPy, no hardware.  Builds the trial list from the config and the
        manifest, checks every file it refers to, prints the design.  This is
        how the design is inspected before anyone sits in front of it.

    python tools/run_module.py --module mcgurk --limit 8
        Presents eight real trials, writes them to the database, prints what was
        recorded.  ``--limit`` keeps a check from costing a full 14-minute run.

    python tools/run_module.py --module mcgurk
        The whole module.

Exit code 0 = the run finished; 1 = a problem the operator has to act on;
2 = the operator aborted with ESC.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.calibration import Calibration, load_calibration  # noqa: E402
from mcgurk.config.loader import (  # noqa: E402
    ConfigError,
    load_config,
    resolve_path,
    summarise_design,
)
from mcgurk.config.schema import ExperimentConfig, ResponseUIConfig  # noqa: E402
from mcgurk.db.database import Database, DatabaseError  # noqa: E402
from mcgurk.db.models import (  # noqa: E402
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Participant,
    SessionRecord,
)
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.modules import avsr as avsr_module  # noqa: E402
from mcgurk.modules import mcgurk as mcgurk_module  # noqa: E402
from mcgurk.modules.base import ModuleError, PlannedTrial  # noqa: E402
from mcgurk.provenance import collect as collect_provenance  # noqa: E402
from mcgurk.stimuli import manifest as manifest_module  # noqa: E402
from mcgurk.stimuli.manifest import ManifestError  # noqa: E402

#: Modules this harness can run, and where their design comes from.  Adım 6–7c
#: add their own entries here; nothing else in the tool is module-specific.
MODULES = {
    "mcgurk": mcgurk_module,
    "avsr": avsr_module,
}

#: Development participant.  An anonymous code and nothing else (§A.6); the age
#: has to satisfy the database's 18–60 CHECK.
DEV_CODE = "DEV01"
DEV_GROUP = "CTRL"
DEV_AGE = 30
DEV_SEX = "UNDISCLOSED"


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * max(40, len(title)))


# --------------------------------------------------------------------- design


def build_plan(
    config: ExperimentConfig, module: str, seed: int, *, speaker_id: int | None = None
) -> list[PlannedTrial]:
    stimuli_root = resolve_path(_PROJECT_ROOT, config.paths.stimuli)
    manifest = manifest_module.load(stimuli_root)
    implementation = MODULES.get(module)
    if implementation is None:  # pragma: no cover - argparse restricts this
        raise ModuleError(f"Bu araç bu modülü henüz koşmuyor: {module}")
    planned: list[PlannedTrial] = implementation.plan_trials(
        config, manifest, seed=seed, stimuli_root=stimuli_root, speaker_id=speaker_id
    )
    return planned


def dry_run(config: ExperimentConfig, module: str, planned: list[PlannedTrial], seed: int) -> int:
    """Print the design and verify every file it refers to exists."""
    _rule(f"Tasarım — {module} (tohum {seed})")
    expected = config.trial_counts()[module]
    print(f"  Deneme sayısı        : {len(planned)}")
    print(f"  Config'in beklentisi : {expected}")
    if len(planned) != expected:
        print("  SORUN: üretilen deneme sayısı config'in hesabıyla uyuşmuyor.")
        return 1

    _rule("Hücreler")
    print(f"  {'Etiket':<20}{'Uyaran':<22}{'Kulak':<8}{'Gürültü':<10}{'n':>4}")
    for (label, tokens, ear, noise), count in sorted(
        MODULES[module].cell_counts(planned).items()
    ):
        print(f"  {label:<20}{tokens:<22}{ear:<8}{noise:<10}{count:>4}")

    _rule("İlk 12 deneme")
    print(f"  {'#':>3}  {'Etiket':<20}{'Kulak':<8}{'Gürültü':<10}{'Örnek':<7}Dosya")
    for index, item in enumerate(planned[:12]):
        trial = item.trial
        noise = "sessiz" if trial.snr_db is None else f"{trial.snr_db:g} dB"
        if trial.presentation_mode == "V":
            noise = "—"
        instance = trial.design_extra.get("noise_instance")
        # V-only carries a video and no audio; A-only the other way round.
        media = item.spec.audio_path or item.spec.video_path
        assert media is not None
        print(
            f"  {index:>3}  {trial.condition_label:<20}{str(trial.ear or '—'):<8}"
            f"{noise:<10}{str(instance or '—'):<7}{media.name}"
        )

    _rule("Dosya kontrolü")
    missing: list[Path] = []
    for item in planned:
        for path in (item.spec.video_path, item.spec.audio_path):
            if path is not None and not path.is_file():
                missing.append(path)
    if missing:
        print(f"  {len(missing)} dosya eksik. İlk beş:")
        for path in sorted(set(missing))[:5]:
            print(f"    {path}")
        print("  python tools/prepare_stimuli.py")
        return 1
    unique = {
        path
        for item in planned
        for path in (item.spec.video_path, item.spec.audio_path)
        if path is not None
    }
    print(f"  {len(unique)} ayrı dosya, tamamı yerinde.")

    _rule("Yanıt seti")
    module_config = config.modules.by_name()[module]
    assert isinstance(module_config, ResponseUIConfig)
    for key, label in zip(module_config.response_keys, module_config.response_set, strict=True):
        marker = ""
        if (
            module_config.free_text_response is not None
            and label.casefold() == module_config.free_text_response.casefold()
        ):
            marker = "  <-- serbest metin"
        print(f"  [{key}] {label}{marker}")
    return 0


# ------------------------------------------------------------------- live run


def _calibration(config: ExperimentConfig) -> Calibration | None:
    if config.audio.calibration_file is None:
        return None
    return load_calibration(resolve_path(_PROJECT_ROOT, config.audio.calibration_file))


def _participant_id(db: Database, code: str, notes: str) -> int:
    existing = db.get_participant_by_code(code)
    if existing is not None:
        return int(existing["participant_id"])
    return db.add_participant(
        Participant(
            participant_code=code,
            group_code=DEV_GROUP,
            age=DEV_AGE,
            sex=DEV_SEX,
            notes=notes,
        )
    )


def live_run(
    config: ExperimentConfig,
    module: str,
    planned: list[PlannedTrial],
    seed: int,
    *,
    db_path: Path,
    participant_code: str,
) -> int:
    """Open the hardware, run the block(s), write the session to the database."""
    from mcgurk.engine import AbortSession
    from mcgurk.engine.audio import open_speaker, require_ptb_backend
    from mcgurk.engine.av_presenter import AVPresenter
    from mcgurk.engine.psychopy_prefs import configure_psychopy
    from mcgurk.engine.scheduling import TimingParams
    from mcgurk.engine.window import (
        check_refresh_hz,
        make_fixation,
        measure_refresh_hz,
        open_window,
    )
    from mcgurk.modules.block import run_avsr, run_mcgurk, summarise
    from mcgurk.modules.response import make_keyboard

    runners = {"mcgurk": run_mcgurk, "avsr": run_avsr}

    configure_psychopy(audio_device=config.audio.device)
    require_ptb_backend()
    speaker = open_speaker(
        device_name=config.audio.device,
        latency_class=config.timing.audio_latency_mode,
        sample_rate=config.audio.sample_rate,
    )

    db = Database(db_path)
    win = open_window(config.display)
    status = SESSION_COMPLETED
    exit_code = 0
    session_id: int | None = None
    try:
        refresh_hz = measure_refresh_hz(win)
        check_refresh_hz(refresh_hz, config.display)
        params = TimingParams(
            frame_period_s=1.0 / refresh_hz,
            lead_frames=config.timing.lead_frames,
            system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
            dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
        )

        provenance = collect_provenance(_PROJECT_ROOT)
        participant_id = _participant_id(
            db, participant_code, "tools/run_module.py geliştirme koşusu"
        )
        session_id = db.start_session(
            SessionRecord(
                participant_id=participant_id,
                seed=seed,
                config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
                config_mode=config.experiment.mode,
                app_version=provenance.app_version,
                git_commit=provenance.git_commit,
                psychopy_version=provenance.psychopy_version,
                python_version=provenance.python_version,
                os_name=provenance.os_name,
                audio_backend="ptb",
                audio_device=str(getattr(speaker, "name", "") or ""),
                measured_refresh_hz=refresh_hz,
                system_av_offset_ms=config.timing.system_av_offset_ms,
                operator_notes=f"tools/run_module.py --module {module}",
            )
        )
        print(f"  Oturum {session_id}, katılımcı {participant_code}, tohum {seed}")

        presenter = AVPresenter(
            win,
            params,
            speaker=speaker,
            calibration=_calibration(config),
            sample_rate=config.audio.sample_rate,
            alignment_tolerance_ms=config.stimulus_prep.burst.alignment_tolerance_ms,
            fixation=make_fixation(win),
        )
        outcomes = runners[module](
            config=config,
            db=db,
            session_id=session_id,
            presenter=presenter,
            win=win,
            kb=make_keyboard(),
            planned=planned,
        )
    except AbortSession:
        status = SESSION_ABORTED
        exit_code = 2
        print("\n  Oturum ESC ile kesildi.")
        outcomes = []
    except Exception:
        status = SESSION_ABORTED
        raise
    finally:
        win.close()
        if session_id is not None:
            db.finish_session(session_id, status)
            if config.database.backup_on_session_end:
                backup = db.backup(
                    resolve_path(_PROJECT_ROOT, config.paths.backups),
                    label=f"session{session_id}",
                )
                print(f"  Yedek: {backup}")
        db.close()

    if outcomes:
        _rule("Koşu özeti")
        print(summarise(outcomes))
        if module == "avsr":
            print()
            print(avsr_module.summarise_measures(_flat_rows(db_path, session_id)))
    return exit_code


def _flat_rows(db_path: Path, session_id: int | None) -> list[Any]:
    """Read the session back for the module's own measures.

    After the run, not during it: the measures are a report on what was
    collected, and computing them from the same objects that wrote the rows
    would not notice a row that never arrived.
    """
    if session_id is None:
        return []
    db = Database(db_path)
    try:
        return list(db.flat_rows(session_id))
    finally:
        db.close()


# ------------------------------------------------------------------ plumbing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tek bir modülü koştur (geliştirme aracı, steps.md §C Adım 4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--module", choices=sorted(MODULES), default="mcgurk")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None, help="config'teki veritabanını ez")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="oturum tohumu (verilmezse üretilir ve yazdırılır)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="yalnızca ilk N denemeyi koştur"
    )
    parser.add_argument("--speaker-id", type=int, default=None, help="konuşmacıyı ez")
    parser.add_argument("--participant", default=DEV_CODE, help="anonim katılımcı kodu")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="donanım açmadan tasarımı bas ve dosyaları doğrula",
    )
    parser.add_argument("--device", default=None, help="bu koşu için audio.device'ı ez")
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

    print(summarise_design(config))
    try:
        planned = build_plan(config, args.module, seed, speaker_id=args.speaker_id)
    except (ManifestError, ModuleError, NotImplementedError) as exc:
        print(f"\nHATA: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        return dry_run(config, args.module, planned, seed)

    full_length = len(planned)
    if args.limit is not None:
        planned = planned[: args.limit]
        print(
            f"\n  UYARI: yalnızca ilk {len(planned)}/{full_length} deneme "
            "koşulacak (--limit). Bu bir veri toplama oturumu değildir."
        )

    _rule(f"Koşu — {args.module}")
    db_path = args.db or resolve_path(_PROJECT_ROOT, config.database.path)
    try:
        return live_run(
            config,
            args.module,
            planned,
            seed,
            db_path=db_path,
            participant_code=args.participant,
        )
    except DatabaseError as exc:
        print(f"\nHATA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
