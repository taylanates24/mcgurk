# McGurk Effect Experiment Platform

## Project Overview
TÜBİTAK-supported academic research project: "Behavioral Assessment of Audiovisual Speech Integration in Single-Sided Deafness (SSD)". A desktop experiment platform that presents audiovisual speech stimuli and collects participant responses to measure multisensory integration.

## Tech Stack
- **Language**: Python 3.10 (PsychoPy requires <3.12)
- **Experiment Engine**: PsychoPy — psychophysics-grade timing, video playback (MovieStim), response collection
- **Pre-experiment UI**: PsychoPy `gui.Dlg` dialogs for login/demographics and admin setup
- **Operator Panel**: Separate app (`mcgurk/panel/`, `python -m mcgurk.panel`) using **PyQt6** for launching sessions/checklist and browsing/exporting results. PyQt6 (not PySide6): PsychoPy's `psychopy.gui` supports only PyQt, and PyInstaller cannot bundle two Qt bindings, so the whole app standardises on PyQt6 (Adım 10c-ii)
- **Database**: SQLite (via Python stdlib `sqlite3`) + CSV export capability
- **Timing**: PsychoPy `core.Clock` (sub-millisecond precision) for reaction time
- **Noise Generation**: numpy + scipy for white noise / speech-shaped noise (pre-generated)
- **Config**: YAML (`pyyaml`) parsed into **Pydantic v2** models (`mcgurk/config`); unknown fields are rejected
- **Packaging**: PyInstaller for Windows executable distribution

## Architecture

### Entry points
1. **`main.py`** (= `python -m mcgurk.ui`) — the full session flow (Adım 8):
   participant login → resume prompt for an interrupted session → pre-session
   checklist confirm → practice → every module in `session.module_order` with its
   instruction screen and breaks → cross-hearing check (SSD) → end + backup. ESC
   opens an "are you sure?" confirm at any point.
2. **`python -m mcgurk.checklist`** — the operator's pre-session GREEN/RED pre-flight.
3. Admin / analysis (browse results, export) — Adım 9.

The six assessment modules are `mcgurk`, `avsr`, `tbw`, `oddball`, `dichotic`,
`gin` (documented under `mcgurk/modules/` below); `practice` and the
cross-hearing check are session-flow steps, not measurement modules.

### Legacy retired under legacy/ (Adım 8c-ii)

The Adım 0 `src/` tree — its own `main.py`, `admin.py`, `config.yaml`, the old
asset-generator scripts, and the McGurk/AV-congruent/A-only/V-only/Dichotic
"section" model it used — is frozen under `legacy/` and no longer run, tested or
type-checked (see `legacy/README.md`). `mcgurk/` is the single live platform.
Its config/db/stimuli layers stay PsychoPy-free; the two used to share a repo
root and separate config/database files — the schemas are incompatible.

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
│   ├── edit.py                  # panel-editable rep counts; ruamel round-trip write (Adım 11)
│   ├── selection.py             # operator's per-session choice: speaker + modules (Adım 12b)
│   ├── calibration.py           # 02_kalibrasyon.md JSON (Turkish keys → aliases)
│   ├── word_lists.py            # AVSR word-list schema + reader (Adım 5)
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
├── engine/                      # Adım 3 — A/V synchronisation core
│   ├── scheduling.py            # pure timing arithmetic, no PsychoPy
│   ├── audio.py                 # lateralisation, calibration trim, PTB gate
│   ├── window.py                # window, measured refresh, frame stats
│   ├── av_presenter.py          # TrialSpec -> presentation -> TimingRecord
│   ├── loopback.py              # level-2 jitter analysis (pure numpy)
│   └── psychopy_prefs.py        # must run before psychopy.sound is imported
├── modules/                     # Adım 4–8: mcgurk, avsr, tbw, oddball, dichotic, gin, practice, cross_hearing
│   ├── base.py                  # seeding, ordering, PlannedTrial — no PsychoPy
│   ├── practice.py              # congruent AV warm-up design (Adım 8b-ii) — no PsychoPy
│   ├── cross_hearing.py         # deaf-ear detection design + runner (Adım 8b-ii)
│   ├── mcgurk.py                # design + categorisation — no PsychoPy
│   ├── avsr.py                  # design + scoring + measures — no PsychoPy
│   ├── tbw.py                   # design + Gaussian fit + bootstrap — no PsychoPy
│   ├── oddball.py               # stream design + attribution + d' — no PsychoPy
│   ├── dichotic.py              # design + ear attribution + KAİ — no PsychoPy
│   ├── gin.py                   # segment design + gap attribution + threshold — no PsychoPy
│   ├── response.py              # option grid, keyboard, two RTs, free text
│   ├── block.py                 # shared trial loop + per-module TrialPolicy
│   └── stream.py                # continuous-stream loop (oddball + GIN)
├── analysis/                    # Adım 9 (empty)
├── ui/                          # Adım 8 — session flow (8b-i)
│   ├── login.py                 # gui.DlgFromDict -> Participant; build_participant is pure
│   ├── screens.py               # instruction / break / operator-checklist / quit-confirm screens
│   ├── runtime.py               # shared hardware open + start_session (also used by run_module)
│   ├── session.py               # orchestrator: checklist -> login -> practice -> modules -> cross-hearing -> end; installs the ESC confirmer
│   └── __main__.py              # python -m mcgurk.ui
├── checklist.py                 # Adım 8a — python -m mcgurk.checklist (pre-session GREEN/RED)
├── logging_setup.py
└── provenance.py                # git commit, OS, package versions
config/experiment.yaml           # new single source of truth (§G)
config/experiment.defaults.yaml  # read-only factory rep counts — "Varsayılana dön" (Adım 11)
stimuli/                         # prepared set + manifest.json (gitignored)
tools/verify_backup.py           # an untested backup is not a backup
tools/prepare_stimuli.py         # assets/ -> stimuli/
tools/verify_stimuli.py          # audit stimuli/ against manifest + design
tools/timing_selftest.py         # --level 1|2|3, --demo
tools/run_module.py              # run one module; --dry-run, --limit (dev harness)
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
stimuli/tones/tone_<hz>Hz.wav                           oddball tones, ramped
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

