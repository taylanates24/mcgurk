"""Main experiment engine: runs the trial loop in a PsychoPy window."""

import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from psychopy import core, event, visual

from ..config import get_key_to_syllable_map, get_response_key_map, get_syllables
from ..data.database import Database
from ..data.models import SESSION_ABORTED, SESSION_COMPLETED, Session, Trial
from ..dialogs.admin_setup import ExperimentSetup
from ..utils.assets import get_assets_dir
from .response import collect_response
from .sections import build_trial_list
from .stimuli import (
    ABORT_KEY,
    AbortSession,
    create_fixation_cross,
    create_response_screen,
    load_audio_stimulus,
    load_video_stimulus,
    present_audio_only,
    present_fixation,
    present_response_screen,
    present_video,
    require_ptb_backend,
)
from .trial import TrialResult, TrialSpec

logger = logging.getLogger(__name__)

# Sections whose trials have no single correct answer.  For McGurk the
# stimulus is incongruent by construction, so "correct" is undefined; for
# dichotic listening both ears carry a valid syllable.  Scoring these as
# right/wrong would be a category error — the raw response is what counts.
_SECTIONS_WITHOUT_CORRECT_ANSWER = frozenset({"mcgurk", "dichotic"})

# Sections presented without a visible video frame.
_AUDIO_PRESENTATION_SECTIONS = frozenset({"audio_only", "dichotic"})


def _find_noise_file(noise_condition: str, config: dict[str, Any]) -> Path | None:
    """Return the noise file path for *noise_condition* from assets/noise/.

    Raises FileNotFoundError when a noisy condition was requested but no
    matching file exists.  Returning None there would silently downgrade the
    trial to the clean condition and the data would look valid but be wrong.
    """
    if noise_condition == "clean":
        return None
    noise_dir = get_assets_dir(config) / "noise"
    for ext in (".mp3", ".wav", ".ogg", ".flac"):
        candidate = noise_dir / f"{noise_condition}_noise{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Gürültü dosyası bulunamadı: {noise_dir / (noise_condition + '_noise.*')}\n"
        "Gürültülü koşul bu dosya olmadan sunulamaz."
    )


def _stimulus_path(trial_spec: TrialSpec) -> Path:
    """Return the media file this trial is presented from.

    Sections presented without a picture read from ``audio_path`` — a stereo
    WAV for dichotic trials, the congruent video the track is lifted out of
    for audio-only.  Every other section reads from ``video_path``.
    """
    path = (
        trial_spec.audio_path
        if trial_spec.section_type in _AUDIO_PRESENTATION_SECTIONS
        else trial_spec.video_path
    )
    if path is None:
        raise RuntimeError(
            f"'{trial_spec.section_type}' denemesinde uyaran dosyası yolu tanımsız "
            f"(görsel={trial_spec.visual_syllable!r}, işitsel={trial_spec.audio_syllable!r})."
        )
    return path


def resolve_seed(config: dict[str, Any]) -> int:
    """Return the RNG seed for this session.

    A fixed ``seed`` in the config reproduces an earlier session exactly;
    otherwise a fresh seed is drawn and recorded with the session so the
    trial order can be reconstructed later.
    """
    configured = config.get("seed")
    if configured is not None:
        return int(configured)
    return random.randrange(2**31)


def _show_instruction_screen(win: visual.Window, text: str):
    """Show an instruction/message screen and wait for a key press."""
    msg = visual.TextStim(win, text=text, height=0.05, wrapWidth=1.5, color=[1, 1, 1])
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", ABORT_KEY])
    if keys and keys[0] == ABORT_KEY:
        raise AbortSession()


def _show_end_screen(win: visual.Window, n_trials: int):
    """Show the experiment completion screen.

    Deliberately reports no accuracy figure: most sections have no correct
    answer, and giving participants performance feedback on a perception task
    invites demand characteristics.
    """
    text = (
        f"Deney tamamlandı!\n\n"
        f"Tamamlanan deneme sayısı: {n_trials}\n\n"
        f"Katılımınız için teşekkür ederiz.\n\n"
        f"[SPACE] tuşuna basarak çıkabilirsiniz."
    )
    msg = visual.TextStim(win, text=text, height=0.05, wrapWidth=1.5, color=[1, 1, 1])
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["space", ABORT_KEY])


