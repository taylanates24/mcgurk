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
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from ..checklist import Check, any_red, render, run_checks
from ..config.calibration import Calibration, load_calibration
from ..config.loader import config_from_snapshot, resolve_path
from ..config.schema import ExperimentConfig
from ..config.selection import SPEAKER_MODULES, SessionSelection, select_speaker
from ..config.selection import apply as apply_selection
from ..db.database import Database
from ..db.models import (
    GROUP_SSD_LEFT,
    GROUP_SSD_RIGHT,
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Participant,
)
from ..engine import AbortSession, set_abort_confirmer
from ..engine.av_presenter import AVPresenter
from ..engine.window import make_fixation
from ..modules import avsr as avsr_module
from ..modules import cross_hearing as cross_hearing_module
from ..modules import dichotic as dichotic_module
from ..modules import gin as gin_module
from ..modules import mcgurk as mcgurk_module
from ..modules import oddball as oddball_module
from ..modules import practice as practice_module
from ..modules import tbw as tbw_module
from ..modules.base import PlannedTrial
from ..modules.block import run_avsr, run_dichotic, run_mcgurk, run_practice, run_tbw
from ..modules.response import make_keyboard
from ..modules.stream import run_gin, run_oddball
from ..stimuli import manifest as manifest_module
from . import screens
from .login import ask_resume_or_new, show_login_dialog
from .runtime import Hardware, open_hardware, start_session

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

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

_BLOCK_RUNNERS = {
    "mcgurk": run_mcgurk,
    "avsr": run_avsr,
    "tbw": run_tbw,
    "dichotic": run_dichotic,
}
_STREAM_RUNNERS = {"oddball": run_oddball, "gin": run_gin}


# ----------------------------------------------------------- pure decisions

# ``select_speaker`` moved to ``config.selection`` in Adım 12b, where the rest of
# the per-session choice lives; it is re-exported here because it was this
# module's function for four steps and callers still import it from here.


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


def deaf_ear_for(participant: Participant) -> str | None:
    """The SSD (deaf) ear the cross-hearing check is presented to, or None.

    Defined by the group, which is what "single-sided deafness on the right"
    means; a control has no deaf ear, so the check is skipped for them.
    """
    if participant.group_code == GROUP_SSD_RIGHT:
        return "right"
    if participant.group_code == GROUP_SSD_LEFT:
        return "left"
    return None


# --------------------------------------------------------------- resume (8c-i)