### Presentation engine (`mcgurk/engine/`, from Adım 3)

The timing arithmetic is deliberately PsychoPy-free (`scheduling.py`) so the
part that decides when a sound starts is testable in CI. Things that are easy
to get wrong:

- **The lead is per trial, not a constant.** `timing.lead_frames` is a floor.
  A negative SOA needs the flip target pushed far enough ahead that the audio
  can still start before it — TBW's −300 ms needs ~19 frames at 60 Hz, not 6.
  Above `max_lead_s` (1 s) the trial fails rather than quietly stretching.
- **`trials.actual_soa_ms` is the *experienced* SOA**: measured software
  difference **plus** the applied `system_av_offset_ms`. It is directly
  comparable with `nominal_soa_ms`; the raw difference is recoverable as
  `actual_soa_ms − sessions.system_av_offset_ms`. The difference is taken
  between the two acoustic **burst** times, not the file onsets.
- **PsychoPy 2026.1 removed `prefs.hardware['audioLatencyMode']`** from the
  preference spec. Latency class is now `SpeakerDevice(latencyClass=...)` and
  defaults to 1, so `timing.audio_latency_mode` is applied in
  `audio.open_speaker()`. Writing the old preference key is silently ignored.
- **`SoundPTB.statusDetailed['StartTime']` is not a measurement.** On WASAPI
  with no output timestamping it comes back bit-identical to the requested
  time. It is recorded, and `TimingRecord.audio_onset_reported` says what it
  is. The onset is verified physically or not at all (selftest level 2,
  photodiode).
- `TimeFailed` / `XRuns` from the same status dict *are* real: either one
  during a trial means the sound did not come out when it was asked for.
- **`MovieStim.frameIndex` always returns 0** in this version — use `pts`
  to find out which frame was actually shown. `movie.stop()` reloads the file
  from disk, so it must never be called between trials; `pause()`/`unload()`.
- The device's stream rate is checked against `audio.sample_rate`: PsychoPy
  resamples at load time otherwise, undoing the 48 kHz the set was prepared at.

### Assessment modules (`mcgurk/modules/`, from Adım 4–7)

The split follows the engine's: `base.py`, `mcgurk.py`, `avsr.py` and `tbw.py`
are PsychoPy-free, so the design, the categorisation, the scoring and the
psychometric fit are tested in CI. Things that are easy to get wrong:

- **The RNG seed is derived per module**, not shared. One stream would make
  McGurk's trial order depend on where it sits in `session.module_order`.
  `sessions.seed` still determines every order in the session.
- **`randomization: block_shuffle` means rounds, evenly spread.** A cell with
  fewer reps than the maximum is placed in rounds `floor(k·R/r)`, not in the
  first `r` rounds — otherwise every congruent control lands in the first half
  of the module.
- **`reps` is per cell**, so `reps: 10` on a pair with 2 noise × 2 ear
  conditions is 40 presentations. `config.trial_counts()` is the authority and
  a test asserts the generator matches it.
- **Noise instances are balanced within a cell** (3 over 10 reps → 4/3/3) and
  the one used is written to `trials.design_extra.noise_instance`. The noisy
  file is the clean token plus noise of the same length, so its burst time is
  the clean token's — the manifest records it only once.
- **`trials.design_extra.speaker_id` is per trial.** The config snapshot only
  pins the speaker down while `speaker_selection.strategy` is `fixed`;
  `plan_trials(..., speaker_id=...)` lets Adım 8 choose per participant. Since
  Adım 12b the operator's choice is applied to the config *before* the session
  starts (`config/selection.py`), so a chosen speaker **is** pinned in that
  session's snapshot and `select_speaker` simply reads it back.
