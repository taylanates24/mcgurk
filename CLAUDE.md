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
- **Config**: YAML (`pyyaml`) parsed into **Pydantic v2** models (`mcgurk/config`); unknown fields are rejected
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

### Two packages side by side (from Adım 1)

`src/` is the Adım 0 baseline and still runs the experiment. `mcgurk/` is the
new platform, built next to it and retired `src/` in Adım 8. They use separate
config files and separate database files — the schemas are incompatible.

**Hard rule: `mcgurk/config`, `mcgurk/db` and `mcgurk/stimuli` must not import
PsychoPy.** CI has no PsychoPy installed and an analysis machine need not
either; `tests/mcgurk/test_package_boundaries.py` enforces this with an AST
check. `engine/`, `modules/` and `ui/` are exempt — that is where PsychoPy
belongs.

```
mcgurk/                          # new platform (Adım 1→)
├── config/
│   ├── schema.py                # Pydantic models, §G — extra="forbid"
│   ├── loader.py                # load, validate, design summary
│   ├── calibration.py           # 02_kalibrasyon.md JSON (Turkish keys → aliases)
│   └── __main__.py              # python -m mcgurk.config
├── db/
│   ├── schema.sql               # 6 tables + v_trials_flat + §A.10 trigger
│   ├── database.py              # access layer; trial writes do NOT commit (§A.5)
│   ├── design.py                # trials.design_extra validation per module
│   ├── models.py                # row dataclasses
│   └── backup.py                # VACUUM INTO — never a file copy
├── stimuli/                     # Adım 2 — offline preparation, no PsychoPy
│   ├── ffmpeg.py                # binary discovery, probe, silent re-encode
│   ├── wavfile.py               # 24-bit PCM I/O via soundfile
│   ├── dsp.py                   # burst, active level, LTAS/SSN, SNR, GIN gaps
│   ├── manifest.py              # manifest.json models + lookups
│   ├── prepare.py               # the pipeline
│   └── verify.py                # re-measure from disk, report
├── engine/                      # Adım 3 (empty)
├── modules/                     # Adım 4–7c (empty)
├── analysis/                    # Adım 9 (empty)
├── ui/                          # Adım 8 (empty)
├── logging_setup.py
└── provenance.py                # git commit, OS, package versions
config/experiment.yaml           # new single source of truth (§G)
stimuli/                         # prepared set + manifest.json (gitignored)
tools/verify_backup.py           # an untested backup is not a backup
tools/prepare_stimuli.py         # assets/ -> stimuli/
tools/verify_stimuli.py          # audit stimuli/ against manifest + design
.github/workflows/ci.yml         # ruff + mypy, pytest -m "not psychopy"
```

### Prepared stimuli (`stimuli/`, from Adım 2)

`assets/` is the raw recording and is never presented by the new package.
`tools/prepare_stimuli.py` reads only the **congruent** takes
(`Vis-<t>_Aud-<t>.mp4`) and writes:

```
stimuli/manifest.json
stimuli/video/speaker_<id>/Vis-<t>.mp4                  silent, CFR 30 fps, all-intra
stimuli/audio/speaker_<id>/Vis-<v>_Aud-<a>.wav          48 kHz 24-bit, burst-aligned
stimuli/audio_noisy/speaker_<id>/…_ssn<snr>dB_<n>.wav   n noise instances per cell
stimuli/dichotic/speaker_<id>/Left-<l>_Right-<r>.wav    both ears on one burst time
stimuli/gin/segment_<nn>.wav                            gaps cut offline
stimuli/noise/speech_shaped_noise.wav                   from the corpus LTAS
```

Key points that are easy to get wrong:
- **Alignment target is per video, not global.** Audio token Y mounted on
  video X sits at X's own acoustic burst time, because the source recording
  was already in sync. The corpus spread is up to ~250 ms between tokens of
  one speaker, so this is not a rounding detail.
- The 29.97 → 30 fps conversion compresses the visual timeline by 0.1%, so the
  alignment target is scaled by `source_fps / target_fps` too.
- Levels are equalised on **speech-active** RMS, never whole-file RMS.
- "Silence" for trimming purposes is measured against each take's own noise
  floor: these recordings sit only ~30 dB below the speech peak.
