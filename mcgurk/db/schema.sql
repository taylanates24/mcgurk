-- McGurk / SSD platform database schema (version 1).
--
-- Design notes:
--   * Six tables plus a flat VIEW for analysis (steps.md Adım 1).
--   * `trials` holds the design fields that at least two modules share plus
--     the realised timing.  Module-specific fields go into `design_extra`
--     (JSON), validated by mcgurk/db/design.py before insertion.  A 12-month
--     study cannot afford a schema migration every time a module is added.
--   * `responses` is 0..n per trial: a timeout produces no row, and a GIN
--     segment or an oddball block can produce several.
--   * The trigger at the bottom enforces §A.10 at the storage layer.

CREATE TABLE IF NOT EXISTS participants (
    participant_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Anonymous code only.  No name, surname or date of birth (§A.6, KVKK).
    participant_code    TEXT    NOT NULL UNIQUE,
    group_code          TEXT    NOT NULL CHECK (group_code IN ('SSD_R', 'SSD_L', 'CTRL')),
    age                 INTEGER NOT NULL CHECK (age BETWEEN 18 AND 60),
    sex                 TEXT    NOT NULL CHECK (sex IN ('F', 'M', 'OTHER', 'UNDISCLOSED')),
    -- Deafness history.  NULL for controls.
    deprivation_months  INTEGER CHECK (deprivation_months IS NULL OR deprivation_months >= 0),
    pta_right_db        REAL,
    pta_left_db         REAL,
    postlingual         INTEGER CHECK (postlingual IN (0, 1)),
    notes               TEXT    NOT NULL DEFAULT '',
    created_at          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS calibrations (
    calibration_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    measured_on         TEXT NOT NULL,
    source_file         TEXT NOT NULL,
    k_left_db           REAL NOT NULL,
    k_right_db          REAL NOT NULL,
    k_mean_db           REAL NOT NULL,
    channel_difference_db REAL NOT NULL,
    target_spl_db       REAL NOT NULL,
    required_dbfs       REAL NOT NULL,
    trim_left_db        REAL NOT NULL,
    trim_right_db       REAL NOT NULL,
    -- Verbatim file contents, so the session can be audited even if the
    -- calibration file is later overwritten.
    raw_json            TEXT NOT NULL,
    imported_at         TEXT NOT NULL,
    UNIQUE (measured_on, source_file)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id      INTEGER NOT NULL REFERENCES participants(participant_id),
    calibration_id      INTEGER REFERENCES calibrations(calibration_id),
    -- §A.11: the trial order is reproducible from this seed.
    seed                INTEGER NOT NULL,
    -- The config exactly as loaded, so a later config change cannot make it
    -- ambiguous which design produced this data (steps.md §G).
    config_snapshot     TEXT    NOT NULL,
    config_mode         TEXT    NOT NULL CHECK (config_mode IN ('development', 'data_collection')),
    app_version         TEXT,
    git_commit          TEXT,
    psychopy_version    TEXT,
    python_version      TEXT    NOT NULL,
    os_name             TEXT    NOT NULL,
    audio_backend       TEXT,
    audio_device        TEXT,
    measured_refresh_hz REAL,
    system_av_offset_ms REAL,
    status              TEXT    NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'completed', 'aborted')),
    operator_notes      TEXT    NOT NULL DEFAULT '',
    started_at          TEXT    NOT NULL,
    completed_at        TEXT
);

CREATE TABLE IF NOT EXISTS blocks (
    block_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(session_id),
    module              TEXT    NOT NULL CHECK (module IN (
                            'practice', 'mcgurk', 'avsr', 'tbw', 'oddball',
                            'dichotic', 'gin', 'cross_hearing')),
    block_index         INTEGER NOT NULL,
    label               TEXT    NOT NULL DEFAULT '',
    n_trials_planned    INTEGER NOT NULL CHECK (n_trials_planned >= 0),
    status              TEXT    NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'completed', 'aborted')),
    started_at          TEXT    NOT NULL,
    completed_at        TEXT,
    UNIQUE (session_id, block_index)
);