def run_experiment(
    setup: ExperimentSetup,
    participant_id: int,
    config: dict[str, Any],
    db: Database,
) -> str:
    """Run the full experiment.

    Args:
        setup: Admin setup result (speaker, sections, noise).
        participant_id: ID of the participant in the database.
        config: Experiment configuration dict.
        db: Database instance for saving results.

    Returns:
        The final session status — ``SESSION_COMPLETED`` or ``SESSION_ABORTED``.
        Callers must not report success without checking this: a session that
        was interrupted still returns normally.
    """
    # Refuse to run on a backend that cannot schedule audio against the flip
    # clock.  Checked before anything is written to the database.
    require_ptb_backend()

    seed = resolve_seed(config)
    logger.info("Oturum RNG seed: %d", seed)

    # Build the trial list before creating the session row, so a configuration
    # problem does not leave an empty session behind.
    trials = build_trial_list(
        speaker=setup.speaker,
        selected_sections=setup.selected_sections,
        config=config,
        seed=seed,
        noisy_sections=setup.noisy_sections,
    )

    if not trials:
        logger.warning("Seçilen bölümler için hiç deneme üretilmedi.")
        return SESSION_ABORTED

    session = Session(
        participant_id=participant_id,
        speaker=setup.speaker.folder_name,
        sections_run=",".join(setup.selected_sections),
        seed=seed,
    )
    session_id = db.add_session(session)

    # Get config values
    syllables = get_syllables(config)
    key_map = get_response_key_map(config)
    key_to_syl = get_key_to_syllable_map(config)
    valid_keys = list(key_to_syl.keys())
    fixation_ms = config.get("fixation_duration_ms", 3000)
    bg_color = config.get("background_color", [0.5, 0.5, 0.5])
    fullscreen = config.get("fullscreen", True)
    monitor_name = config.get("monitor_name", "default")
    # Without an explicit size PsychoPy assumes 800x600 and warns that the
    # screen is actually something else on every fullscreen run.
    window_size = config.get("window_size", [1920, 1080])

    # Create PsychoPy window.  waitBlanking is explicit: without it flips do
    # not block on the vertical retrace and frame timing is unmeasurable.
    win = visual.Window(
        size=window_size,
        fullscr=fullscreen,
        monitor=monitor_name,
        color=bg_color,
        units="height",
        allowGUI=False,
        waitBlanking=True,
    )

    status = SESSION_ABORTED
    n_completed = 0

    try:
        # Create reusable stimuli
        fixation = create_fixation_cross(win, config)
        response_stims = create_response_screen(win, syllables, key_map)
        clock = core.Clock()

        # Key mapping instruction
        key_info = "  |  ".join(f"[{key_map[s]}] = {s.upper()}" for s in syllables)
        instruction_text = (
            f"McGurk Deney\n\n"
            f"Videolar izletilecek ve her videonun ardından\n"
            f"NE DUYDUĞUNUZU seçmeniz istenecektir.\n\n"
            f"Tuş atamaları:\n{key_info}\n\n"
            f"Toplam deneme sayısı: {len(trials)}\n\n"
            f"Hazır olduğunuzda [SPACE] tuşuna basınız."
        )
        _show_instruction_screen(win, instruction_text)

        # Run trials
        results: list[TrialResult] = []

        for trial_idx, trial_spec in enumerate(trials):
            # --- Load video + audio before the fixation period so file I/O
            # and ffmpeg extraction do not land inside the presentation. ---
            noise_file = _find_noise_file(trial_spec.noise_condition, config)
            source = _stimulus_path(trial_spec)

            movie = None
            if trial_spec.section_type in _AUDIO_PRESENTATION_SECTIONS:
                # Nothing to display — no MovieStim is created at all.
                # Dichotic files are pre-mixed stereo; noise is not applied.
                audio = load_audio_stimulus(
                    source,
                    noise_file=None if trial_spec.section_type == "dichotic" else noise_file,
                    snr_db=None if trial_spec.section_type == "dichotic" else trial_spec.snr_db,
                )
            elif trial_spec.section_type == "visual_only":
                movie, audio = load_video_stimulus(win, source, with_audio=False)
            else:
                # mcgurk, av_congruent
                movie, audio = load_video_stimulus(
                    win, source, with_audio=True,
                    noise_file=noise_file, snr_db=trial_spec.snr_db,
                )

            try:
                # Fixation (file is already loaded & parsed)
                present_fixation(win, fixation, fixation_ms)

                clock.reset()

                # Present stimulus based on section type
                if movie is None:
                    video_end_time = present_audio_only(win, audio, fixation, clock)
                elif trial_spec.section_type == "visual_only":
                    video_end_time = present_video(win, movie, clock)
                else:
                    # McGurk and AV congruent: normal video+audio
                    video_end_time = present_video(win, movie, clock, audio=audio)

                # Show response options
                options_shown_time = clock.getTime()
                trial_info = f"{trial_idx + 1} / {len(trials)}"
                present_response_screen(win, response_stims, trial_info=trial_info)

                # Collect response
                resp = collect_response(
                    valid_keys=valid_keys,
                    key_to_syllable=key_to_syl,
                    video_end_time=video_end_time,
                    options_shown_time=options_shown_time,
                    clock=clock,
                )
            finally:
                # MovieStim holds a decoder and GPU textures; a session is
                # hundreds of trials long, so releasing it is not optional.
                if movie is not None:
                    movie.unload()

            # Determine correctness.  Sections without a correct answer store
            # NULL rather than a fabricated right/wrong verdict.
            if trial_spec.section_type in _SECTIONS_WITHOUT_CORRECT_ANSWER:
                is_correct = None
            else:
                is_correct = resp.syllable == trial_spec.correct_answer

            # Dichotic: record which ear the reported syllable came from.
            if trial_spec.section_type == "dichotic":
                left_syl, right_syl = trial_spec.correct_answer.split("|")
                if resp.syllable == left_syl:
                    trial_spec.ear_side = "left"
                elif resp.syllable == right_syl:
                    trial_spec.ear_side = "right"
                else:
                    trial_spec.ear_side = "neither"

            result = TrialResult(
                spec=trial_spec,
                participant_response=resp.syllable,
                is_correct=is_correct,
                rt_from_video_end_ms=resp.rt_from_video_end_ms,
                rt_from_options_shown_ms=resp.rt_from_options_shown_ms,
                trial_order=trial_idx + 1,
            )
            results.append(result)

            # Save trial to database immediately
            trial_record = Trial(
                session_id=session_id,
                participant_id=participant_id,
                section_type=trial_spec.section_type,
                speaker=trial_spec.speaker_name,
                visual_syllable=trial_spec.visual_syllable,
                audio_syllable=trial_spec.audio_syllable,
                noise_condition=trial_spec.noise_condition,
                snr_db=trial_spec.snr_db,
                participant_response=resp.syllable,
                correct_answer=trial_spec.correct_answer,
                is_correct=is_correct,
                rt_from_video_end_ms=resp.rt_from_video_end_ms,
                rt_from_options_shown_ms=resp.rt_from_options_shown_ms,
                trial_order=trial_idx + 1,
                ear_side=trial_spec.ear_side,
            )
            db.add_trial(trial_record)
            n_completed = len(results)

        status = SESSION_COMPLETED
        _show_end_screen(win, n_completed)

    except AbortSession:
        # Operator or participant pressed the abort key.  Everything recorded
        # up to this point stays in the database; only the session status
        # changes, so the run can be told apart from a completed one.
        logger.info(
            "Oturum kesildi (%d deneme kaydedildikten sonra).", n_completed
        )

    finally:
        # The session row is closed out in every exit path — normal finish,
        # abort, or an exception — so no session is ever left as 'running'.
        db.finish_session(session_id, status, datetime.now().isoformat())
        logger.info(
            "Oturum %d kapatıldı: durum=%s, kaydedilen deneme=%d, seed=%d",
            session_id, status, n_completed, seed,
        )
        win.close()

    return status