- Frames that are exactly zero are alignment padding, not a quiet part of the
  recording — the floor estimate excludes them, or the first sample of real
  hiss reads as an onset.
- LTAS analysis uses `n_fft = 4096`; at 1024 the 125 Hz third-octave band
  contains no FFT bin and reads as 20 dB of silence.

### Legacy Structure (src/, Adım 0)
```
mcgurk/
├── CLAUDE.md
├── config.yaml                  # legacy experiment parameters (src/ only)
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
- Audio is embedded in the source video, but is **never played from it** — it is extracted to a separate wav and scheduled independently (see A/V sync strategy below)
- `Zone.Identifier` files (Windows artifacts) should be gitignored
- Noisy variants: `assets/noisy/{speaker_folder}/Vis-{visual}_Aud-{audio}_{noise_type}_{snr}dB.mp4`
- Dichotic stimuli: `assets/dichotic/{speaker_folder}/Left-{left}_Right-{right}.wav` — 48 kHz stereo PCM, **not** a video container

## Legacy Config Parameters (config.yaml — src/ only)
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

## Config Parameters (config/experiment.yaml — new package)
Validated by `mcgurk/config/schema.py`; **unknown fields are an error**.
- `experiment.mode`: `development` | `data_collection`. The second gates on a
  measured `timing.system_av_offset_ms`, an existing readable
  `audio.calibration_file`, `display.fullscreen: true` and an explicit
  `audio.device`.
- `modules.*`: six modules — `mcgurk`, `avsr`, `tbw`, `oddball`, `dichotic`,
  `gin`. Each knows its own trial count; `python -m mcgurk.config` prints the
  totals and a duration estimate.
- `display.video_position` must stay `[0, 0]` (§A.13) — the schema rejects
  anything else.
- Categorisation maps (`fusion_map`, `combination_map`) live here, not in code
  (§A.9). Their keys must name a real `av_pairs` entry and their values must be
  in `response_set`; both are checked at load.
- `stimulus_prep.*`: everything `tools/prepare_stimuli.py` needs — the seed,
  the `speaker_id` → source-folder map, the token list, and the video/audio/
  burst/noise/GIN parameters. The SNRs to prepare are **derived** from the
  enabled modules' `noise_conditions`, never listed a second time. Load-time
  checks: every `modules.*.speaker_id` names a declared speaker, and every
  token the design uses is in `stimulus_prep.tokens`.

## Data Model (new package — data/mcgurk.sqlite)
Six tables + `v_trials_flat`. See `mcgurk/db/schema.sql`.
- `participants` — anonymous code, group (`SSD_R`/`SSD_L`/`CTRL`), age, sex,
  deprivation_months, PTA left/right, postlingual
- `calibrations` — parsed 02_kalibrasyon.md output plus the verbatim file
- `sessions` — seed, **config snapshot**, git commit, PsychoPy/Python version,
  OS, audio backend, measured refresh, `system_av_offset_ms`, status
- `blocks` — module, index, planned trial count, status
- `trials` — shared design columns + realised timing; module-specific fields in
  `design_extra` (JSON), validated by `mcgurk/db/design.py`
- `responses` — **0..n per trial**: none on timeout, several for a GIN segment
- A trigger refuses `is_correct` on `mcgurk`/`dichotic` trials (§A.10)

## Legacy Data Model (src/, data/mcgurk.db)
### Participants Table
- participant_id, **participant_code** (anonymous — never a name, KVKK), age, gender, group (SSD-right, SSD-left, control), created_at, notes

### Trials Table
- trial_id, participant_id, session_id, section_type, speaker, visual_syllable, audio_syllable, noise_condition, snr_db, participant_response, correct_answer, is_correct (**NULL for mcgurk/dichotic**), rt_from_video_end_ms, rt_from_options_shown_ms, ear_side (for dichotic), trial_order, timestamp

### Sessions Table
- session_id, participant_id, sections_run, speaker, **seed**, **status** (running/completed/aborted), started_at, completed_at, admin_notes

## Key Design Decisions
1. **Experiment accuracy > UI aesthetics** — PsychoPy chosen for psychophysics-grade timing
2. **Two separate apps**: PsychoPy for experiment (main.py), PySide6 for admin (admin.py) — avoids event loop conflicts
3. **Incongruent trials have no correct answer.** For `mcgurk` and `dichotic`, `is_correct` is stored as NULL and excluded from accuracy figures. Scoring an incongruent trial against the audio syllable is a category error: Vis-/ga/ + Aud-/ba/ → "DA" is classic fusion, not a mistake. Only the congruent sections (`av_congruent`, `audio_only`, `visual_only`) are scored.
4. **Reaction time**: both `rt_from_video_end` and `rt_from_options_shown` are always recorded; config selects primary
5. **Video randomization**: trials are shuffled with a **seeded** RNG and the seed is stored on the session, so any session's trial order can be reproduced
6. **Noisy stimuli**: pre-generated and saved to `assets/noisy/` (not mixed at runtime) to avoid latency
7. **Speaker thumbnails**: extracted from first frame of a congruent video for speaker selection
8. **Phase 2 ready**: word-level stimuli support planned in asset/config structure but not implemented in Phase 1
9. **Admin can allow re-runs**: same participant can repeat experiments at admin's discretion
10. **Dichotic audio**: stereo WAVs with isolated L/R channels, pre-generated from the congruent recordings — no video container, no run-time conversion

## Development Environment
- Primary OS: Linux (WSL2), must also work on Windows
- **Python 3.10 via Miniconda:** `C:\Users\tayla\miniconda3\envs\mcgurk`.
  That directory is not in conda's `envs_dirs` (which points at `anaconda3\envs`),
  so the env lists without a name and `conda activate mcgurk` fails until you run
  `conda config --append envs_dirs C:\Users\tayla\miniconda3\envs`. Activating by
  full path always works. Base is Python 3.13, where
  `pip install -r requirements.txt` fails with
  `No matching distribution found for psychopy==2026.1.2` (psychopy needs <3.12).
- Install: `pip install -r requirements.txt`
- Run experiment: `python main.py` (WSL2'de `LIBGL_ALWAYS_SOFTWARE=1` prefix gerekebilir)
- Run admin panel: `python admin.py`
- Monitor setup (ilk kurulumda bir kez): `python scripts/setup_monitor.py`
- Validate config + design cost: `python -m mcgurk.config`
- Prepare stimuli: `python tools/prepare_stimuli.py [--force]`
- Verify stimuli: `python tools/verify_stimuli.py [--quick]`
- Verify a backup: `python tools/verify_backup.py <yedek> --compare-with data/mcgurk.sqlite`
- Tests: `pytest` locally; `pytest -m "not psychopy"` is what CI runs (no
  PsychoPy installed there — see `requirements-ci.txt`)
- Language: Turkish UI, English code/comments

## Known Issues & Notes
- **A/V sync stratejisi**: `MovieStim` (ffpyplayer) ses çalmak için SDL2 kullanır ve bu Windows'ta belirgin gecikme yaratır. Çözüm olarak videodan ffmpeg ile sesi tamamen sökülmüş bir kopya üretilir ve `MovieStim`'e o verilir; ses ayrı wav olarak çıkarılıp `sound.Sound` (ptb backend) ile `play(when=win.getFutureFlipTime(clock="ptb"))` üzerinden flip saatine karşı zamanlanır. Çıkarılan wav'lar ve sessiz videolar process boyunca cache'lenir, çıkışta temizlenir.
- **`noAudio=True` KAPATILAMAZ (PsychoPy 2026.1)**: `MovieStim.__init__` içinde `audioLib is None and movieLib == 'ffpyplayer'` ise `self._noAudio = False` atanır — çağıranın `noAudio` argümanı **koşulsuz eziliyor**. Başka bir `audioLib` vermek de çare değil: o dalda `MovieAudioError` fırlatılıyor ("only supported with the 'sdl2' library"). Yani SDL2 ses yolunu kapatmanın tek yolu dosyada ses akışı bırakmamaktır. Bu yüzden her `MovieStim` çağrısı `Using \`sdl2\` for audio playback` uyarısı üretir; uyarı beklenen ve zararsızdır. `_quiet_movie_init()` context manager'ı bunu **yalnızca constructor çağrısı boyunca** bastırır (PsychoPy kendi `psychopy.logging.console`'unu kullandığı için stdlib logger seviyesi işe yaramaz) — sunum sırasındaki düşen kare uyarıları etkilenmez. `tests/test_silent_video.py` hem sessiz kopyalarda ses akışı olmadığını hem de konsol seviyesinin geri yüklendiğini doğrular.
- **Ses backend API'si (PsychoPy 2026.1)**: Backend seçimi `prefs.hardware['audioLib']`'ten `sound.Sound.backend` sınıf niteliğine taşındı; `sound.audioLib` **artık yok**. `src/experiment/stimuli.py:require_ptb_backend()` doğru niteliği kontrol eder, modülün gerçekten yüklendiğini doğrular ve ptb değilse programı durdurur — sessiz geri düşüş yasak.
- **Windows audio backend**: `main.py`'de `SDL_AUDIODRIVER=wasapi` ortam değişkeni ayarlanır (MovieStim init sırasında SDL2'ye hâlâ dokunulduğu için). Video dosyaları fixation öncesinde yüklenerek dosya I/O gecikmesi playback'ten ayrıştırılır.
- **WSL2 OpenGL**: WSL2'de `LIBGL_ALWAYS_SOFTWARE=1` gerekir. Gerçek deneyde native Windows kullanılacak.
- **PsychoPy gui.Dlg vs DlgFromDict**: `gui.Dlg` field parsing'de sorun çıkarıyor, `gui.DlgFromDict` kullanılıyor.
- **Dichotic Listening**: `scripts/generate_dichotic_stimuli.py` uyumlu videolardan **48 kHz stereo PCM WAV** üretir (`assets/dichotic/{konuşmacı}/Left-{l}_Right-{r}.wav`). Çalışma anında dönüştürme yok. Kanal izolasyonu ölçüldü: kanallar arası sızıntı yok.
- **Videosuz ses sunumu**: `audio_only` ve `dichotic` bölümleri `MovieStim` **oluşturmaz**; `present_audio_only()` ekranda sabitleme haçı bırakır ve deneme sesin kendi süresi kadar sürer. Eskiden bu bölümler sesi 64×64/1 fps siyah bir videonun içinde taşıyordu ve deneme bitiş anı o akışın kare ızgarasına bağlıydı.
- **Noisy stimuli**: `scripts/generate_noisy_stimuli.py` mevcut, ancak çalışma anındaki karıştırma yolu (`stimuli.mix_noise_into_audio`) kullanılıyor. SNR hesabı şu an tüm dosya RMS'i üzerinden yapılıyor; konuşma-aktif RMS'e geçirilmesi Adım 2'de.
- **Admin panel**: `admin.py` PySide6 ile ayrı process olarak çalışır, PsychoPy ile aynı process'te çalıştırılamaz.

