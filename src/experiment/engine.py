"""Main experiment engine: runs the trial loop in a PsychoPy window."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from psychopy import visual, core, event

from ..config import get_syllables, get_response_key_map, get_key_to_syllable_map
from ..data.database import Database
from ..data.models import Session, Trial
from ..dialogs.admin_setup import ExperimentSetup
from .sections import build_trial_list
from .stimuli import (
    create_fixation_cross,
    create_response_screen,
    load_video_stimulus,
    present_fixation,
    present_response_screen,
    present_video,
)
from .response import collect_response
from .trial import TrialResult
from ..utils.assets import get_assets_dir

logger = logging.getLogger(__name__)


def _find_noise_file(noise_condition: str, config: dict[str, Any]) -> Path | None:
    """Return the noise file path for *noise_condition* from assets/noise/.

    Tries common audio extensions in order.  Returns None if not found.
    """
    if noise_condition == "clean":
        return None
    noise_dir = get_assets_dir(config) / "noise"
    for ext in (".mp3", ".wav", ".ogg", ".flac"):
        candidate = noise_dir / f"{noise_condition}_noise{ext}"
        if candidate.exists():
            return candidate
    logger.warning("Gürültü dosyası bulunamadı: assets/noise/%s_noise.*", noise_condition)
    return None


def _show_instruction_screen(win: visual.Window, text: str):
    """Show an instruction/message screen and wait for a key press."""
    msg = visual.TextStim(win, text=text, height=0.05, wrapWidth=1.5, color=[1, 1, 1])
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def _show_end_screen(win: visual.Window, results: list[TrialResult]):
    """Show experiment completion screen with basic stats."""
    total = len(results)
    correct = sum(1 for r in results if r.is_correct)
    pct = (correct / total * 100) if total > 0 else 0

    text = (
        f"Deney tamamlandı!\n\n"
        f"Toplam deneme: {total}\n"
        f"Doğru cevap: {correct} / {total} ({pct:.0f}%)\n\n"
        f"Katılımınız için teşekkür ederiz.\n\n"
        f"[SPACE] tuşuna basarak çıkabilirsiniz."
    )
    msg = visual.TextStim(win, text=text, height=0.05, wrapWidth=1.5, color=[1, 1, 1])
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])


def run_experiment(
    setup: ExperimentSetup,
    participant_id: int,
    config: dict[str, Any],
    db: Database,
):
    """Run the full experiment.

    Args:
        setup: Admin setup result (speaker, sections, noise).
        participant_id: ID of the participant in the database.
        config: Experiment configuration dict.
        db: Database instance for saving results.
    """
    # Create session
    session = Session(
        participant_id=participant_id,
        speaker=setup.speaker.folder_name,
        sections_run=",".join(setup.selected_sections),
    )
    session_id = db.add_session(session)

    # Build trial list
    trials = build_trial_list(
        speaker=setup.speaker,
        selected_sections=setup.selected_sections,
        config=config,
        noisy_sections=setup.noisy_sections,
    )

    if not trials:
        return

    # Get config values
    syllables = get_syllables(config)
    key_map = get_response_key_map(config)
    key_to_syl = get_key_to_syllable_map(config)
    valid_keys = list(key_to_syl.keys())
    fixation_ms = config.get("fixation_duration_ms", 3000)
    bg_color = config.get("background_color", [0.5, 0.5, 0.5])
    fullscreen = config.get("fullscreen", True)
    monitor_name = config.get("monitor_name", "default")

    # Create PsychoPy window
    win = visual.Window(
        fullscr=fullscreen,
        monitor=monitor_name,
        color=bg_color,
        units="height",
        allowGUI=False,
    )

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
        aborted = False

        for trial_idx, trial_spec in enumerate(trials):
            # --- Load video + audio BEFORE fixation so file I/O and
            # ffmpeg extraction happen during the fixation period. ---
            noise_file = _find_noise_file(trial_spec.noise_condition, config)
            snr_db = trial_spec.snr_db

            if trial_spec.section_type == "visual_only":
                movie, audio = load_video_stimulus(win, trial_spec.video_path, with_audio=False)
            elif trial_spec.section_type == "audio_only":
                movie, audio = load_video_stimulus(
                    win, trial_spec.audio_path, with_audio=True,
                    noise_file=noise_file, snr_db=snr_db,
                )
            elif trial_spec.section_type == "dichotic":
                movie, audio = load_video_stimulus(win, trial_spec.video_path, with_audio=True)
            else:
                # mcgurk, av_congruent
                movie, audio = load_video_stimulus(
                    win, trial_spec.video_path, with_audio=True,
                    noise_file=noise_file, snr_db=snr_db,
                )

            # Fixation (file is already loaded & parsed)
            present_fixation(win, fixation, fixation_ms)

            clock.reset()

            # Present stimulus based on section type
            if trial_spec.section_type == "visual_only":
                video_end_time = present_video(win, movie, clock)
            elif trial_spec.section_type == "audio_only":
                # Play muted video (for timing) with cover hiding frames,
                # audio via ptb backend for precise sync
                cover = visual.Rect(
                    win, width=2, height=2, pos=(0, 0),
                    fillColor=bg_color, lineColor=bg_color,
                )
                movie.play()
                if audio is not None:
                    audio.play()
                while not movie.isFinished:
                    movie.draw()
                    cover.draw()
                    fixation.draw()
                    win.flip()
                win.flip()
                video_end_time = clock.getTime()
                if audio is not None:
                    audio.stop()
            elif trial_spec.section_type == "dichotic":
                # Stereo mp4: left ear = one syllable, right ear = another
                cover = visual.Rect(
                    win, width=2, height=2, pos=(0, 0),
                    fillColor=bg_color, lineColor=bg_color,
                )
                movie.play()
                if audio is not None:
                    audio.play()
                while not movie.isFinished:
                    movie.draw()
                    cover.draw()
                    fixation.draw()
                    win.flip()
                win.flip()
                video_end_time = clock.getTime()
                if audio is not None:
                    audio.stop()
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

            if resp is None:
                # Escape pressed — abort experiment
                aborted = True
                break

            # Determine correctness
            # Dichotic has no single correct answer — record which ear matches
            if trial_spec.section_type == "dichotic":
                left_syl, right_syl = trial_spec.correct_answer.split("|")
                if resp.syllable == left_syl:
                    trial_spec.ear_side = "left"
                elif resp.syllable == right_syl:
                    trial_spec.ear_side = "right"
                else:
                    trial_spec.ear_side = "neither"
                is_correct = True  # no wrong answer in dichotic
            else:
                is_correct = resp.syllable == trial_spec.correct_answer

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

        # End screen
        if not aborted:
            _show_end_screen(win, results)

        # Complete session
        db.complete_session(session_id, datetime.now().isoformat())

    finally:
        win.close()
