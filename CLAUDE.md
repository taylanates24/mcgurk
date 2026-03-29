# McGurk Effect Experiment Platform

## Project Overview
TÜBİTAK-supported academic research project: "Behavioral Assessment of Audiovisual Speech Integration in Single-Sided Deafness (SSD)". A desktop experiment platform that presents audiovisual speech stimuli and collects participant responses to measure multisensory integration.

## Tech Stack
- **Language**: Python 3.10 (PsychoPy requires <3.12)
- **Experiment Engine**: PsychoPy — psychophysics-grade timing, video playback (MovieStim), response collection
- **Pre-experiment UI**: PsychoPy `gui.Dlg` dialogs for login/demographics and admin setup
- **Admin Panel**: Separate script (`admin.py`) using PySide6 for results browsing and export
- **Database**: SQLite (via Python stdlib `sqlite3`) + CSV export capability
- **Timing**: PsychoPy `core.Clock` (sub-millisecond precision) for reaction time
- **Noise Generation**: numpy + scipy for white noise / speech-shaped noise (pre-generated)
- **Config**: YAML (`pyyaml`) for all experiment parameters
- **Packaging**: PyInstaller for Windows executable distribution

## Architecture

### Two Entry Points
1. **`main.py`** — Experiment runner (PsychoPy-based)
   - Login dialog → Admin setup (speaker + section selection) → Fullscreen experiment → End screen
2. **`admin.py`** — Admin panel (PySide6-based, separate process)
   - Browse participants, view results, export CSV, manage sessions

### Application Flow (main.py)
```
[PsychoPy gui.Dlg]                                    [PsychoPy visual.Window — fullscreen]
Login/Demographics  →  Admin Setup (speaker + sections)  →  Experiment Loop  →  End Screen
                       (admin picks speaker & sections)      ↓
                                                   Fixation (+) → Video → Response (ba/da/ga) → repeat
```

### Test Sections (admin selects before experiment)
1. **McGurk** — incongruent stimuli only (visual ≠ audio), 6 videos per speaker (all permutations of ba/da/ga where visual ≠ audio)
2. **AV Congruent** — visual = audio (ba-ba, da-da, ga-ga), 3 videos per speaker
3. **A-only** — audio only, screen shows fixation cross or blank
4. **V-only** — video only, audio muted
5. **Dichotic Listening** — audio only to headphones, different syllable per ear, records which ear the response matches

Each section has **clean** and **noisy** variants. Noise type and SNR level are configurable.

### Project Structure (Target)
```
mcgurk/
├── CLAUDE.md
├── config.yaml                  # All experiment parameters
├── requirements.txt
├── main.py                      # Experiment entry point (PsychoPy)
├── admin.py                     # Admin panel entry point (PySide6)
├── assets/
│   ├── female_speaker_1/        # Vis-{x}_Aud-{y}.mp4
│   ├── male_speaker_1/
│   └── noisy/                   # Pre-generated noisy versions
├── src/
│   ├── __init__.py
│   ├── config.py                # Config loader (YAML)
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── login.py             # PsychoPy gui.Dlg — demographics form
│   │   └── admin_setup.py       # PsychoPy gui — admin picks speaker + sections to run
│   ├── experiment/
│   │   ├── __init__.py
│   │   ├── engine.py            # Trial sequencer, state machine, main experiment loop
│   │   ├── trial.py             # Single trial data model
│   │   ├── sections.py          # Section definitions (McGurk, AV, A-only, V-only, Dichotic)
│   │   ├── stimuli.py           # Stimulus loading, MovieStim/Sound management
│   │   └── response.py          # Response collection, RT measurement via core.Clock
│   ├── data/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLite schema, read/write operations
│   │   ├── models.py            # Data models (Participant, Trial, Session)
│   │   └── export.py            # CSV/Excel export
│   ├── admin/
│   │   ├── __init__.py
│   │   └── panel.py             # PySide6 admin panel (results viewer, export)
│   └── utils/
│       ├── __init__.py
│       └── assets.py            # Asset discovery (scan speaker folders, parse filenames)
├── scripts/
│   └── generate_noisy_stimuli.py  # Pre-generate noisy video variants
├── data/                        # SQLite DB files (gitignored)
│   └── mcgurk.db
└── tests/
```

## PsychoPy Usage Notes
- **Video**: `visual.MovieStim` with `noAudio=True` for video playback — hardware-accelerated, frame-accurate
- **Audio**: extracted from video via ffmpeg, played through `sound.Sound` (ptb backend) for precise A/V sync; SDL2 audio path is intentionally bypassed
- **Timing**: `core.Clock` for RT measurement, `core.wait()` for fixation duration
- **Response**: `event.waitKeys()` or clickable visual elements for ba/da/ga selection
- **Fullscreen**: experiment runs in `visual.Window(fullscr=True)` for minimal distraction
- **Monitor calibration**: configure via `monitors.Monitor` for consistent visual presentation
- **Dichotic audio**: use stereo sound files with left/right channel separation via numpy array manipulation + `sound.Sound`