## Git Workflow
- `master`: stable releases
- `develop`: active development
- Feature branches from `develop`

## Don'ts
- Don't hardcode syllables, speaker names, or trial counts — everything from config
- Don't collect or store participant names — anonymous code only (KVKK)
- Don't score incongruent trials as right/wrong — store the raw response, derive the category
- Don't add a silent fallback for the audio backend — if ptb is unavailable, stop
- Don't call `random.shuffle` unseeded — the trial order must be reproducible from the stored seed
- Don't mix audio at runtime for noisy conditions — use pre-generated files. *(Current code still mixes at runtime with a cache; moving this offline is Adım 2.)*
- Don't mix PsychoPy and PySide6 in the same process — separate entry points
- Don't store experiment data in git (data/ is gitignored)
- Don't use PsychoPy Builder GUI — all code is hand-written Coder style
- Don't import PsychoPy from `mcgurk/config`, `mcgurk/db` or `mcgurk/stimuli` — CI has none, and a test enforces it
- Don't present anything from `assets/` in the new package — it is raw material; the prepared set under `stimuli/` is what a session uses
- Don't let stimulus preparation continue past a tolerance violation; there is no partially-prepared set worth having
- Don't back up SQLite by copying the file — use `VACUUM INTO`; a WAL-mode copy is silently inconsistent
- Don't commit inside a trial (§A.5) — `add_trial`/`add_response` defer, `finish_block` commits
- Don't add a module to `modules.*` without also adding it to `blocks.module`'s CHECK list and `design.py`