- **Both RTs come from one measurement.** `rt_from_prompt_ms` is the keyboard's
  own clock, reset at the prompt flip; `rt_from_burst_ms` adds the known
  prompt−burst interval. Nothing is computed from `KeyPress.tDown`, but the
  disagreement between the two clocks is checked and logged.
- **Keys pressed before the prompt are discarded** (and counted in the log): a
  press during the video would otherwise be recorded with a near-zero RT.
- **A timeout writes no `responses` row.** `NONE` is derived from the row's
  absence; `categorise(None)` returns it too so QC and analysis agree.
- **A block is at most `session.break_every_n_trials` trials** — §A.5 puts the
  commit there, and one 140-trial block would risk the whole module.
- Categorisation order is fixed (auditory > visual > fusion > combination) and
  the config validation depends on it: a map listing the pair's own token is a
  rule that can never fire, so it is rejected at load.

**One loop, one policy per module (Adım 5).** `block.py` sequences fixation →
stimulus → response → database for every module that takes one forced choice;
what differs arrives as a `TrialPolicy` (which grid, what a response means,
whether there is a correct answer). `run_mcgurk`/`run_avsr`/`run_tbw` are thin
wrappers. Copying the loop per module is how two copies drift apart.

**Modül 2 — AVSR** (`avsr.py`) adds:

- **V-only is not crossed with noise or ear.** A silent video has no SNR and no
  side; those trials write `snr_db`, `noise_condition` and `ear` as **NULL** —
  *not applicable*, which is a different statement from "quiet, both ears".
  Crossing them would quadruple the cell for physically identical trials.
- **There is a correct answer here**, unlike Modül 1: `responses.is_correct` is
  written and `category` is left NULL. One fact in two columns is one fact that
  can disagree.
- **A timeout counts as incorrect**, not as a missing observation — excluding it
  would raise the accuracy of exactly the participants who could not answer in
  time. `Accuracy.n_missing` carries the timeout count alongside so a condition
  that is mostly timeouts is visible rather than merely low.
- **The V-only RT reference is the *visual* burst.** There is no acoustic one,
  and without a reference the mode could not be compared with the AV trials it
  is the baseline for; `TimingRecord.burst_onset_s` falls back to
  `video_onset + video_burst_s`.
- **`mode_questions` overrides the prompt per presentation mode.** "Ne
  duydunuz?" is the wrong question in V-only.
- **Word sets are data, not code** (§F.2). `config/word_lists/*.yaml` is read by
  the loader — the schema never touches the disk — and the items are attached to
  the `StimulusSet`. An enabled word set that is empty, missing from
  `stimulus_prep.tokens`, or missing from the manifest fails at **load**, each
  with its own message. `response_mode: open_set` raises
  `OpenSetNotImplemented`.

**Modül 3 — TBW** (`tbw.py`, Adım 6) adds:

- **The SOA is the whole manipulation** and it is produced on the audio side
  only (Adım 3). A negative SOA is paid for with presentation lead;
  `check_soa_is_schedulable()` does the engine's arithmetic at *design* time so
  an SOA grid the machine cannot present fails before the participant sits down,
  not mid-session.
- **There is no correct answer here either.** `responses.category` holds
  `SAME`/`DIFFERENT`, `is_correct` stays NULL, and the §A.10 trigger now refuses
  `tbw` as well (**schema version 3**). At +300 ms the streams really are
  asynchronous — but the measurement is whether they were *perceived* as one
  event, and scoring "different" as correct turns the width of the participant's
  window into an error rate.
- **A timeout is a missing observation, not a "different".** The opposite of the
  AVSR rule, and for the opposite reason: with no correct answer, filling a
  timeout in either direction moves the curve. `SOAPoint.n_missing` carries them.
- **The fit is a binomial MLE**, not least squares on the proportions: after
  timeouts are dropped the points carry different trial counts.
- **A fit that cannot be made is an error, never a number.** `FitError` covers
  fewer than three answered SOA points, a participant who never said "same", and
  — the one that looks like a result — a fitted `sigma` wider than half the
  tested SOA range, which is an extrapolation beyond the grid rather than a
  measured window.
- **`tbw_definition` travels with the width.** `fwhm` = 2.355 sigma, `sigma1` =
  2 sigma; both are used in the literature and a width without its definition
  cannot be compared with anything.
- **Bootstrap intervals are seeded from the session seed** (§A.11), so the same
  data always gives the same interval. Resamples that fail to fit are counted;
  if more than half fail, no interval is reported at all — one computed from the
  resamples that happened to fit is biased towards the shape that fits.
- `response_set` is what is on the screen and in what order, `response_labels`
  says which of the two means "simultaneous". The schema checks they name the
  same two strings: a mismatch would invert the curve, and an inverted curve
  still fits.

