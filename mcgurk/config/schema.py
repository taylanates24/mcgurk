"""Pydantic models for ``config/experiment.yaml`` — the single source of truth.

Every model forbids unknown fields (steps.md §G).  A misspelled parameter must
fail loudly: silently falling back to a default would change the experimental
design without anyone noticing, and the data would already be collected by the
time it surfaced.

Filesystem checks live in :mod:`mcgurk.config.loader`, not here — a schema that
touches the disk cannot be unit tested without building a directory tree.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["development", "data_collection"]
Ear = Literal["left", "right", "both"]
PresentationMode = Literal["A", "V", "AV"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

#: Modules that may appear in ``session.module_order``.  ``practice`` is a
#: warm-up block rather than a measurement, so it has no ``modules.*`` entry.
ModuleName = Literal[
    "practice", "mcgurk", "avsr", "tbw", "oddball", "dichotic", "gin"
]

#: Modules whose trials have no correct answer (§A.10).  Mirrored by a database
#: trigger in ``db/schema.sql`` so the rule survives a coding mistake.
NO_CORRECT_ANSWER_MODULES = frozenset({"mcgurk", "dichotic"})

_THRESHOLD_CRITERION_RE = re.compile(r"^(\d+)_of_(\d+)$")


class StrictModel(BaseModel):
    """Base model: unknown fields are an error, assignments are validated."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# --------------------------------------------------------------- top sections


