"""The session flow (steps.md §C Adım 8) — the real thing ``run_module`` is not.

One participant, from the pre-session checklist through login, every enabled
module in ``session.module_order`` with its instruction screen and breaks, to the
closing backup.  ESC aborts at any point and the session is closed ``aborted``.

What is here in 8b-i is the skeleton over the existing measurement modules.  The
practice block and the cross-hearing check are 8b-ii — for now their slots are
logged and skipped, so the flow is complete and 8b-ii fills the stubs.

The orchestration touches PsychoPy, but the per-participant decisions —
which speaker, which ear — are pure functions, tested in CI: a wrong ear is a
monaural test of a deaf ear, and that has to be caught without a sound card.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from ..checklist import Check, any_red, render, run_checks
from ..config.calibration import Calibration, load_calibration
from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..db.models import (
    GROUP_SSD_LEFT,
    GROUP_SSD_RIGHT,
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Participant,
)
from ..engine import AbortSession
from ..engine.av_presenter import AVPresenter
from ..engine.window import make_fixation
from ..modules import avsr as avsr_module
from ..modules import dichotic as dichotic_module
from ..modules import gin as gin_module
from ..modules import mcgurk as mcgurk_module
from ..modules import oddball as oddball_module
from ..modules import tbw as tbw_module
from ..modules.base import PlannedTrial
from ..modules.block import run_avsr, run_dichotic, run_mcgurk, run_tbw
from ..modules.response import make_keyboard
from ..modules.stream import run_gin, run_oddball
from ..stimuli import manifest as manifest_module
from . import screens
from .login import show_login_dialog
from .runtime import Hardware, open_hardware, start_session

logger = logging.getLogger(__name__)

#: name -> the module whose ``plan_trials`` builds the design.
MODULE_IMPLS = {
    "mcgurk": mcgurk_module,
    "avsr": avsr_module,
    "tbw": tbw_module,
    "oddball": oddball_module,
    "dichotic": dichotic_module,
    "gin": gin_module,
}
#: Presented as a continuous stream — no AVPresenter, no per-block break.
STREAM_MODULES = {"oddball", "gin"}
#: Carry a speaker; the design picks that speaker's recordings.  oddball's tones
#: and gin's noise have no speaker.
SPEAKER_MODULES = {"mcgurk", "avsr", "tbw", "dichotic"}

_BLOCK_RUNNERS = {
    "mcgurk": run_mcgurk,
    "avsr": run_avsr,
    "tbw": run_tbw,
    "dichotic": run_dichotic,
}
_STREAM_RUNNERS = {"oddball": run_oddball, "gin": run_gin}


# ----------------------------------------------------------- pure decisions


def select_speaker(config: ExperimentConfig, *, session_count: int, seed: int) -> int:
    """Which speaker this participant is tested with (§F.4).

    ``fixed`` pins one; ``balanced`` rotates by how many sessions have run so a
    fresh participant takes the next in turn; ``random`` draws one, seeded from
    the session seed so the choice is reproducible from the stored data.
    """
    selection = config.speaker_selection
    ids = config.stimulus_prep.speaker_ids()
    if selection.strategy == "fixed":
        assert selection.fixed_id is not None  # the schema guarantees it
        return selection.fixed_id
    if selection.strategy == "balanced":
        return ids[session_count % len(ids)]
    return random.Random(seed).choice(ids)


def good_ear_for(participant: Participant) -> str:
    """The ear GIN is presented to — the participant's better ear.

    GIN is monaural and presenting it to a deaf ear measures nothing (§C Adım
    8).  The better ear is the one with the lower PTA when both are known; when
    they are not, it is derived from the group (the SSD side is the deaf one),
    and a control with no PTA falls back to the right ear with a log line rather
    than a silent guess.
    """
    left, right = participant.pta_left_db, participant.pta_right_db
    if left is not None and right is not None and left != right:
        return "left" if left < right else "right"
    if participant.group_code == GROUP_SSD_RIGHT:  # right ear deaf
        return "left"
    if participant.group_code == GROUP_SSD_LEFT:
        return "right"
    logger.info(
        "İyi kulak PTA'dan belirlenemedi (grup %s) — varsayılan sağ. "
        "Kontrol grubunda kulak dengeleme danışman kararı (Adım 8/9).",
        participant.group_code,
    )
    return "right"


# ------------------------------------------------------------- orchestration


def _participant_id(db: Database, participant: Participant) -> int:
    existing = db.get_participant_by_code(participant.participant_code)
    if existing is not None:
        logger.info("Var olan katılımcı: %s", participant.participant_code)
        return int(existing["participant_id"])
    return db.add_participant(participant)


def _calibration(config: ExperimentConfig, project_root: Path) -> Calibration | None:
    if config.audio.calibration_file is None:
        return None
    return load_calibration(resolve_path(project_root, config.audio.calibration_file))


def _plan_module(
    name: str,
    config: ExperimentConfig,
    manifest: manifest_module.StimulusManifest,
    *,
    seed: int,
    stimuli_root: Path,
    speaker_id: int,
    good_ear: str,
    limit: int | None,
) -> list[PlannedTrial]:
    kwargs: dict[str, object] = {"seed": seed, "stimuli_root": stimuli_root}
    if name in SPEAKER_MODULES:
        kwargs["speaker_id"] = speaker_id
    if name == "gin":
        kwargs["ear"] = good_ear
    planned: list[PlannedTrial] = MODULE_IMPLS[name].plan_trials(
        config, manifest, **kwargs
    )
    if limit is not None and limit < len(planned):
        logger.warning(
            "%s: yalnızca ilk %d/%d deneme koşulacak (--limit) — veri toplama değil.",
            name,
            limit,
            len(planned),
        )
        planned = planned[:limit]
    return planned


def run_session(
    config: ExperimentConfig,
    *,
    project_root: Path,
    db_path: Path,
    limit: int | None = None,
) -> int:
    """Run one full session.  Returns 0 completed, 1 refused/failed, 2 aborted."""
    # 1. Pre-session checklist (pure part) on the console.  The hardware is
    #    verified when it is opened below (open_hardware raises on a bad backend
    #    or an unmeasurable refresh), so the console pass is the file checks.
    checks = run_checks(config, project_root, probe_hardware=False)
    print(
        render(
            checks,
            title=f"Oturum öncesi kontrol — {config.experiment.name} "
            f"({config.experiment.mode})",
        )
    )
    if config.experiment.mode == "data_collection" and any_red(checks):
        logger.error(
            "Checklist KIRMIZI — data_collection oturumu başlatılamaz. "
            "python -m mcgurk.checklist ile ayrıntıya bakın."
        )
        return 1

    # 2. Login (separate OS dialog, before the fullscreen window).
    participant = show_login_dialog()
    if participant is None:
        logger.info("Giriş iptal edildi; oturum başlatılmadı.")
        return 0

    # 3. Hardware.
    hardware = open_hardware(config)
    win = hardware.win

    db = Database(db_path)
    seed = random.SystemRandom().randrange(2**31)
    status = SESSION_COMPLETED
    session_id: int | None = None
    try:
        participant_id = _participant_id(db, participant)
        speaker_id = select_speaker(
            config, session_count=db.count_sessions(), seed=seed
        )
        good_ear = good_ear_for(participant)
        session_id = start_session(
            db,
            config,
            project_root=project_root,
            participant_id=participant_id,
            seed=seed,
            hardware=hardware,
            operator_notes=f"ui.session konuşmacı={speaker_id} iyi_kulak={good_ear}",
        )
        logger.info(
            "Oturum %d, katılımcı %s (%s), tohum %d, konuşmacı %d, iyi kulak %s",
            session_id,
            participant.participant_code,
            participant.group_code,
            seed,
            speaker_id,
            good_ear,
        )

        _run_flow(
            config,
            db=db,
            session_id=session_id,
            hardware=hardware,
            project_root=project_root,
            speaker_id=speaker_id,
            good_ear=good_ear,
            seed=seed,
            limit=limit,
            checks=checks,
        )
    except AbortSession:
        status = SESSION_ABORTED
        logger.warning("Oturum ESC ile kesildi.")
    except Exception:
        status = SESSION_ABORTED
        raise
    finally:
        win.close()
        if session_id is not None:
            db.finish_session(session_id, status)
            if config.database.backup_on_session_end:
                backup = db.backup(
                    resolve_path(project_root, config.paths.backups),
                    label=f"session{session_id}",
                )
                logger.info("Yedek: %s", backup)
        db.close()

    return 0 if status == SESSION_COMPLETED else 2


def _run_flow(
    config: ExperimentConfig,
    *,
    db: Database,
    session_id: int,
    hardware: Hardware,
    project_root: Path,
    speaker_id: int,
    good_ear: str,
    seed: int,
    limit: int | None,
    checks: list[Check],
) -> None:
    """The on-window part: confirm, welcome, modules with breaks, end."""
    win = hardware.win
    kb = make_keyboard()
    advance = config.screens.advance_key
    hint = config.screens.continue_hint

    # Operator confirms the checklist in the interface (steps.md Adım 8).
    screens.show_checklist(win, kb, checks, advance_key=advance, advance_hint=hint)
    screens.show_instruction(win, kb, config.screens.welcome, advance_key=advance, hint=hint)

    stimuli_root = resolve_path(project_root, config.paths.stimuli)
    manifest = manifest_module.load(stimuli_root)
    calibration = _calibration(config, project_root)
    fixation = make_fixation(win)
    presenter = AVPresenter(
        win,
        hardware.params,
        speaker=hardware.speaker,
        calibration=calibration,
        sample_rate=config.audio.sample_rate,
        alignment_tolerance_ms=config.stimulus_prep.burst.alignment_tolerance_ms,
        fixation=fixation,
    )

    def on_break(done: int, total: int) -> None:
        logger.info("Mola: %d/%d blok tamamlandı.", done, total)
        screens.show_break(
            win,
            kb,
            text=config.screens.break_screen,
            duration_s=config.session.break_duration_s,
            advance_key=advance,
            hint=hint,
        )

    order = config.session.module_order
    for index, name in enumerate(order):
        logger.info("Modül %d/%d: %s", index + 1, len(order), name)
        if name == "practice":
            # 8b-ii: warm-up block with congruent stimuli, no feedback.
            logger.info("Alıştırma bloğu 8b-ii'de gelecek — şimdilik atlanıyor.")
            continue

        screens.show_instruction(
            win,
            kb,
            config.screens.module_instructions[name],
            advance_key=advance,
            hint=hint,
        )
        planned = _plan_module(
            name,
            config,
            manifest,
            seed=seed,
            stimuli_root=stimuli_root,
            speaker_id=speaker_id,
            good_ear=good_ear,
            limit=limit,
        )
        if name in STREAM_MODULES:
            _STREAM_RUNNERS[name](
                config=config,
                db=db,
                session_id=session_id,
                planned=planned,
                win=win,
                kb=kb,
                params=hardware.params,
                speaker=hardware.speaker,
                calibration=calibration,
                fixation=fixation,
            )
        else:
            _BLOCK_RUNNERS[name](
                config=config,
                db=db,
                session_id=session_id,
                presenter=presenter,
                win=win,
                kb=kb,
                planned=planned,
                on_break=on_break,
            )

    if config.cross_hearing_check.enabled:
        # 8b-ii: SSD-only detection task on the deaf ear.
        logger.info("Çapraz dinleme kontrolü 8b-ii'de gelecek — şimdilik atlanıyor.")

    screens.show_instruction(
        win, kb, config.screens.session_end, advance_key=advance, hint=None
    )