**Modül 4 — Oddball** (`oddball.py` + `stream.py`, Adım 7) is the first module
that is *not* a sequence of trials. It is a continuous stream of tones with a
jittered ISI, and it does not use `block.py` or `AVPresenter` at all:

- **A press is attributed, not collected.** Presses are timestamped as they
  arrive and assigned afterwards to the tone whose onset most recently preceded
  them. `modules.oddball.response_window_ms` then decides whether that press
  counts as a *response* to it. The config refuses a window that reaches past
  the shortest ISI, so a press can never belong to two tones.
- **The window is a design parameter, fixed before data collection.** Chosen
  afterwards it becomes a way of choosing the hit and false-alarm rates after
  seeing them. (Same rule as GIN's, still open with the danışman — §F.)
- **A press outside every window is still written**, against the tone it
  followed, with `category = OUTSIDE_WINDOW` and `is_correct` NULL. A
  participant pressing at random has to be visible in QC without their presses
  entering either rate.
- **A miss and a correct rejection produce no `responses` row.** Both are the
  absence of a press; they are derived from `v_trials_flat`, which keeps the
  trial visible through its LEFT JOIN.
- **`rt_from_prompt_ms` is NULL here** — a stream has no prompt. The RT lives
  in `rt_from_burst_ms`, measured from the tone's own onset.
- **Onsets are cumulative from one origin** and every tone is handed to PTB as
  an absolute time. A stream that re-referenced itself each tone would
  accumulate the scheduler's error over five minutes; measured drift over 300
  tones is under a millisecond.
- **The keyboard clock is reset once**, at the start of the run, and an RT is
  `press.rt + (reset_time − tone_onset)`. Resetting per tone would require the
  reset to happen *at* the onset, which no flip loop can promise.
- **Every target has its run of standards in front of it, the first one
  included.** A deviant presented before any standard is not a deviant. The
  placement is drawn uniformly from the legal sequences (stars and bars), not
  greedily: greedy placement pushes targets towards the end, where the free
  space accumulates.
- **d' and the criterion use the log-linear correction** (Hautus 1995) always,
  not only when a rate is 0 or 1 — a conditional correction is discontinuous
  exactly where an easy task puts most participants. One consequence: with 54
  targets against 246 standards, someone who presses at *every* tone lands at a
  small negative d' rather than zero, and it is the criterion that identifies
  them.
- **The tones are prepared offline** like everything else that is presented
  (`stimuli/tones/`, derived from `modules.oddball` rather than configured
  twice). The 10 ms raised-cosine ramp is the point: an un-ramped 50 ms tone
  can be told from another one by its click alone, which would make the task
  solvable without hearing a pitch.

**Modül 5 — Dikotik dinleme** (`dichotic.py`, Adım 7b) is back on `block.py` —
one forced choice, one `TrialPolicy`. It is drafted for the method document as
§6.5 (`docs/EK_DIKOTIK_DINLEME.docx`), still with the danışman. What is specific
to it:

- **The lateralisation is inside the file.** A dichotic WAV is stereo with a
  different token per channel, so `ear` is `both` and the engine hands it over
  untouched — `prepare_samples` refuses to route a stereo file anywhere, because
  routing it would destroy exactly what it was prepared for.
- **`trials.ear = 'both'`, not NULL.** The column says which ears received
  sound; *what* each one received is `design_extra.left_token` /
  `right_token`, which `v_trials_flat` exposes as columns. `audio_token` is NULL
  — there are two of them, and picking one would hide the other.
- **There is no correct answer** (§A.10, and the trigger already covered
  `dichotic` from Adım 1). `responses.category` holds `LEFT`/`RIGHT`/`OTHER`;
  reporting the right ear is a percept, not a success.
- **A timeout is a missing observation**, as in TBW and for the same reason:
  with no correct answer, assigning an unanswered trial to either ear moves the
  index. `EarAdvantage.n_missing` carries them.
- **`OTHER` is §6.5's intrusion rate** — a report matching neither presented
  syllable, whether the third syllable or the free-text option. It is in the
  denominator of the rates and outside the index, which names an ear.
- **KAİ = [(Sağ − Sol) / (Sağ + Sol)] × 100**, and it is `None` — never 0 —
  when neither ear was reported: 0 would read as "perfectly symmetrical" for a
  participant who in fact reported neither syllable.
- **The instruction is a free report.** `prompts.question` is singular ("Hangi
  heceyi duydunuz?") and never says that two syllables were presented; a
  directed-attention instruction would replace the measurement with a
  compliance check.
- **Both ears sit on one burst time** (Adım 2). Speaker 2's tokens differ by up
  to 248 ms naturally, and an ear advantage measured with asynchronous onsets
  would partly be an onset effect.
- In the SSD groups the presentation is functionally monotic, so the index
  measures the *absence* of competition rather than hemispheric lateralisation.
  Same numbers, different reading — §6.5 requires the asymmetry to be stated
  whenever the groups are compared.

**Modül 6 — GIN** (`gin.py` + `stream.py`, Adım 7c) is the second stream module,
sharing `stream.py`'s scheduling, screen-hold and health-reading with oddball
but keeping its own loop body — one trial is a six-second segment, not a tone.
It is drafted for the method document as §6.6 (`docs/EK_GIN.docx`), still with
the danışman. What is specific to it:

- **The unit of analysis is the gap, not the trial.** A segment holds up to
  three gaps and the threshold is computed per gap *duration*, so a hit has to
  name the gap it answered: `responses.event_index` indexes
  `design_extra.gap_onsets_s` (**schema version 4** — the first response field
  smaller than a trial). It is NULL in every other module, where the trial is
  the event.
- **The segments are read, not designed.** They were cut offline (Adım 2) and
  the manifest records where every gap landed; `gin.plan_trials` checks the set
  against the config's gap distribution and reads the positions from it, so what
  the participant hears and what the database says cannot disagree.
- **A press is attributed first and scored second** (the oddball rule). It
  belongs to the gap whose onset most recently preceded it, then
  `response_window_ms` decides whether it is a detection. The config keeps that
  window under `min_gap_separation_s`, so a press can never answer two gaps.
- **A press that followed no gap is a false alarm**, written with `event_index`
  NULL — unlike oddball's `OUTSIDE_WINDOW`, because in a stream of gaps a press
  outside every window answered nothing, and "pressed when there was nothing to
  hear" is the definition of a false alarm here. The prepared set holds one
  catch segment (zero gaps) that exists to measure exactly this.
- **A missed gap produces no row**, like an oddball miss; it is derived by
  comparing the gaps the trial carries with the `event_index` values returned.
- **The threshold is the shortest duration detected on ≥4 of its 6
  presentations**, `None` when none qualifies — never the longest gap, which
  would be a threshold the data never showed. It is always reported beside the
  false-alarm count (§"Yorumlama Sınırları"): someone who presses often detects
  short gaps by chance, and the threshold alone would flatter them.
- **GIN is monaural.** `ear_selection: good_ear` needs the ear passed in
  (`plan_trials(..., ear=...)`) — the good ear is the participant's, an Adım 8
  decision, and picking one silently would look like a measurement.
  `ear_selection: both` presents the segment list twice, once per ear, doubling
  the module. `trials.noise_condition` is NULL, not `quiet`: the stimulus *is*
  noise.
- **Segments are loaded one ahead**, not all at once: thirty six-second files
  are hundreds of MB, so the run reads each while the previous plays. The first
  is loaded before the clock starts — reading it after would eat the lead-in and
  the run would ask for an onset already past.

### Legacy Structure (Adım 0 — frozen under `legacy/`)

Retired in Adım 8c-ii and moved under `legacy/` (see `legacy/README.md`): the
paths below are now `legacy/main.py`, `legacy/admin.py`, `legacy/config.yaml`,
`legacy/src/…` and `legacy/scripts/generate_*`. Not run, tested or type-checked.
The tree below describes what is inside `legacy/` for reference only.
```
(repo root, Adım 0)
├── CLAUDE.md
├── config.yaml                  # legacy experiment parameters (src/ only)
├── requirements.txt
├── main.py                      # Experiment entry point (PsychoPy)
├── admin.py                     # Admin panel entry point (PySide6)
├── assets/                      # shared, not frozen — renamed in Adım 12a
│   ├── speaker_1_female/        # Vis-{x}_Aud-{y}.mp4 (was female_speaker_1)
│   ├── speaker_2_male/          # … through speaker_8_female
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
- Speaker folders follow pattern: `speaker_{id}_{gender}` (e.g., `speaker_1_female`, `speaker_2_male`) — the id comes first and equals `speaker_id`. The old `{gender}_speaker_{n}` numbered within a gender, so speaker id 5 would have lived in `female_speaker_2` (renamed in Adım 12a). Eight speakers are prepared; a session uses one
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
  in `response_set`; both are checked at load, as is the rule that a map may not
  list the pair's own visual or audio token (it could never fire).
- Response collection is config-driven too (Adım 4): `response_keys` maps 1:1
  onto `response_set` by position, `free_text_response` names the option that
  opens a text field, and `prompts.{question,other,timeout}` carries every
  string the participant reads. `prompts.other` is required exactly when
  `free_text_response` is set — a prompt for a screen that never opens is text
  nobody reads. `fixation_duration_ms` and `post_response_ms` are the trial
  structure. These live on `ResponseUIConfig`, shared by `mcgurk`, `avsr`,
  `tbw` and `dichotic`; AVSR adds `mode_questions` (per presentation mode), TBW
  adds `response_labels` (which of its two options means "simultaneous"),
  `tbw_definition` and `bootstrap_samples`/`bootstrap_ci`, and dichotic adds
  only `pairs` and `reps` — nothing is crossed with them. **Oddball and GIN have
  none of it**: no grid, no prompt, one `response_key`. Oddball adds
  `response_window_ms` (which press answers which tone), `lead_in_s`, and
  `ears` restricted to exactly one entry because `n_trials` is the total and
  the ear is not crossed. GIN adds `response_window_ms` (which press answers
  which gap — the schema keeps its upper bound under `min_gap_separation_s`),
  `lead_in_s`, and `ear_selection` (`good_ear` / `fixed` / `both`): the ear is
  the participant's, chosen in Adım 8, and `both` doubles the module.
- `modules.avsr.stimulus_sets[].list` points at a `config/word_lists/*.yaml`
  file, read by the loader (§F.2 — the recording session has not happened, so
  the shipped list is an empty template with `enabled: false`).
- **The repetition counts are editable from the panel** (Adım 11):
  `mcgurk/config/edit.py` exposes the per-module counts as `RepField`s and
  writes them back with **ruamel round-trip**, so the file's ~200 lines of
  explanation survive. What is easy to get wrong here:
  - **Writing is the only thing that uses ruamel**; reading stays on pyyaml.
    Re-dumping with pyyaml would delete every comment in the file.
  - **A write is validated and rolled back if it fails.** The new bytes go to
    disk, `load_config` runs, and a design the schema refuses (a zero rep, an
    oddball count too small to carry its targets) restores the previous bytes
    and raises. There is no partially-valid config worth keeping — the next
    session has to start.
  - **A no-op write is byte-identical, and a test asserts it.** That is what
    makes "only the edited key changes" true rather than intended; it is also
    why the `av_pairs` lines carry no alignment padding, which ruamel cannot
    reproduce inside a flow mapping.
  - **The factory values live in `config/experiment.defaults.yaml`**, not in
    code (§A.9) and not in `experiment.yaml` — from a source checkout that file
    *is* the one being edited, so it cannot be its own reference. A test pins
    its keys to `read_reps`'s, so a design change cannot leave the reset stale.
  - **`gin` is not editable.** Its trials are prepared segments and
    `reps_per_gap` is tied to the `4_of_6` threshold rule and the published
    norms; the tab shows it disabled, with the reason.
- `stimulus_prep.*`: everything `tools/prepare_stimuli.py` needs — the seed,
  the `speaker_id` → source-folder map, the token list, and the video/audio/
  burst/noise/GIN/tone parameters. The SNRs to prepare are **derived** from the
  enabled modules' `noise_conditions`, and the tone frequencies from
  `modules.oddball`, never listed a second time. Load-time checks: every
  `modules.*.speaker_id` names a declared speaker, and every token the design
  uses is in `stimulus_prep.tokens`. `stimulus_prep.tones.level_dbfs` is the
  one thing about a tone that is not design — the level it is written at.

## Data Model (new package — data/mcgurk.sqlite, schema version 4)
Six tables + `v_trials_flat`. See `mcgurk/db/schema.sql`.
- `participants` — anonymous code, group (`SSD_R`/`SSD_L`/`CTRL`), age, sex,
  deprivation_months, PTA left/right, postlingual
- `calibrations` — parsed 02_kalibrasyon.md output plus the verbatim file
- `sessions` — seed, **config snapshot**, git commit, PsychoPy/Python version,
  OS, audio backend, measured refresh, `system_av_offset_ms`, status
- `blocks` — module, index, planned trial count, status
- `trials` — shared design columns + realised timing; module-specific fields in
  `design_extra` (JSON), validated by `mcgurk/db/design.py`. `mcgurk`, `avsr`,
  `tbw` and `dichotic` trials carry `speaker_id` (required) and
  `noise_instance`; `avsr` adds `stimulus_type` and `item`; `dichotic` adds
  `left_token` and `right_token`; `oddball` carries `tone_type`, `tone_hz` and
  the nominal `isi_ms`; `gin` carries `segment_index` and the `gap_onsets_s` /
  `gap_durations_ms` lists. `v_trials_flat` exposes `speaker_id`,
  `noise_instance`, `dichotic_left_token`, `dichotic_right_token`,
  `gin_segment_index`, `gin_gap_onsets_s`, `gin_gap_durations_ms`,
  `avsr_item` and `oddball_tone_type` as columns (`stimulus_type` and `isi_ms`
  are only in the JSON — adding either to the VIEW is a schema-version bump,
  and the occasion for that is the word set arriving; the realised interval is
  recoverable by differencing `audio_onset_s`).
- `responses` — **0..n per trial**: none on timeout or on an oddball tone the
  participant did not answer, several for a GIN segment or a tone pressed twice.
  `event_index` (schema version 4) names which event *inside* the trial a
  response answers — the gap's index for GIN, NULL everywhere else (there the
  trial is the event).
- A trigger refuses `is_correct` on `mcgurk`/`dichotic`/`tbw` trials (§A.10)
- A module may write several blocks; use `db.next_block_index(session_id)`
  rather than counting in the caller.

## Legacy Data Model (src/, data/mcgurk.db)
### Participants Table
- participant_id, **participant_code** (anonymous — never a name, KVKK), age, gender, group (SSD-right, SSD-left, control), created_at, notes

### Trials Table
- trial_id, participant_id, session_id, section_type, speaker, visual_syllable, audio_syllable, noise_condition, snr_db, participant_response, correct_answer, is_correct (**NULL for mcgurk/dichotic**), rt_from_video_end_ms, rt_from_options_shown_ms, ear_side (for dichotic), trial_order, timestamp

### Sessions Table
- session_id, participant_id, sections_run, speaker, **seed**, **status** (running/completed/aborted), started_at, completed_at, admin_notes

## Key Design Decisions
1. **Experiment accuracy > UI aesthetics** — PsychoPy chosen for psychophysics-grade timing
2. **Two separate apps**: PsychoPy for the experiment (`mcgurk.ui`), **PyQt6** for the operator panel (`mcgurk.panel`) — separate processes avoid event-loop conflicts. Both use the same Qt binding (PyQt6), which is what PsychoPy's dialogs need
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
- Run the experiment: `python main.py` (= `python -m mcgurk.ui`; full options below. WSL2'de `LIBGL_ALWAYS_SOFTWARE=1` prefix gerekebilir)
- Admin / analysis: Adım 9 (the Adım 0 `admin.py` is retired under `legacy/`)
- Monitor setup (ilk kurulumda bir kez): `python scripts/setup_monitor.py`
- Validate config + design cost: `python -m mcgurk.config`
- Pre-session checklist (operator, Adım 8): `python -m mcgurk.checklist [--no-hardware]` — YEŞİL/KIRMIZI ön-uçuş; any RED blocks a `data_collection` session (exit 1)
- Timing self-test: `python tools/timing_selftest.py --level 1` / `--demo`
- Inspect a module's design (no hardware): `python tools/run_module.py --module mcgurk|avsr|tbw|oddball|dichotic|gin --dry-run` (gin needs `--ear left|right`)
- Run a module: `python tools/run_module.py --module mcgurk|avsr|tbw|oddball|dichotic|gin [--limit N] [--seed N]` (gin needs `--ear left|right`)
- Run a full session (Adım 8, new package): `python -m mcgurk.ui [--limit N] [--db PATH] [--device NAME] [--new-session] [--speaker N] [--modules mcgurk,dichotic] [--no-practice] [--no-cross-hearing]` — login → (resume prompt if a half-finished session exists) → checklist confirm → practice → instructions → modules → breaks → cross-hearing (SSD) → end. ESC opens an "are you sure?" confirm (Adım 8b-ii); confirmed → `aborted` + backup. Resume (Adım 8c-i) reuses the same session/seed/snapshot and skips completed modules; `--new-session` forces a fresh one.
- Verify cross-hearing lateralisation on its own (Adım 8b-ii): `python tools/run_cross_hearing.py --ear left|right` — `--ear` is the deaf ear; the tone routes there, the other channel is silent, half the trials are catch. Runs just this check so the side can be confirmed without a full session.
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
- **Operatör paneli**: `mcgurk/panel/` **PyQt6** ile ayrı process olarak çalışır, PsychoPy ile aynı process'te çalıştırılamaz. Deneyi/checklist'i subprocess (`--run`) olarak açar (Adım 10). (Eski `legacy/admin.py` PySide6'ydı.) İki sekme: **Panel** (Adım 10) ve **Ayarlar** (Adım 11 — tekrar sayıları).
- **Modal `QMessageBox` offscreen testte de bloke eder.** Qt'nin `offscreen` platform eklentisi pencereyi çizmez ama event loop'u yine döndürür, yani `QMessageBox.critical(...)` bir yanıt bekleyerek asılır — test kırmızıya dönmez, süresiz takılır (Adım 11b'de 120 sn'lik timeout olarak bulundu). Bir handler'ın diyalog yolunu test edecekseniz `critical`/`question`/`information`'ı monkeypatch'leyin.

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
- Don't run the PyQt6 operator panel in the same process as the PsychoPy experiment — separate entry points/processes (the panel launches the experiment via `--run`). Both use PyQt6, but their event loops must not share a process
- Don't store experiment data in git (data/ is gitignored)
- Don't use PsychoPy Builder GUI — all code is hand-written Coder style
- Don't import PsychoPy from `mcgurk/config`, `mcgurk/db` or `mcgurk/stimuli` — CI has none, and a test enforces it
- Don't put timing arithmetic in `av_presenter.py` — it belongs in `scheduling.py`, where it can be tested without hardware
- Don't call `configure_psychopy()` after anything has imported `psychopy.sound` — backend selection is frozen at import
- Don't treat a scheduled audio time as a measured onset; only a physical measurement verifies it
- Don't present anything from `assets/` in the new package — it is raw material; the prepared set under `stimuli/` is what a session uses
- Don't let stimulus preparation continue past a tolerance violation; there is no partially-prepared set worth having
- Don't back up SQLite by copying the file — use `VACUUM INTO`; a WAL-mode copy is silently inconsistent
- Don't commit inside a trial (§A.5) — `add_trial`/`add_response` defer, `finish_block` commits
- Don't add a module to `modules.*` without also adding it to `blocks.module`'s CHECK list and `design.py`
- Don't import PsychoPy at module level in `modules/base.py`, `modules/mcgurk.py`, `modules/avsr.py`, `modules/tbw.py`, `modules/oddball.py`, `modules/dichotic.py` or `modules/gin.py` — the design, the categorisation, the scoring, the psychometric fit, the signal-detection measures and the threshold are CI-tested, and a test enforces it
- Don't give the participant correctness feedback in any module — the McGurk effect must not be taught mid-session (demand characteristics)
- Don't derive a category from `free_text`; the participant declined the options that were on screen
- Don't put a character outside cp1254 in a printed, logged or raised string (`−`, `≠`, `→`) — the Turkish Windows console raises `UnicodeEncodeError` instead of degrading, so the traceback replaces the message. Docstrings and comments are fine; `tests/mcgurk/test_console_encoding.py` enforces the rest
- Don't copy `block.py`'s loop into a new module — give it a `TrialPolicy`; two copies of a trial loop drift apart
- Don't cross AVSR's V-only cells with noise or ear, and don't write "quiet"/"both" on them — NULL means *not applicable*
- Don't drop AVSR timeouts from an accuracy figure — they are incorrect answers, and excluding them flatters the participants who ran out of time
- Don't score a TBW simultaneity judgement — there is no correct answer at any SOA, and the database refuses `is_correct` on `tbw` trials
- Don't count a TBW timeout as "different" — with no correct answer, filling it in either direction moves the curve; it is a missing observation
- Don't report a fitted window wider than half the tested SOA range — beyond that the grid does not constrain sigma and the number is an extrapolation, not a measurement
- Don't decide an oddball press's response window inside the trial loop — it is a config parameter, fixed before data collection, and attribution has to stay testable without hardware
- Don't drop an oddball press that fell outside every window — record it with `category = OUTSIDE_WINDOW` and no correctness; a participant pressing at random must be visible without being counted as a hit or a false alarm
- Don't write a `responses` row for an oddball miss or correct rejection — both are the absence of a press, and inventing a row puts the analyst's reading into the data
- Don't schedule an oddball tone relative to the previous *realised* onset — the whole stream comes off one origin, or the scheduler's error accumulates over five minutes
- Don't lateralise a dichotic file — it is stereo and already carries a different token per ear; `ear` is `both` and the engine refuses anything else
- Don't count a dichotic timeout as a report — with no correct answer, assigning it to either ear moves the laterality index; it is a missing observation
- Don't report a laterality index of 0 when neither ear was reported — the index is undefined there, and 0 reads as "perfectly symmetrical"
- Don't tell the dichotic participant that two syllables are presented, or ask them to attend to one ear — the free report *is* the measurement
- Don't record a GIN hit without its `event_index` — the threshold is computed per gap duration, and a detection that does not name its gap cannot enter it
- Don't record a GIN press outside every gap's window as `OUTSIDE_WINDOW` — unlike oddball, it answered no gap at all, so it is a plain false alarm with `event_index` NULL
- Don't present GIN to a deaf ear or diotically — it is monaural; `ear_selection: good_ear` needs the ear passed in from the session flow, and the deaf ear measures nothing
- Don't report a GIN threshold wider than the tested range as a number — if no duration meets the criterion it is `None` ("ulaşılamadı"), not the longest gap
- Don't read a GIN threshold without the false-alarm count beside it — a participant who presses often catches short gaps by chance and reads as more acute than they are
- Don't rewrite `config/experiment.yaml` by dumping it with pyyaml — the file is mostly explanation, and a dump deletes all of it; the writer is `mcgurk/config/edit.py`'s ruamel round trip
- Don't leave an unvalidated config on disk — write, `load_config`, and restore the previous bytes if it fails; the operator's next session has to start
- Don't hard-code the factory repetition counts for "Varsayılana dön" — they are design (§A.9) and live in `config/experiment.defaults.yaml`, whose keys a test pins to `read_reps`'s
- Don't expose GIN's `reps_per_gap` as an editable count — it is tied to the `4_of_6` threshold rule and the published norms, and the segments come from the prepared set
- Don't buffer every GIN segment up front like oddball's tones — thirty six-second files are hundreds of MB; load one ahead, and load the first before the clock starts