CREATE TABLE IF NOT EXISTS trials (
    trial_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id            INTEGER NOT NULL REFERENCES blocks(block_id),
    trial_index         INTEGER NOT NULL,

    -- ---- design ----
    module              TEXT    NOT NULL,
    condition_label     TEXT    NOT NULL DEFAULT '',
    visual_token        TEXT,
    audio_token         TEXT,
    ear                 TEXT    CHECK (ear IS NULL OR ear IN ('left', 'right', 'both')),
    snr_db              REAL,
    noise_condition     TEXT,
    nominal_soa_ms      REAL,
    presentation_mode   TEXT    CHECK (presentation_mode IS NULL
                                       OR presentation_mode IN ('A', 'V', 'AV')),
    -- Module-specific design fields as JSON; see mcgurk/db/design.py.
    design_extra        TEXT    NOT NULL DEFAULT '{}',

    -- ---- realised timing (§A.4), written after presentation ----
    video_onset_s       REAL,
    audio_onset_s       REAL,
    actual_soa_ms       REAL,
    dropped_frames      INTEGER,
    max_frame_interval_ms REAL,
    presented_at        TEXT,

    UNIQUE (block_id, trial_index)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trial_id            INTEGER NOT NULL REFERENCES trials(trial_id),
    -- 0 for the single response of a forced-choice trial; increments for the
    -- multiple key presses a GIN segment or an oddball run can produce.
    response_index      INTEGER NOT NULL DEFAULT 0,
    raw_response        TEXT,
    free_text           TEXT,
    -- Derived category.  The vocabulary is module-specific and deliberately
    -- unconstrained here: the categorisation maps live in the config (§A.9)
    -- and a CHECK would have to be migrated every time one changes.
    category            TEXT,
    -- NULL wherever there is no correct answer; enforced by the trigger below.
    is_correct          INTEGER CHECK (is_correct IS NULL OR is_correct IN (0, 1)),
    rt_from_burst_ms    REAL,
    rt_from_prompt_ms   REAL,
    input_device        TEXT    NOT NULL DEFAULT 'keyboard'
                        CHECK (input_device IN ('keyboard', 'mouse')),
    recorded_at         TEXT    NOT NULL,
    UNIQUE (trial_id, response_index)
);

CREATE INDEX IF NOT EXISTS idx_sessions_participant ON sessions(participant_id);
CREATE INDEX IF NOT EXISTS idx_blocks_session       ON blocks(session_id);
CREATE INDEX IF NOT EXISTS idx_trials_block         ON trials(block_id);
CREATE INDEX IF NOT EXISTS idx_trials_module        ON trials(module);
CREATE INDEX IF NOT EXISTS idx_responses_trial      ON responses(trial_id);

-- §A.10: an incongruent trial has no correct answer.  Scoring a McGurk or
-- dichotic response against the audio token is a category error, so the
-- database refuses it outright rather than trusting every future caller.
CREATE TRIGGER IF NOT EXISTS trg_responses_no_correctness_on_insert
BEFORE INSERT ON responses
FOR EACH ROW
WHEN NEW.is_correct IS NOT NULL
 AND (SELECT module FROM trials WHERE trial_id = NEW.trial_id)
     IN ('mcgurk', 'dichotic')
BEGIN
    SELECT RAISE(ABORT,
        'is_correct must be NULL for mcgurk/dichotic trials (steps.md §A.10)');
END;

CREATE TRIGGER IF NOT EXISTS trg_responses_no_correctness_on_update
BEFORE UPDATE OF is_correct ON responses
FOR EACH ROW
WHEN NEW.is_correct IS NOT NULL
 AND (SELECT module FROM trials WHERE trial_id = NEW.trial_id)
     IN ('mcgurk', 'dichotic')
BEGIN
    SELECT RAISE(ABORT,
        'is_correct must be NULL for mcgurk/dichotic trials (steps.md §A.10)');
END;

-- Flat table for analysis.  LEFT JOIN on responses so a timed-out trial (no
-- response row) still appears — dropping it would silently bias the data.
CREATE VIEW IF NOT EXISTS v_trials_flat AS
SELECT
    p.participant_code,
    p.group_code,
    p.age,
    p.sex,
    p.deprivation_months,
    p.pta_left_db,
    p.pta_right_db,
    p.postlingual,

    s.session_id,
    s.seed,
    s.status              AS session_status,
    s.config_mode,
    s.started_at          AS session_started_at,
    s.system_av_offset_ms,
    s.measured_refresh_hz,
    s.audio_backend,
    s.git_commit,

    b.block_id,
    b.block_index,
    b.label               AS block_label,

    t.trial_id,
    t.trial_index,
    t.module,
    t.condition_label,
    t.visual_token,
    t.audio_token,
    t.ear,
    t.snr_db,
    t.noise_condition,
    t.presentation_mode,
    t.nominal_soa_ms,
    t.actual_soa_ms,
    t.video_onset_s,
    t.audio_onset_s,
    t.dropped_frames,
    t.max_frame_interval_ms,

    json_extract(t.design_extra, '$.left_token')       AS dichotic_left_token,
    json_extract(t.design_extra, '$.right_token')      AS dichotic_right_token,
    json_extract(t.design_extra, '$.gap_onsets_s')     AS gin_gap_onsets_s,
    json_extract(t.design_extra, '$.gap_durations_ms') AS gin_gap_durations_ms,
    json_extract(t.design_extra, '$.tone_type')        AS oddball_tone_type,
    json_extract(t.design_extra, '$.item')             AS avsr_item,

    r.response_id,
    r.response_index,
    r.raw_response,
    r.free_text,
    r.category,
    r.is_correct,
    r.rt_from_burst_ms,
    r.rt_from_prompt_ms,
    r.input_device
FROM trials t
JOIN blocks       b ON b.block_id = t.block_id
JOIN sessions     s ON s.session_id = b.session_id
JOIN participants p ON p.participant_id = s.participant_id
LEFT JOIN responses r ON r.trial_id = t.trial_id;