## Asset Conventions
- Video location: `assets/{speaker_folder}/Vis-{visual}_Aud-{audio}.mp4`
- Speaker folders follow pattern: `{gender}_speaker_{n}` (e.g., `female_speaker_1`, `male_speaker_1`)
- **Auto-discovery**: speakers are detected at runtime by scanning `assets/` — adding a new folder like `female_speaker_2/` with the correct video files is enough, no code or config change needed
- Syllables (Phase 1): `ba`, `da`, `ga`
- Audio is embedded in video — no separate sync needed
- `Zone.Identifier` files (Windows artifacts) should be gitignored
- Noisy variants: `assets/noisy/{speaker_folder}/Vis-{visual}_Aud-{audio}_{noise_type}_{snr}dB.mp4`

## Config Parameters (config.yaml)
Key configurable values:
- `syllables`: list of syllables (default: [ba, da, ga])
- `fixation_duration_ms`: time for fixation cross (default: 3000)
- `noise.type`: white | speech_shaped | cocktail
- `noise.snr_db`: signal-to-noise ratio (default: 5)
- `rt_mode`: "from_video_end" | "from_options_shown" (both are always recorded)
- `sections`: which sections are available
- `trial_repetitions`: how many times each trial repeats
- `fullscreen`: true | false
- `monitor_name`: PsychoPy monitor profile name

## Data Model
### Participants Table
- participant_id, name, age, gender, group (SSD-right, SSD-left, control), session_date, notes

### Trials Table
- trial_id, participant_id, session_id, section_type, speaker, visual_syllable, audio_syllable, noise_condition, snr_db, participant_response, correct_answer, is_correct, rt_from_video_end_ms, rt_from_options_shown_ms, ear_side (for dichotic), trial_order, timestamp

### Sessions Table
- session_id, participant_id, sections_run, speaker, started_at, completed_at, admin_notes

## Key Design Decisions
1. **Experiment accuracy > UI aesthetics** — PsychoPy chosen for psychophysics-grade timing
2. **Two separate apps**: PsychoPy for experiment (main.py), PySide6 for admin (admin.py) — avoids event loop conflicts
3. **Correct answer = audio** (not visual) for McGurk and AV sections
4. **Reaction time**: both `rt_from_video_end` and `rt_from_options_shown` are always recorded; config selects primary
5. **Video randomization**: trials within each section are randomized per participant
6. **Noisy stimuli**: pre-generated and saved to `assets/noisy/` (not mixed at runtime) to avoid latency
7. **Speaker thumbnails**: extracted from first frame of a congruent video for speaker selection
8. **Phase 2 ready**: word-level stimuli support planned in asset/config structure but not implemented in Phase 1
9. **Admin can allow re-runs**: same participant can repeat experiments at admin's discretion
10. **Dichotic audio**: stereo files with isolated L/R channels, generated from mono syllable recordings

## Development Environment
- Primary OS: Linux (WSL2), must also work on Windows
- Python 3.10 via Miniconda: `conda activate mcgurk`
- Install: `pip install -r requirements.txt`
- Run experiment: `python main.py` (WSL2'de `LIBGL_ALWAYS_SOFTWARE=1` prefix gerekebilir)
- Run admin panel: `python admin.py`
- Monitor setup (ilk kurulumda bir kez): `python scripts/setup_monitor.py`
- Language: Turkish UI, English code/comments

## Known Issues & Notes
- **A/V sync stratejisi**: `MovieStim` (ffpyplayer) ses çalmak için SDL2 kullanır ve bu Windows'ta belirgin gecikme yaratır. Çözüm olarak `MovieStim` her zaman `noAudio=True` ile oluşturulur; ses ffmpeg ile ayrı wav dosyasına çıkarılıp PsychoPy `sound.Sound` (ptb backend) üzerinden çalınır. Bu sayede SDL2 bypass edilir ve sub-ms A/V sync sağlanır. Çıkarılan wav'lar process boyunca cache'lenir, çıkışta temizlenir.
- **Windows audio backend**: `main.py`'de `SDL_AUDIODRIVER=wasapi` ortam değişkeni ayarlanır (MovieStim init sırasında SDL2'ye hâlâ dokunulduğu için). Video dosyaları fixation öncesinde yüklenerek dosya I/O gecikmesi playback'ten ayrıştırılır.
- **WSL2 OpenGL**: WSL2'de `LIBGL_ALWAYS_SOFTWARE=1` gerekir. Gerçek deneyde native Windows kullanılacak.
- **PsychoPy gui.Dlg vs DlgFromDict**: `gui.Dlg` field parsing'de sorun çıkarıyor, `gui.DlgFromDict` kullanılıyor.
- **Dichotic Listening**: Runtime'da congruent videolardan ffmpeg ile ses çıkarılıp stereo (L/R) numpy array olarak PsychoPy sound.Sound ile çalınıyor. ffmpeg sistemde kurulu olmalı.
- **Noisy stimuli generation**: `scripts/generate_noisy_stimuli.py` henüz yazılmadı.
- **Admin panel**: `admin.py` PySide6 ile ayrı process olarak çalışır, PsychoPy ile aynı process'te çalıştırılamaz.

## Git Workflow
- `master`: stable releases
- `develop`: active development
- Feature branches from `develop`

## Don'ts
- Don't hardcode syllables, speaker names, or trial counts — everything from config
- Don't mix audio at runtime for noisy conditions — use pre-generated files
- Don't mix PsychoPy and PySide6 in the same process — separate entry points
- Don't store experiment data in git (data/ is gitignored)
- Don't use PsychoPy Builder GUI — all code is hand-written Coder style