def remaining_plan(
    full: list[_T], completed_count: int, *, is_stream: bool
) -> list[_T]:
    """What is left to run of a module on resume.

    A fully-recorded module returns nothing.  A stream (oddball/GIN, and the
    cross-hearing check) that is not complete is re-run in full — a continuous
    stream cannot be resumed from its middle, so its aborted partial block is
    left in the database and superseded.  A forced-choice module resumes after
    the trials already in its completed blocks; the seed makes the order
    identical, so those first *completed_count* trials are exactly the ones
    already recorded.
    """
    if completed_count >= len(full):
        return []
    if is_stream:
        return list(full)
    return list(full[completed_count:])


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
    offer_resume: bool = True,
    selection: SessionSelection | None = None,
) -> int:
    """Run one full session.  Returns 0 completed, 1 refused/failed, 2 aborted.

    If *offer_resume* and the participant has a half-finished session, the
    operator is asked to continue it (Adım 8c-i): the same session id, seed and
    stored config snapshot are reused and the already-completed modules are
    skipped.

    *selection* is the operator's choice of speaker and modules (Adım 12).  It
    is applied to the config **before** the session is started, so the design it
    produces is what goes into ``sessions.config_snapshot`` — resume, analysis
    and QC then read the subset from the same place they read everything else.
    A resumed session ignores it: that session already has a design, and
    offering a different one would contradict the snapshot it continues under.
    """
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

    db = Database(db_path)
    status = SESSION_COMPLETED
    session_id: int | None = None
    win: Any = None
    active_config = config
    try:
        participant_id = _participant_id(db, participant)

        # 3. Resume a half-finished session for this participant, if any and if
        #    the operator wants to.  Cancel here backs out before any hardware.
        resume_row = None
        if offer_resume:
            resumable = db.latest_resumable_session(participant_id)
            if resumable is not None:
                decision = ask_resume_or_new(
                    session_id=int(resumable["session_id"]),
                    started_at=str(resumable["started_at"]),
                    status=str(resumable["status"]),
                )
                if decision == "cancel":
                    logger.info("Operatör devam/yeni seçmedi (iptal).")
                    return 0
                if decision == "resume":
                    resume_row = resumable

        # A resumed session runs under the config it was started with, so the
        # trials still to run are the ones it originally planned.  A fresh one
        # runs under the operator's selection, which becomes its snapshot.
        if resume_row is not None:
            active_config = config_from_snapshot(str(resume_row["config_snapshot"]))
            if selection is not None:
                logger.info(
                    "Devam eden oturum kendi tasarımıyla koşuyor; seçim yok sayıldı."
                )
        elif selection is not None:
            active_config = apply_selection(config, selection)
            logger.info("Oturum seçimi: %s", selection.describe())
        else:
            active_config = config

        # 4. Hardware (under the active config).
        hardware = open_hardware(active_config)
        win = hardware.win

        good_ear = good_ear_for(participant)
        deaf_ear = deaf_ear_for(participant)
        if resume_row is not None:
            session_id = int(resume_row["session_id"])
            seed = int(resume_row["seed"])
            speaker_id = db.session_speaker_id(session_id) or select_speaker(
                active_config, session_count=db.count_sessions(), seed=seed
            )
            db.set_session_status(session_id, "running")
            completed = db.completed_trial_counts(session_id)
            logger.info("Oturum %d DEVAM ediyor. Tamamlanan: %s", session_id, completed)
        else:
            seed = random.SystemRandom().randrange(2**31)
            speaker_id = select_speaker(
                active_config, session_count=db.count_sessions(), seed=seed
            )
            completed = {}
            session_id = start_session(
                db,
                active_config,
                project_root=project_root,
                participant_id=participant_id,
                seed=seed,
                hardware=hardware,
                operator_notes=f"ui.session konuşmacı={speaker_id} iyi_kulak={good_ear}",
            )
        logger.info(
            "Oturum %d, katılımcı %s (%s), tohum %d, konuşmacı %d, iyi kulak %s, "
            "sağır kulak %s",
            session_id,
            participant.participant_code,
            participant.group_code,
            seed,
            speaker_id,
            good_ear,
            deaf_ear or "-",
        )

        _run_flow(
            active_config,
            db=db,
            session_id=session_id,
            hardware=hardware,
            project_root=project_root,
            speaker_id=speaker_id,
            good_ear=good_ear,
            deaf_ear=deaf_ear,
            seed=seed,
            limit=limit,
            checks=checks,
            completed=completed,
        )
    except AbortSession:
        status = SESSION_ABORTED
        logger.warning("Oturum ESC ile kesildi.")
    except Exception:
        status = SESSION_ABORTED
        raise
    finally:
        # Clear the abort confirmer so the closing writes below — and any later
        # run in this process — are not affected by it.
        set_abort_confirmer(None)
        if win is not None:
            win.close()
        if session_id is not None:
            db.finish_session(session_id, status)
            if active_config.database.backup_on_session_end:
                backup = db.backup(
                    resolve_path(project_root, active_config.paths.backups),
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
    deaf_ear: str | None,
    seed: int,
    limit: int | None,
    checks: list[Check],
    completed: dict[str, int],
) -> None:
    """The on-window part: confirm, welcome, modules with breaks, end.

    *completed* maps a module to how many of its trials are already recorded
    (empty for a fresh session); each module runs only what is left of it
    (:func:`remaining_plan`), so a resumed session skips what it already did.
    """
    win = hardware.win
    kb = make_keyboard()
    advance = config.screens.advance_key
    hint = config.screens.continue_hint

    # From now on ESC opens "are you sure?" instead of stopping outright; the
    # confirmer draws on this window and is cleared in run_session's finally.
    set_abort_confirmer(lambda: screens.confirm_quit(win, kb, config.screens.quit_confirm))

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
            _run_practice(
                config,
                db=db,
                session_id=session_id,
                presenter=presenter,
                win=win,
                kb=kb,
                seed=seed,
                stimuli_root=stimuli_root,
                manifest=manifest,
                speaker_id=speaker_id,
                limit=limit,
                advance=advance,
                hint=hint,
                on_break=on_break,
                completed_count=completed.get("practice", 0),
            )
            continue

        full = _plan_module(
            name,
            config,
            manifest,
            seed=seed,
            stimuli_root=stimuli_root,
            speaker_id=speaker_id,
            good_ear=good_ear,
            limit=limit,
        )
        planned = remaining_plan(
            full, completed.get(name, 0), is_stream=name in STREAM_MODULES
        )
        if not planned:
            logger.info("  %s zaten tamamlanmış — atlanıyor (resume).", name)
            continue
        if len(planned) < len(full):
            logger.info("  %s: %d/%d deneme kaldı (resume).", name, len(planned), len(full))

        screens.show_instruction(
            win,
            kb,
            config.screens.module_instructions[name],
            advance_key=advance,
            hint=hint,
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
        _run_cross_hearing(
            config,
            db=db,
            session_id=session_id,
            hardware=hardware,
            win=win,
            kb=kb,
            deaf_ear=deaf_ear,
            seed=seed,
            stimuli_root=stimuli_root,
            manifest=manifest,
            calibration=calibration,
            limit=limit,
            advance=advance,
            hint=hint,
            completed_count=completed.get("cross_hearing", 0),
        )

    screens.show_instruction(
        win, kb, config.screens.session_end, advance_key=advance, hint=None
    )


def _run_practice(
    config: ExperimentConfig,
    *,
    db: Database,
    session_id: int,
    presenter: AVPresenter,
    win: Any,
    kb: Any,
    seed: int,
    stimuli_root: Path,
    manifest: manifest_module.StimulusManifest,
    speaker_id: int,
    limit: int | None,
    advance: str,
    hint: str,
    on_break: Callable[[int, int], None],
    completed_count: int,
) -> None:
    full = practice_module.plan_trials(
        config, manifest, seed=seed, stimuli_root=stimuli_root, speaker_id=speaker_id
    )
    if limit is not None:
        full = full[:limit]
    planned = remaining_plan(full, completed_count, is_stream=False)
    if not planned:
        logger.info("Alıştırma tamamlanmış ya da denemesi yok — atlanıyor.")
        return
    screens.show_instruction(
        win, kb, config.screens.practice_intro, advance_key=advance, hint=hint
    )
    run_practice(
        config=config,
        db=db,
        session_id=session_id,
        presenter=presenter,
        win=win,
        kb=kb,
        planned=planned,
        on_break=on_break,
    )
    # practice_end doubles as the comprehension-check screen the operator
    # advances once the participant is ready for the real test.
    screens.show_instruction(
        win, kb, config.screens.practice_end, advance_key=advance, hint=hint
    )


def _run_cross_hearing(
    config: ExperimentConfig,
    *,
    db: Database,
    session_id: int,
    hardware: Hardware,
    win: Any,
    kb: Any,
    deaf_ear: str | None,
    seed: int,
    stimuli_root: Path,
    manifest: manifest_module.StimulusManifest,
    calibration: Calibration | None,
    limit: int | None,
    advance: str,
    hint: str,
    completed_count: int,
) -> None:
    if deaf_ear is None:
        logger.info(
            "Çapraz dinleme kontrol grubunda atlanıyor (sağır kulak yok)."
        )
        return
    assert config.screens.cross_hearing_intro is not None  # required when enabled
    full = cross_hearing_module.plan_trials(
        config, manifest, seed=seed, stimuli_root=stimuli_root, deaf_ear=deaf_ear
    )
    if limit is not None:
        full = full[:limit]
    # A discrete but non-resumable check: done, or re-run whole (is_stream=True).
    planned = remaining_plan(full, completed_count, is_stream=True)
    if not planned:
        logger.info("Çapraz dinleme tamamlanmış — atlanıyor (resume).")
        return
    screens.show_instruction(
        win, kb, config.screens.cross_hearing_intro, advance_key=advance, hint=hint
    )
    outcome = cross_hearing_module.run_cross_hearing(
        config=config,
        db=db,
        session_id=session_id,
        planned=planned,
        win=win,
        kb=kb,
        params=hardware.params,
        speaker=hardware.speaker,
        calibration=calibration,
        fixation=make_fixation(win),
    )
    logger.info("%s", cross_hearing_module.summarise(outcome))