class ExperimentMeta(StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    mode: Mode


class Paths(StrictModel):
    """Directories, relative to the project root unless absolute."""

    stimuli: Path
    data: Path
    logs: Path
    backups: Path


class LoggingConfig(StrictModel):
    console_level: LogLevel = "INFO"
    file_level: LogLevel = "DEBUG"


class DatabaseConfig(StrictModel):
    path: Path
    #: Every session close writes a backup, aborted sessions included
    #: (steps.md Adım 1).  Only turn this off for throwaway development runs.
    backup_on_session_end: bool = True


class TimingConfig(StrictModel):
    #: Photodiode measurement, ``01_av_gecikme_olcumu.md``.  Null until the
    #: whole code base is finished; ``data_collection`` then requires it.
    system_av_offset_ms: float | None = None
    measured_on: date | None = None
    audio_latency_mode: int = Field(default=3, ge=0, le=4)
    lead_frames: int = Field(default=6, ge=1)
    dropped_frame_tolerance: float = Field(default=1.5, gt=1.0)

    @model_validator(mode="after")
    def _offset_needs_a_date(self) -> TimingConfig:
        if self.system_av_offset_ms is not None and self.measured_on is None:
            raise ValueError(
                "system_av_offset_ms doluysa measured_on da dolu olmalı — "
                "tarihi olmayan bir gecikme ölçümü doğrulanamaz"
            )
        return self


class DisplayConfig(StrictModel):
    fullscreen: bool
    screen: int = Field(default=0, ge=0)
    size: tuple[int, int]
    background: str = "black"
    video_position: tuple[float, float] = (0.0, 0.0)
    expected_refresh_hz: float = Field(default=60.0, gt=0)

    @model_validator(mode="after")
    def _visual_stimulus_stays_centred(self) -> DisplayConfig:
        # §A.13 — the method document requires the visual stimulus at the
        # centre of the screen.  Making this configurable but unenforced would
        # be an invitation to break it.
        if self.video_position != (0.0, 0.0):
            raise ValueError(
                "display.video_position [0, 0] olmalı — görsel uyaran merkezde "
                "sunulur (§A.13)"
            )
        if self.size[0] <= 0 or self.size[1] <= 0:
            raise ValueError("display.size pozitif olmalı")
        return self


class AudioConfig(StrictModel):
    sample_rate: int = Field(default=48000, gt=0)
    target_spl_db: float = Field(gt=0)
    #: Output of ``02_kalibrasyon.md``.  Null until calibration is done;
    #: ``data_collection`` then requires an existing, readable file.
    calibration_file: Path | None = None
    #: Exact output device name.  Null lets the operator pick at run time,
    #: which is fine in development but not during data collection.
    device: str | None = None


class SessionConfig(StrictModel):
    module_order: list[ModuleName] = Field(min_length=1)
    break_every_n_trials: int = Field(gt=0)
    break_duration_s: float = Field(ge=0)
    practice_trials: int = Field(ge=0)

    @model_validator(mode="after")
    def _no_duplicate_modules(self) -> SessionConfig:
        seen = [m for m in self.module_order if self.module_order.count(m) > 1]
        if seen:
            raise ValueError(
                f"session.module_order tekrarlı modül içeriyor: {sorted(set(seen))}"
            )
        return self


# ------------------------------------------------------------------- modules


class ModuleBase(StrictModel):
    enabled: bool = True
    #: Used only for the duration estimate printed at config load.  It is not
    #: a timing parameter — nothing in the presentation path reads it.
    estimated_trial_duration_s: float = Field(gt=0)

    def total_trials(self) -> int:
        """Number of trials this module generates from the current design."""
        raise NotImplementedError

    def estimated_duration_s(self) -> float:
        return self.total_trials() * self.estimated_trial_duration_s


class AVPair(StrictModel):
    visual: str = Field(min_length=1)
    audio: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reps: int = Field(gt=0)


class McGurkConfig(ModuleBase):
    speaker_id: int = Field(ge=1)
    av_pairs: list[AVPair] = Field(min_length=1)
    #: ``null`` = quiet, a number = SNR in dB.
    noise_conditions: list[float | None] = Field(min_length=1)
    ears: list[Ear] = Field(min_length=1)
    response_set: list[str] = Field(min_length=2)
    response_timeout_s: float = Field(gt=0)
    randomization: Literal["block_shuffle", "full_shuffle"]
    #: "visual|audio" -> accepted responses.  Kept out of the code (§A.9) so
    #: the categorisation can be revised without touching the module.
    fusion_map: dict[str, list[str]] = Field(default_factory=dict)
    combination_map: dict[str, list[str]] = Field(default_factory=dict)

    def total_trials(self) -> int:
        return (
            sum(pair.reps for pair in self.av_pairs)
            * len(self.noise_conditions)
            * len(self.ears)
        )

    @model_validator(mode="after")
    def _maps_match_the_design(self) -> McGurkConfig:
        responses = {r.casefold() for r in self.response_set}
        pairs = {f"{p.visual}|{p.audio}" for p in self.av_pairs}

        for name, mapping in (
            ("fusion_map", self.fusion_map),
            ("combination_map", self.combination_map),
        ):
            for key, values in mapping.items():
                if key not in pairs:
                    raise ValueError(
                        f"modules.mcgurk.{name} anahtarı '{key}' av_pairs "
                        f"içinde yok. Tanımlı çiftler: {sorted(pairs)}"
                    )
                unknown = [v for v in values if v.casefold() not in responses]
                if unknown:
                    raise ValueError(
                        f"modules.mcgurk.{name}['{key}'] response_set'te "
                        f"olmayan yanıt içeriyor: {unknown}"
                    )
        return self

    @model_validator(mode="after")
    def _duplicate_noise_or_ears(self) -> McGurkConfig:
        if len(set(self.ears)) != len(self.ears):
            raise ValueError("modules.mcgurk.ears tekrarlı değer içeriyor")
        keys = [("null" if n is None else n) for n in self.noise_conditions]
        if len(set(keys)) != len(keys):
            raise ValueError("modules.mcgurk.noise_conditions tekrarlı değer içeriyor")
        return self


class StimulusSet(StrictModel):
    """One AVSR stimulus set: syllables today, words once they are recorded."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["syllable", "word"]
    tokens: list[str] | None = None
    #: ``list:`` in YAML — renamed here because ``list`` shadows the builtin.
    word_list: Path | None = Field(default=None, alias="list")
    reps: int = Field(gt=0)
    enabled: bool

    @model_validator(mode="after")
    def _shape_matches_type(self) -> StimulusSet:
        if self.type == "syllable":
            if not self.tokens:
                raise ValueError("type: syllable için tokens gerekli")
            if self.word_list is not None:
                raise ValueError("type: syllable ile 'list' birlikte kullanılamaz")
        else:
            if self.word_list is None:
                raise ValueError("type: word için 'list' gerekli")
            if self.tokens:
                raise ValueError("type: word ile 'tokens' birlikte kullanılamaz")
        return self

    def n_items(self) -> int:
        """How many distinct items this set contributes.

        Word lists are not read here.  Loading them is Adım 5's job (steps.md
        §C Adım 5) and the recording session has not happened yet (§F.2), so an
        enabled word set is reported as an error rather than guessed at.
        """
        if self.type == "syllable":
            return len(self.tokens or [])
        raise ValueError(
            f"Kelime listesi ({self.word_list}) henüz yüklenemiyor — kelime seti "
            "desteği Adım 5'te geliyor (§F.2). Şimdilik 'enabled: false' bırakın."
        )


class AVSRConfig(ModuleBase):
    speaker_id: int = Field(ge=1)
    stimulus_sets: list[StimulusSet] = Field(min_length=1)
    presentation_modes: list[PresentationMode] = Field(min_length=1)
    noise_conditions: list[float | None] = Field(min_length=1)
    ears: list[Ear] = Field(min_length=1)
    response_mode: Literal["closed_set", "open_set"]
    response_timeout_s: float = Field(gt=0)

    def total_trials(self) -> int:
        total = 0
        for stimulus_set in self.stimulus_sets:
            if not stimulus_set.enabled:
                continue
            items = stimulus_set.n_items() * stimulus_set.reps
            for mode in self.presentation_modes:
                if mode == "V":
                    # V-only carries no audio, so crossing it with noise level
                    # and ear is meaningless — and would inflate the session by
                    # a factor of four for nothing (steps.md §C Adım 5).
                    total += items
                else:
                    total += items * len(self.noise_conditions) * len(self.ears)
        return total

    @model_validator(mode="after")
    def _at_least_one_enabled_set(self) -> AVSRConfig:
        if self.enabled and not any(s.enabled for s in self.stimulus_sets):
            raise ValueError(
                "modules.avsr etkin ama hiçbir stimulus_set etkin değil"
            )
        if len(set(self.presentation_modes)) != len(self.presentation_modes):
            raise ValueError("modules.avsr.presentation_modes tekrarlı değer içeriyor")
        return self


class TBWStimulus(StrictModel):
    visual: str = Field(min_length=1)
    audio: str = Field(min_length=1)


class TBWConfig(ModuleBase):
    speaker_id: int = Field(ge=1)
    stimulus: TBWStimulus
    soa_values_ms: list[float] = Field(min_length=3)
    reps_per_soa: int = Field(gt=0)
    ears: list[Ear] = Field(min_length=1)
    #: Written into the QC report — the literature uses both definitions and a
    #: TBW figure is meaningless without saying which one produced it.
    tbw_definition: Literal["fwhm", "sigma1"]
    response_labels: dict[str, str]
    response_timeout_s: float = Field(gt=0)

    def total_trials(self) -> int:
        return len(self.soa_values_ms) * self.reps_per_soa * len(self.ears)

    @model_validator(mode="after")
    def _soa_and_labels(self) -> TBWConfig:
        if len(set(self.soa_values_ms)) != len(self.soa_values_ms):
            raise ValueError("modules.tbw.soa_values_ms tekrarlı değer içeriyor")
        if sorted(self.soa_values_ms) != self.soa_values_ms:
            raise ValueError(
                "modules.tbw.soa_values_ms artan sırada olmalı — psikometrik "
                "eğri uydurma sıralı ızgara varsayıyor"
            )
        expected = {"same", "different"}
        if set(self.response_labels) != expected:
            raise ValueError(
                "modules.tbw.response_labels anahtarları tam olarak "
                f"{sorted(expected)} olmalı, bulunan: {sorted(self.response_labels)}"
            )
        return self


class OddballConfig(ModuleBase):
    standard_hz: float = Field(gt=0)
    target_hz: float = Field(gt=0)
    target_probability: float = Field(gt=0.0, lt=1.0)
    min_standards_between_targets: int = Field(ge=0)
    n_trials: int = Field(gt=0)
    tone_duration_ms: float = Field(gt=0)
    tone_ramp_ms: float = Field(ge=0)
    isi_ms: tuple[float, float]
    ears: list[Ear] = Field(min_length=1)
    response_key: str = Field(min_length=1)

    def total_trials(self) -> int:
        return self.n_trials

    def n_targets(self) -> int:
        return round(self.n_trials * self.target_probability)

    @model_validator(mode="after")
    def _design_is_realisable(self) -> OddballConfig:
        if self.standard_hz == self.target_hz:
            raise ValueError("modules.oddball: standard_hz ve target_hz aynı olamaz")
        if 2 * self.tone_ramp_ms > self.tone_duration_ms:
            raise ValueError(
                "modules.oddball: iki rampa ton süresinden uzun — "
                f"2 × {self.tone_ramp_ms} ms > {self.tone_duration_ms} ms"
            )
        if self.isi_ms[0] > self.isi_ms[1]:
            raise ValueError("modules.oddball.isi_ms [alt, üst] sırasında olmalı")
        if self.isi_ms[0] <= 0:
            raise ValueError("modules.oddball.isi_ms pozitif olmalı")

        # A target sequence only exists if the standards required between
        # targets actually fit into the trial count.
        targets = self.n_targets()
        if targets < 1:
            raise ValueError(
                "modules.oddball: target_probability × n_trials 1'den küçük, "
                "hiç hedef üretilemez"
            )
        needed = targets + (targets - 1) * self.min_standards_between_targets
        if needed > self.n_trials:
            raise ValueError(
                f"modules.oddball: {targets} hedef arasında en az "
                f"{self.min_standards_between_targets} standart olması için "
                f"{needed} deneme gerekir, n_trials={self.n_trials}"
            )
        return self


class DichoticPair(StrictModel):
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)


class DichoticConfig(ModuleBase):
    """Dichotic listening.

    Not part of the reference method document yet — see progress.md, "Kullanıcıya
    bekleyen aksiyonlar".  The stimuli are 48 kHz stereo PCM WAVs produced by
    ``scripts/generate_dichotic_stimuli.py``; there is no video, so no ear or
    presentation-mode crossing: the pair itself is the lateralisation.
    """

    speaker_id: int = Field(ge=1)
    pairs: list[DichoticPair] = Field(min_length=1)
    reps: int = Field(gt=0)
    response_set: list[str] = Field(min_length=2)
    response_timeout_s: float = Field(gt=0)
    randomization: Literal["block_shuffle", "full_shuffle"]

    def total_trials(self) -> int:
        return len(self.pairs) * self.reps

    @model_validator(mode="after")
    def _pairs_are_dichotic(self) -> DichoticConfig:
        seen: set[tuple[str, str]] = set()
        for pair in self.pairs:
            if pair.left == pair.right:
                raise ValueError(
                    f"modules.dichotic.pairs: '{pair.left}' iki kulakta da aynı — "
                    "dikotik sunum farklı hece gerektirir"
                )
            key = (pair.left, pair.right)
            if key in seen:
                raise ValueError(f"modules.dichotic.pairs tekrarlı çift: {key}")
            seen.add(key)
        return self


class GINConfig(ModuleBase):
    """Gaps-In-Noise (Musiek et al., 2005) — auditory temporal resolution.

    Not part of the reference method document yet — see progress.md, "Kullanıcıya
    bekleyen aksiyonlar".  The noise segments are generated offline (§A.12
    forbids run-time DSP); that pipeline lands in Adım 2.
    """

    gap_durations_ms: list[float] = Field(min_length=1)
    reps_per_gap: int = Field(gt=0)
    segment_duration_s: float = Field(gt=0)
    n_segments: int = Field(gt=0)
    max_gaps_per_segment: int = Field(ge=1)
    min_gap_separation_s: float = Field(ge=0)
    inter_segment_interval_s: float = Field(ge=0)
    #: GIN is monaural.  Presenting it to a deaf ear measures nothing, so the
    #: ear is normally chosen per participant; the session flow (Adım 8) makes
    #: that choice and the database records the ear actually used.
    ear_selection: Literal["good_ear", "fixed", "both"]
    fixed_ear: Ear | None = None
    response_key: str = Field(min_length=1)
    #: "<hits>_of_<presentations>" — the threshold rule, written into the
    #: report.  Standard GIN uses 4 of 6.
    threshold_criterion: str

    def total_trials(self) -> int:
        # One trial = one noise segment.  Gaps are scored inside the segment.
        return self.n_segments

    def total_gaps(self) -> int:
        return len(self.gap_durations_ms) * self.reps_per_gap

    def threshold_rule(self) -> tuple[int, int]:
        match = _THRESHOLD_CRITERION_RE.match(self.threshold_criterion)
        if match is None:  # pragma: no cover - validated on construction
            raise ValueError(self.threshold_criterion)
        return int(match.group(1)), int(match.group(2))

    def estimated_duration_s(self) -> float:
        return self.n_segments * (
            self.segment_duration_s + self.inter_segment_interval_s
        )

    @model_validator(mode="after")
    def _design_is_realisable(self) -> GINConfig:
        if any(d <= 0 for d in self.gap_durations_ms):
            raise ValueError("modules.gin.gap_durations_ms pozitif olmalı")
        if len(set(self.gap_durations_ms)) != len(self.gap_durations_ms):
            raise ValueError("modules.gin.gap_durations_ms tekrarlı değer içeriyor")

        match = _THRESHOLD_CRITERION_RE.match(self.threshold_criterion)
        if match is None:
            raise ValueError(
                "modules.gin.threshold_criterion '<isabet>_of_<sunum>' biçiminde "
                f"olmalı (örn. '4_of_6'), bulunan: {self.threshold_criterion!r}"
            )
        hits, presentations = int(match.group(1)), int(match.group(2))
        if hits > presentations:
            raise ValueError(
                "modules.gin.threshold_criterion: isabet sayısı sunum sayısından "
                f"büyük olamaz ({hits} > {presentations})"
            )
        if presentations != self.reps_per_gap:
            raise ValueError(
                "modules.gin.threshold_criterion sunum sayısı reps_per_gap ile "
                f"eşleşmeli ({presentations} ≠ {self.reps_per_gap})"
            )

        capacity = self.n_segments * self.max_gaps_per_segment
        if self.total_gaps() > capacity:
            raise ValueError(
                f"modules.gin: {self.total_gaps()} boşluk {self.n_segments} "
                f"segmente sığmıyor (segment başına en fazla "
                f"{self.max_gaps_per_segment} → kapasite {capacity})"
            )

        # The gaps plus the silence that has to separate them must physically
        # fit inside one segment.
        longest = max(self.gap_durations_ms) / 1000.0
        needed = self.max_gaps_per_segment * longest + (
            self.max_gaps_per_segment + 1
        ) * self.min_gap_separation_s
        if needed > self.segment_duration_s:
            raise ValueError(
                f"modules.gin: {self.max_gaps_per_segment} boşluk + ayrım süresi "
                f"{needed:.3f} s tutuyor, segment {self.segment_duration_s} s. "
                "max_gaps_per_segment veya min_gap_separation_s düşürülmeli"
            )

        if self.ear_selection == "fixed" and self.fixed_ear is None:
            raise ValueError(
                "modules.gin.ear_selection 'fixed' ise fixed_ear verilmeli"
            )
        if self.ear_selection != "fixed" and self.fixed_ear is not None:
            raise ValueError(
                "modules.gin.fixed_ear yalnızca ear_selection 'fixed' iken anlamlı"
            )
        return self


class ModulesConfig(StrictModel):
    mcgurk: McGurkConfig
    avsr: AVSRConfig
    tbw: TBWConfig
    oddball: OddballConfig
    dichotic: DichoticConfig
    gin: GINConfig

    def by_name(self) -> dict[str, ModuleBase]:
        return {
            "mcgurk": self.mcgurk,
            "avsr": self.avsr,
            "tbw": self.tbw,
            "oddball": self.oddball,
            "dichotic": self.dichotic,
            "gin": self.gin,
        }


class SpeakerSelection(StrictModel):
    strategy: Literal["fixed", "balanced", "random"]
    fixed_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _fixed_needs_an_id(self) -> SpeakerSelection:
        if self.strategy == "fixed" and self.fixed_id is None:
            raise ValueError("speaker_selection.strategy 'fixed' ise fixed_id gerekli")
        return self


class CrossHearingCheck(StrictModel):
    """Detection task on the deaf ear — validates the lateralisation (§F.3)."""

    enabled: bool
    n_trials: int = Field(gt=0)


# ---------------------------------------------------------------------- root


class ExperimentConfig(StrictModel):
    experiment: ExperimentMeta
    paths: Paths
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig
    timing: TimingConfig
    display: DisplayConfig
    audio: AudioConfig
    session: SessionConfig
    modules: ModulesConfig
    speaker_selection: SpeakerSelection
    cross_hearing_check: CrossHearingCheck

    # -- design summary ---------------------------------------------------

    def enabled_modules(self) -> list[str]:
        return [
            name
            for name in self.session.module_order
            if name != "practice" and self.modules.by_name()[name].enabled
        ]

    def trial_counts(self) -> dict[str, int]:
        """Trials per module, in session order.

        This is the count the module generators must produce in Adım 4–7; the
        tests there assert against it so the estimate and the real design
        cannot drift apart.
        """
        counts: dict[str, int] = {}
        for name in self.session.module_order:
            if name == "practice":
                counts[name] = self.session.practice_trials
                continue
            module = self.modules.by_name()[name]
            counts[name] = module.total_trials() if module.enabled else 0
        if self.cross_hearing_check.enabled:
            counts["cross_hearing"] = self.cross_hearing_check.n_trials
        return counts

    def estimated_duration_s(self) -> float:
        total = 0.0
        for name in self.session.module_order:
            if name == "practice":
                continue
            module = self.modules.by_name()[name]
            if module.enabled:
                total += module.estimated_duration_s()
        n_breaks = sum(self.trial_counts().values()) // self.session.break_every_n_trials
        return total + n_breaks * self.session.break_duration_s

    # -- cross-section validation ----------------------------------------

    @model_validator(mode="after")
    def _module_order_matches_modules(self) -> ExperimentConfig:
        known = self.modules.by_name()
        for name in self.session.module_order:
            if name == "practice":
                continue
            if not known[name].enabled:
                raise ValueError(
                    f"session.module_order '{name}' içeriyor ama "
                    f"modules.{name}.enabled false"
                )
        missing = [
            name
            for name, module in known.items()
            if module.enabled and name not in self.session.module_order
        ]
        if missing:
            raise ValueError(
                f"Etkin ama module_order'da olmayan modüller: {sorted(missing)}. "
                "Etkin her modül oturum sırasında yer almalı, aksi hâlde sessizce "
                "hiç koşmaz"
            )
        return self

    @model_validator(mode="after")
    def _data_collection_requirements(self) -> ExperimentConfig:
        """Extra gates that only apply to real data collection (§G).

        File existence is checked in the loader — this layer never touches the
        disk.
        """
        if self.experiment.mode != "data_collection":
            return self

        problems: list[str] = []
        if self.timing.system_av_offset_ms is None:
            problems.append(
                "timing.system_av_offset_ms boş — fotodiyot ölçümü yapılmadan "
                "veri toplanamaz (01_av_gecikme_olcumu.md)"
            )
        if self.audio.calibration_file is None:
            problems.append(
                "audio.calibration_file boş — ses kalibrasyonu yapılmadan veri "
                "toplanamaz (02_kalibrasyon.md)"
            )
        if not self.display.fullscreen:
            problems.append("display.fullscreen false — veri toplamada zorunlu (§A.8)")
        if self.audio.device is None:
            problems.append(
                "audio.device boş — veri toplamada çıkış aygıtı açıkça "
                "belirtilmeli, operatör seçimine bırakılamaz"
            )
        if problems:
            raise ValueError(
                "mode: data_collection için eksikler:\n  - " + "\n  - ".join(problems)
            )
        return self
