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
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

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


class SessionScreens(StrictModel):
    """Every narrative screen the participant reads during a session (§A.9).

    Turkish, and in the config rather than in the code: an instruction wording
    is a protocol detail, so it has to travel in ``sessions.config_snapshot``
    with the data it applied to.  ``module_instructions`` must cover every
    enabled measurement module (checked in :class:`ExperimentConfig`) — a module
    with no instruction screen means the participant meets it with no idea what
    to do.
    """

    # ``break`` is a keyword, so the field is ``break_screen`` with a YAML
    # alias; populate_by_name lets the model still be built from field names.
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, populate_by_name=True
    )

    #: The key that advances past an instruction or break screen.
    advance_key: str = Field(min_length=1)
    #: The "press <key> to continue" hint shown under a screen.
    continue_hint: str = Field(min_length=1)
    welcome: str = Field(min_length=1)
    practice_intro: str = Field(min_length=1)
    #: Shown after practice — the comprehension-check / "the real test begins"
    #: screen the operator advances once the participant is ready.
    practice_end: str = Field(min_length=1)
    break_screen: str = Field(min_length=1, alias="break")
    session_end: str = Field(min_length=1)
    #: Shown when ESC is pressed, before the session actually stops (Adım 8b-ii).
    #: Names the confirm/cancel keys itself, since the wording is participant-
    #: facing and must not be hard-coded (§A.9).
    quit_confirm: str = Field(min_length=1)
    #: Required exactly when ``cross_hearing_check`` is enabled (checked in
    #: :class:`ExperimentConfig`); None otherwise, so a disabled check does not
    #: force a screen nobody sees.
    cross_hearing_intro: str | None = Field(default=None, min_length=1)
    #: Module name -> the instruction screen shown before it.  Coverage of the
    #: enabled modules is enforced at the root, where the module order is known.
    module_instructions: dict[ModuleName, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _instructions_are_not_blank(self) -> SessionScreens:
        # min_length on the field only constrains the top-level strings, not the
        # values of the dict — a blank instruction would otherwise pass.
        blank = sorted(
            name for name, text in self.module_instructions.items() if not text.strip()
        )
        if blank:
            raise ValueError(
                f"screens.module_instructions boş yönerge içeriyor: {blank}"
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


class PromptTexts(StrictModel):
    """Everything a response screen says to the participant (§A.9).

    Turkish, and in the config rather than in the module: a wording change in
    the response prompt is a protocol change, and it has to be visible in
    ``sessions.config_snapshot`` for the sessions it applied to.
    """

    question: str = Field(min_length=1)
    #: Prompt of the free-text field.  Optional because a module without a
    #: free-text option (TBW's two-alternative judgement) would otherwise have
    #: to carry a string the participant can never see; ``ResponseUIConfig``
    #: requires it exactly when ``free_text_response`` is set.
    other: str | None = Field(default=None, min_length=1)
    timeout: str = Field(min_length=1)


class ResponseUIConfig(ModuleBase):
    """The forced-choice response screen, for the modules that show one.

    Shared by McGurk (Adım 4) and AVSR (Adım 5): both put a labelled grid on
    the screen, take one key press and time out the same way, and every string
    the participant reads has to come from the config (§A.9).  What differs is
    what a response *means*, and that stays in the modules.

    ``config_path`` only names the section in the error messages, so a mistake
    in the AVSR block does not send the operator to the McGurk block.
    """

    config_path: ClassVar[str] = "modules.<modül>"

    response_set: list[str] = Field(min_length=2)
    #: Key that selects each entry of ``response_set``, in the same order.
    response_keys: list[str] = Field(min_length=2)
    #: The option that opens a free-text field.  Null means the module offers
    #: no escape hatch; naming it here keeps the Turkish label out of the code.
    free_text_response: str | None = None
    response_timeout_s: float = Field(gt=0)
    fixation_duration_ms: float = Field(gt=0)
    #: Blank screen after a response, before the next trial's fixation.
    post_response_ms: float = Field(ge=0)
    prompts: PromptTexts
    randomization: Literal["block_shuffle", "full_shuffle"]

    @model_validator(mode="after")
    def _keys_match_the_response_set(self) -> ResponseUIConfig:
        where = self.config_path
        if len(self.response_keys) != len(self.response_set):
            raise ValueError(
                f"{where}.response_keys ile response_set aynı uzunlukta "
                f"olmalı ({len(self.response_keys)} tuş, "
                f"{len(self.response_set)} yanıt) — eşleme sıraya dayanıyor"
            )
        if len(set(self.response_keys)) != len(self.response_keys):
            raise ValueError(f"{where}.response_keys tekrarlı tuş içeriyor")
        if len({r.casefold() for r in self.response_set}) != len(self.response_set):
            raise ValueError(f"{where}.response_set tekrarlı yanıt içeriyor")
        # An empty label would be an option the participant cannot read and a
        # response the scoring cannot interpret — AVSR would record it with a
        # NULL is_correct, which is reserved for the modules that have no
        # correct answer at all.
        if any(not label.strip() for label in self.response_set):
            raise ValueError(f"{where}.response_set boş bir yanıt içeriyor")
        if any(not key.strip() for key in self.response_keys):
            raise ValueError(f"{where}.response_keys boş bir tuş içeriyor")
        if self.free_text_response is not None and self.free_text_response.casefold() not in {
            r.casefold() for r in self.response_set
        }:
            raise ValueError(
                f"{where}.free_text_response '{self.free_text_response}' "
                "response_set içinde yok — seçilemeyen bir seçenek serbest metin "
                "alanını hiç açmaz"
            )
        if self.free_text_response is not None and self.prompts.other is None:
            raise ValueError(
                f"{where}.free_text_response tanımlı ama prompts.other yok — "
                "serbest metin alanı katılımcıya sorusuz açılırdı"
            )
        return self


class McGurkConfig(ResponseUIConfig):
    config_path: ClassVar[str] = "modules.mcgurk"

    speaker_id: int = Field(ge=1)
    av_pairs: list[AVPair] = Field(min_length=1)
    #: ``null`` = quiet, a number = SNR in dB.
    noise_conditions: list[float | None] = Field(min_length=1)
    ears: list[Ear] = Field(min_length=1)
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
                # Categorisation is ordered: the audio token is scored as
                # AUDITORY and the visual token as VISUAL before either map is
                # consulted, so a map that lists one of them contains a rule
                # that can never fire — and whoever wrote it expected it to.
                visual, audio = key.split("|", 1)
                shadowed = [
                    v
                    for v in values
                    if v.casefold() in (visual.casefold(), audio.casefold())
                ]
                if shadowed:
                    raise ValueError(
                        f"modules.mcgurk.{name}['{key}'] çiftin kendi "
                        f"token'ını içeriyor: {shadowed}. Bu yanıt zaten "
                        "AUDITORY/VISUAL olarak sınıflanır, kural hiç çalışmaz"
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

    #: Items read from ``word_list``.  Filled in by the loader, which is the
    #: only layer allowed to touch the disk; it stays private so the words
    #: cannot also be written inline in the YAML, which would give the design
    #: two sources that could disagree.
    _items: list[str] | None = PrivateAttr(default=None)

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

    def attach_items(self, items: list[str]) -> None:
        """Record the words read from ``word_list`` (loader only)."""
        self._items = list(items)

    def resolved_items(self) -> list[str] | None:
        """The items, or None while a word list is still unread."""
        if self.type == "syllable":
            return list(self.tokens or [])
        return None if self._items is None else list(self._items)

    def items(self) -> list[str]:
        """The distinct items this set presents, in config order.

        Word lists live in their own file, so they are read by the loader and
        attached here.  A word set that was never resolved raises rather than
        reporting zero items: zero would quietly shrink the design.
        """
        items = self.resolved_items()
        if items is None:
            raise ValueError(
                f"Kelime listesi ({self.word_list}) yüklenmedi — config'i "
                "mcgurk.config.loader.load_config ile açın (şema diske dokunmaz)"
            )
        return items

    def n_items(self) -> int:
        """How many distinct items this set contributes."""
        return len(self.items())


class AVSRConfig(ResponseUIConfig):
    config_path: ClassVar[str] = "modules.avsr"

    speaker_id: int = Field(ge=1)
    stimulus_sets: list[StimulusSet] = Field(min_length=1)
    presentation_modes: list[PresentationMode] = Field(min_length=1)
    noise_conditions: list[float | None] = Field(min_length=1)
    ears: list[Ear] = Field(min_length=1)
    response_mode: Literal["closed_set", "open_set"]
    #: Question per presentation mode, overriding ``prompts.question``.
    #: "Ne duydunuz?" is the wrong question in a V-only trial, where there is
    #: nothing to hear — and the wording is a protocol detail, so it belongs in
    #: the snapshot rather than in a branch in the code (§A.9).
    mode_questions: dict[PresentationMode, str] = Field(default_factory=dict)

    def question_for(self, mode: str) -> str:
        for presented, question in self.mode_questions.items():
            if presented == mode:
                return question
        return self.prompts.question

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
        if len(set(self.ears)) != len(self.ears):
            raise ValueError("modules.avsr.ears tekrarlı değer içeriyor")
        keys = [("null" if n is None else n) for n in self.noise_conditions]
        if len(set(keys)) != len(keys):
            raise ValueError("modules.avsr.noise_conditions tekrarlı değer içeriyor")
        unused = sorted(set(self.mode_questions) - set(self.presentation_modes))
        if unused:
            raise ValueError(
                f"modules.avsr.mode_questions sunulmayan mod içeriyor: {unused} "
                f"(presentation_modes: {self.presentation_modes}) — hiç görünmeyecek "
                "bir metin yazılmış demektir"
            )
        return self


class TBWStimulus(StrictModel):
    visual: str = Field(min_length=1)
    audio: str = Field(min_length=1)


class TBWConfig(ResponseUIConfig):
    """Modül 3 — the temporal binding window, by the method of constant stimuli.

    The response screen is the shared one (Adım 4–5), with two options instead
    of nine, so everything about showing it and timing it is inherited.  What
    this module adds is meaning: ``response_set`` says what is on the screen and
    in which order, ``response_labels`` says which of those two options is the
    *simultaneous* judgement.  The two are checked against each other at load,
    because a mismatch would silently invert the psychometric function — and an
    inverted curve still fits, it just reports the participant's window as its
    complement.
    """

    config_path: ClassVar[str] = "modules.tbw"

    speaker_id: int = Field(ge=1)
    stimulus: TBWStimulus
    soa_values_ms: list[float] = Field(min_length=3)
    reps_per_soa: int = Field(gt=0)
    ears: list[Ear] = Field(min_length=1)
    #: Written into the QC report — the literature uses both definitions and a
    #: TBW figure is meaningless without saying which one produced it.
    tbw_definition: Literal["fwhm", "sigma1"]
    #: ``same`` / ``different`` -> the ``response_set`` entry that means it.
    response_labels: dict[str, str]
    #: Resamples behind the confidence intervals; 0 reports the fit without any.
    bootstrap_samples: int = Field(default=2000, ge=0)
    bootstrap_ci: float = Field(default=0.95, gt=0.0, lt=1.0)

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
        if len(set(self.ears)) != len(self.ears):
            raise ValueError("modules.tbw.ears tekrarlı değer içeriyor")
        expected = {"same", "different"}
        if set(self.response_labels) != expected:
            raise ValueError(
                "modules.tbw.response_labels anahtarları tam olarak "
                f"{sorted(expected)} olmalı, bulunan: {sorted(self.response_labels)}"
            )

        # Two alternatives, and the two names have to be the same two strings:
        # the grid is built from response_set and the judgement is read off
        # response_labels, so anything else leaves an option that cannot be
        # interpreted or a judgement that cannot be given.
        if len(self.response_set) != 2:
            raise ValueError(
                "modules.tbw.response_set tam olarak iki seçenek içermeli "
                f"(eşzamanlılık yargısı iki alternatiflidir), bulunan: "
                f"{len(self.response_set)}"
            )
        shown = {r.casefold() for r in self.response_set}
        named = {label.casefold() for label in self.response_labels.values()}
        if shown != named:
            raise ValueError(
                "modules.tbw.response_labels değerleri response_set ile "
                f"eşleşmiyor: ekranda {sorted(self.response_set)}, "
                f"anlamlandırılan {sorted(self.response_labels.values())}"
            )
        if self.free_text_response is not None:
            raise ValueError(
                "modules.tbw.free_text_response null olmalı — serbest metin "
                "seçeneği psikometrik eğriden deneme düşürür ve iki alternatifli "
                "yargının üçüncü bir yanıtı yoktur"
            )

        # A percentile interval is read off the tails of the resample
        # distribution; with 100 resamples the 2.5th percentile is decided by
        # two of them, and the interval says more about the draw than the data.
        if 0 < self.bootstrap_samples < 200:
            raise ValueError(
                "modules.tbw.bootstrap_samples ya 0 (güven aralığı yok) ya da "
                f"en az 200 olmalı, verilen: {self.bootstrap_samples}"
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
    #: ``[alt, üst]`` ms from a tone's onset: a press inside this interval is a
    #: response to that tone.  It is a design parameter, not an analysis one —
    #: choosing it after the data is in means choosing the hit and false-alarm
    #: rates after seeing them.
    response_window_ms: tuple[float, float]
    #: Fixation before the first tone.  The participant needs a moment between
    #: "the module started" and the first thing they have to judge.
    lead_in_s: float = Field(gt=0)

    def total_trials(self) -> int:
        return self.n_trials

    def n_targets(self) -> int:
        return round(self.n_trials * self.target_probability)

    def tone_frequencies(self) -> list[float]:
        """The tones this module needs prepared, low to high."""
        return sorted({self.standard_hz, self.target_hz})

    @model_validator(mode="after")
    def _design_is_realisable(self) -> OddballConfig:
        if self.standard_hz == self.target_hz:
            raise ValueError("modules.oddball: standard_hz ve target_hz aynı olamaz")
        if 2 * self.tone_ramp_ms > self.tone_duration_ms:
            raise ValueError(
                "modules.oddball: iki rampa ton süresinden uzun — "
                f"2 x {self.tone_ramp_ms} ms > {self.tone_duration_ms} ms"
            )
        if self.isi_ms[0] > self.isi_ms[1]:
            raise ValueError("modules.oddball.isi_ms [alt, üst] sırasında olmalı")
        if self.isi_ms[0] <= 0:
            raise ValueError("modules.oddball.isi_ms pozitif olmalı")

        low, high = self.response_window_ms
        if low < 0 or high <= low:
            raise ValueError(
                "modules.oddball.response_window_ms [alt, üst] ve "
                f"0 <= alt < üst olmalı, verilen: {list(self.response_window_ms)}"
            )
        # A press has to belong to exactly one tone.  If the window outlasted
        # the shortest interval, a press could be a response to two of them and
        # the hit rate would depend on which one the code happened to pick.
        if high >= self.isi_ms[0]:
            raise ValueError(
                f"modules.oddball.response_window_ms üst sınırı ({high:g} ms) en "
                f"kısa ISI'dan ({self.isi_ms[0]:g} ms) kısa olmalı — aksi hâlde "
                "bir tuş basımı iki tona birden ait olurdu"
            )
        if self.tone_duration_ms > high:
            raise ValueError(
                f"modules.oddball: ton süresi ({self.tone_duration_ms:g} ms) yanıt "
                f"penceresinin üst sınırından ({high:g} ms) uzun — ton biterken "
                "verilen bir yanıt pencerenin dışında kalırdı"
            )

        # n_trials is the total, so the ears are not crossed; a second entry
        # would have no defined meaning.  Which ear the tones go to is still a
        # choice, it is just one choice per session.
        if len(self.ears) != 1:
            raise ValueError(
                "modules.oddball.ears tam olarak bir değer içermeli "
                f"(verilen: {self.ears}). n_trials toplam deneme sayısıdır, "
                "kulakla çaprazlanmaz."
            )

        # A target sequence only exists if the standards required around the
        # targets actually fit into the trial count.
        targets = self.n_targets()
        if targets < 1:
            raise ValueError(
                "modules.oddball: target_probability x n_trials 1'den küçük, "
                "hiç hedef üretilemez"
            )
        # The leading standards count too: the first tone of the run cannot be
        # a deviant, because nothing has been established for it to deviate
        # from.  So every target needs its own run of standards before it.
        needed = targets * (1 + self.min_standards_between_targets)
        if needed > self.n_trials:
            raise ValueError(
                f"modules.oddball: {targets} hedefin her birinin önünde en az "
                f"{self.min_standards_between_targets} standart olması için "
                f"{needed} deneme gerekir, n_trials={self.n_trials}"
            )
        return self


class DichoticPair(StrictModel):
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)


class DichoticConfig(ResponseUIConfig):
    """Modül 5 — dichotic listening (Adım 7b).

    Drafted for the method document as §6.5 (``docs/EK_DIKOTIK_DINLEME.docx``),
    where it is still awaiting the supervisor's approval — see progress.md,
    "Kullanıcıya bekleyen aksiyonlar".

    The response screen is the shared one, so everything about showing it and
    timing it is inherited.  What this module adds is the stimulus: a 48 kHz
    stereo WAV carrying a different syllable in each ear (prepared in Adım 2).
    There is no video, no noise condition — the competition between the ears is
    the difficult condition — and no ear factor either: both ears receive a
    token on every trial and which one is the pair itself, so nothing is crossed
    with ``reps``.
    """

    config_path: ClassVar[str] = "modules.dichotic"

    speaker_id: int = Field(ge=1)
    pairs: list[DichoticPair] = Field(min_length=1)
    reps: int = Field(gt=0)

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
    #: Which press counts as a response to which gap, in ms from the gap's
    #: onset.  Fixed before data collection on purpose (§F, EK_GIN §"Danışman
    #: Onayı Gereken Noktalar"): choosing it afterwards means choosing the hit
    #: and false-alarm rates after seeing them.
    response_window_ms: tuple[float, float]
    #: Fixation before the first segment, and the margin the first one is
    #: scheduled in.
    lead_in_s: float = Field(gt=0)
    #: "<hits>_of_<presentations>" — the threshold rule, written into the
    #: report.  Standard GIN uses 4 of 6.
    threshold_criterion: str

    def ears_tested(self) -> int:
        """How many ears one participant is tested on.

        ``both`` presents the whole segment list twice, once per ear — the
        draft's alternative, which it costs ~4 minutes.  ``good_ear`` and
        ``fixed`` are monaural, which is what standard GIN is.
        """
        return 2 if self.ear_selection == "both" else 1

    def total_trials(self) -> int:
        # One trial = one noise segment.  Gaps are scored inside the segment.
        return self.n_segments * self.ears_tested()

    def total_gaps(self) -> int:
        return len(self.gap_durations_ms) * self.reps_per_gap

    def threshold_rule(self) -> tuple[int, int]:
        match = _THRESHOLD_CRITERION_RE.match(self.threshold_criterion)
        if match is None:  # pragma: no cover - validated on construction
            raise ValueError(self.threshold_criterion)
        return int(match.group(1)), int(match.group(2))

    def estimated_duration_s(self) -> float:
        return self.total_trials() * (
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
                f"eşleşmeli ({presentations} != {self.reps_per_gap})"
            )

        capacity = self.n_segments * self.max_gaps_per_segment
        if self.total_gaps() > capacity:
            raise ValueError(
                f"modules.gin: {self.total_gaps()} boşluk {self.n_segments} "
                f"segmente sığmıyor (segment başına en fazla "
                f"{self.max_gaps_per_segment} -> kapasite {capacity})"
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

        low, high = self.response_window_ms
        if low < 0 or high <= low:
            raise ValueError(
                "modules.gin.response_window_ms [alt, üst] ve artan olmalı, "
                f"verilen: {list(self.response_window_ms)}"
            )
        # The window may not reach the next gap: a press inside one gap's window
        # would then also be inside the previous gap's, and which one it counted
        # for would depend on the code rather than on the design.
        if high >= self.min_gap_separation_s * 1000.0:
            raise ValueError(
                f"modules.gin.response_window_ms üst sınırı ({high:g} ms) "
                f"boşluklar arası en kısa ayrımdan ({self.min_gap_separation_s:g} "
                "s) kısa olmalı — aksi hâlde bir tuş basımı iki boşluğa birden "
                "ait olurdu"
            )
        # A gap can sit close to the end of the segment, so its window runs into
        # the inter-segment interval.  Listening continues there, but not past
        # the next segment's start.
        if high >= (self.segment_duration_s + self.inter_segment_interval_s) * 1000.0:
            raise ValueError(
                f"modules.gin.response_window_ms üst sınırı ({high:g} ms) "
                "segment + segmentler arası aradan kısa olmalı"
            )

        if self.ear_selection == "fixed" and self.fixed_ear is None:
            raise ValueError(
                "modules.gin.ear_selection 'fixed' ise fixed_ear verilmeli"
            )
        if self.ear_selection != "fixed" and self.fixed_ear is not None:
            raise ValueError(
                "modules.gin.fixed_ear yalnızca ear_selection 'fixed' iken anlamlı"
            )
        if self.fixed_ear == "both":
            # "both" as a *side* means diotic, which is not what a monaural test
            # asks for; presenting to both ears at once is a different measure.
            raise ValueError(
                "modules.gin.fixed_ear 'both' olamaz — GIN monaural bir testtir. "
                "İki kulağın da test edilmesi isteniyorsa ear_selection: both"
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
    """Detection task on the deaf ear — validates the lateralisation (§F.3).

    In an SSD participant, a tone lateralised to the deaf ear should be at chance:
    if it is detected above chance the sound is reaching the good cochlea through
    the skull and the spatial-direction manipulation is invalid for them.  What
    is measured here is only the raw detections and false alarms; whether that is
    "above chance" is Adım 9's reading (§F.3), not this module's.
    """

    enabled: bool
    n_trials: int = Field(gt=0)
    #: Detection-tone frequency.  Defaults to the oddball standard so one prepared
    #: tone serves both — see :meth:`ExperimentConfig.required_tones`.
    tone_hz: float = Field(gt=0)
    #: Fraction of trials with no sound.  A press on a catch trial is a false
    #: alarm; without catch trials, pressing on every trial would look like
    #: perfect detection.
    catch_ratio: float = Field(gt=0.0, lt=1.0)
    #: A press this many ms after the tone onset counts as a detection.
    response_window_ms: tuple[float, float]
    response_key: str = Field(min_length=1)
    fixation_duration_ms: float = Field(gt=0)
    post_response_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def _window_is_ordered(self) -> CrossHearingCheck:
        low, high = self.response_window_ms
        if low < 0 or high <= low:
            raise ValueError(
                "cross_hearing_check.response_window_ms [alt, üst] ve "
                f"0 <= alt < üst olmalı, verilen: {list(self.response_window_ms)}"
            )
        return self


class ChecklistConfig(StrictModel):
    """Thresholds for ``python -m mcgurk.checklist`` (steps.md §C Adım 8).

    In the config rather than the code because they are QC parameters (§A.9): a
    site that recalibrates weekly and one that recalibrates monthly draw the RED
    line in different places, and neither should have to edit Python to move it.
    """

    #: A calibration older than this many days turns the check RED.
    calibration_max_age_days: int = Field(gt=0)
    #: Free space below this many MB on the data volume turns the check RED.
    min_free_disk_mb: int = Field(ge=0)


# --------------------------------------------------------- stimulus preparation


class SpeakerSource(StrictModel):
    """One speaker: the id the modules reference and its raw recording folder.

    The mapping used to be implicit — ``modules.*.speaker_id: 1`` with nothing
    saying which of the ``assets/`` folders that is.  Writing it down means
    adding a speaker cannot silently renumber the existing ones.
    """

    id: int = Field(ge=1)
    source: Path


class VideoPrep(StrictModel):
    #: The sources are 29.97 fps (30000/1001), which is 2.002 refreshes per
    #: frame at 60 Hz and therefore a periodic frame repeat.  30 makes it two.
    target_fps: float = Field(gt=0)
    crf: int = Field(ge=0, le=51)
    #: Every frame an I-frame: decoding one frame never depends on another, so
    #: playback cannot stall on a long GOP.  Costs disk, which is free here.
    all_intra: bool = True


class AudioPrep(StrictModel):
    bit_depth: Literal[16, 24]
    #: Active-speech level every token is normalised to.  Well below 0 dBFS so
    #: adding noise at the configured SNR cannot clip.
    target_level_dbfs: float = Field(lt=0)
    #: A frame counts as speech when its energy is within this many dB of the
    #: loudest frame.  Whole-file RMS is wrong here: the tokens are ~43%
    #: silence and the silent fraction differs between them.
    active_speech_threshold_db: float = Field(gt=0)
    #: Fade at the start and end of every written speech file.  Alignment
    #: trims up to ~250 ms off the front of some tokens, which leaves the file
    #: beginning mid-hiss; without a fade, some trials would start with a step
    #: and others with digital silence.
    edge_ramp_ms: float = Field(gt=0)


class BurstPrep(StrictModel):
    #: Envelope rise over the pre-burst floor that counts as the burst.
    threshold_db: float = Field(gt=0)
    #: …and how long it has to stay up, so a single sample of noise is not it.
    min_duration_ms: float = Field(gt=0)
    #: QC gate: after alignment the burst is measured again and must land this
    #: close to its target, otherwise preparation fails.
    alignment_tolerance_ms: float = Field(gt=0)


class NoisePrep(StrictModel):
    type: Literal["speech_shaped"]
    #: Distinct noise waveforms per (token, SNR).  With 10 repetitions per cell
    #: a single waveform would be heard ten times and could be learned.
    instances: int = Field(ge=1)
    ltas_tolerance_db: float = Field(gt=0)
    ramp_ms: float = Field(ge=0)


class GinPrep(StrictModel):
    #: Gap edges are ramped: an instantaneous cut produces a click whose
    #: spectral splatter is audible independently of the gap itself.
    gap_ramp_ms: float = Field(gt=0)
    #: Fade at the start and end of a whole segment.  Separate from
    #: ``noise.ramp_ms``, which shapes the noise mixed into a 2.5 s speech
    #: token and therefore has to be short: a six-second noise burst that
    #: arrives in 50 ms is startling, and startle is not what GIN measures.
    segment_ramp_ms: float = Field(gt=0)
    bandwidth_hz: tuple[float, float]


class TonePrep(StrictModel):
    """The part of an oddball tone that is not in ``modules.oddball``.

    Frequency, duration and ramp are the design and live with the module; the
    level is a property of the written file, like every other level under
    ``stimulus_prep``.  Separate from ``audio.target_level_dbfs`` so the speech
    corpus can be re-levelled without silently moving the tones with it.
    """

    level_dbfs: float = Field(lt=0)


class StimulusPrep(StrictModel):
    """Everything ``tools/prepare_stimuli.py`` needs (steps.md §C Adım 2).

    Preparation is offline by design (§A.12): nothing here is read during a
    trial.  It is in the experiment config rather than a separate file because
    the prepared set and the design have to be validated against each other —
    a token in ``av_pairs`` with no recording is a config error, not a run-time
    surprise.
    """

    seed: int
    speakers: list[SpeakerSource] = Field(min_length=1)
    tokens: list[str] = Field(min_length=1)
    video: VideoPrep
    audio: AudioPrep
    burst: BurstPrep
    noise: NoisePrep
    gin: GinPrep
    tones: TonePrep

    def speaker_ids(self) -> list[int]:
        return [speaker.id for speaker in self.speakers]

    def source_for(self, speaker_id: int) -> Path:
        for speaker in self.speakers:
            if speaker.id == speaker_id:
                return speaker.source
        raise KeyError(f"stimulus_prep.speakers içinde id {speaker_id} yok")

    @model_validator(mode="after")
    def _no_duplicates(self) -> StimulusPrep:
        ids = self.speaker_ids()
        if len(set(ids)) != len(ids):
            raise ValueError("stimulus_prep.speakers tekrarlı id içeriyor")
        sources = [str(s.source) for s in self.speakers]
        if len(set(sources)) != len(sources):
            raise ValueError("stimulus_prep.speakers tekrarlı kaynak klasörü içeriyor")
        if len(set(self.tokens)) != len(self.tokens):
            raise ValueError("stimulus_prep.tokens tekrarlı değer içeriyor")
        low, high = self.gin.bandwidth_hz
        if low <= 0 or high <= low:
            raise ValueError(
                "stimulus_prep.gin.bandwidth_hz [alt, üst] ve 0 < alt < üst olmalı"
            )
        return self


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
    screens: SessionScreens
    modules: ModulesConfig
    speaker_selection: SpeakerSelection
    cross_hearing_check: CrossHearingCheck
    checklist: ChecklistConfig
    stimulus_prep: StimulusPrep

    # -- what the stimulus set has to contain ------------------------------

    def required_snrs(self) -> list[float]:
        """SNRs the enabled modules ask for, in dB.

        Derived rather than configured twice: a separate list under
        ``stimulus_prep`` could disagree with ``noise_conditions`` and the
        mismatch would only show up as a missing file mid-session.
        """
        snrs: set[float] = set()
        for module in (self.modules.mcgurk, self.modules.avsr):
            if not module.enabled:
                continue
            snrs.update(snr for snr in module.noise_conditions if snr is not None)
        return sorted(snrs)

    def required_tones(self) -> list[float]:
        """Tone frequencies the enabled modules ask for, in Hz.

        Derived from ``modules.oddball`` (and the cross-hearing check, which
        reuses the standard tone) for the same reason as :meth:`required_snrs`:
        a second list under ``stimulus_prep`` could disagree with the design, and
        the disagreement would surface as a stimulus file that is named after one
        frequency and carries another.
        """
        tones: set[float] = set()
        if self.modules.oddball.enabled:
            tones.update(self.modules.oddball.tone_frequencies())
        if self.cross_hearing_check.enabled:
            tones.add(self.cross_hearing_check.tone_hz)
        return sorted(tones)

    def required_speaker_ids(self) -> list[int]:
        ids: set[int] = set()
        for module in (
            self.modules.mcgurk,
            self.modules.avsr,
            self.modules.tbw,
            self.modules.dichotic,
        ):
            if module.enabled:
                ids.add(module.speaker_id)
        if self.speaker_selection.fixed_id is not None:
            ids.add(self.speaker_selection.fixed_id)
        return sorted(ids)

    def required_tokens(self) -> dict[str, list[str]]:
        """Tokens each enabled module needs, keyed by module name."""
        needed: dict[str, list[str]] = {}
        if self.modules.mcgurk.enabled:
            needed["mcgurk"] = sorted(
                {t for p in self.modules.mcgurk.av_pairs for t in (p.visual, p.audio)}
            )
        if self.modules.avsr.enabled:
            tokens: set[str] = set()
            for stimulus_set in self.modules.avsr.stimulus_sets:
                if not stimulus_set.enabled:
                    continue
                # A word set contributes nothing until the loader has read its
                # file; the loader re-runs this check once it has.
                tokens.update(stimulus_set.resolved_items() or [])
            needed["avsr"] = sorted(tokens)
        if self.modules.tbw.enabled:
            stimulus = self.modules.tbw.stimulus
            needed["tbw"] = sorted({stimulus.visual, stimulus.audio})
        if self.modules.dichotic.enabled:
            needed["dichotic"] = sorted(
                {t for p in self.modules.dichotic.pairs for t in (p.left, p.right)}
            )
        return needed

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
    def _screens_cover_the_session(self) -> ExperimentConfig:
        """Every enabled module the participant meets must have a screen (§A.9).

        Coverage cannot be checked on ``SessionScreens`` alone: whether a module
        is presented depends on ``session.module_order`` and ``modules.*.enabled``,
        which only exist here.  A module with no instruction screen is a
        participant sitting down with no idea what to do; an instruction for a
        module that is never presented is text nobody reads — both are refused.
        """
        presented = self.enabled_modules()
        missing = [m for m in presented if m not in self.screens.module_instructions]
        if missing:
            raise ValueError(
                f"screens.module_instructions eksik: {sorted(missing)} için "
                "yönerge yok. Etkin her ölçüm modülünün bir yönerge ekranı "
                "olmalı, aksi hâlde katılımcı modülle ne yapacağını bilmeden "
                "karşılaşır"
            )
        # An instruction keyed to something that is not a measurement module can
        # never be shown.  A *disabled* measurement module is fine — its screen
        # is dormant and returns when it is re-enabled — but 'practice' has its
        # own screens (practice_intro/end) and never reads this map.
        non_modules = sorted(
            set(self.screens.module_instructions) - set(self.modules.by_name())
        )
        if non_modules:
            raise ValueError(
                "screens.module_instructions ölçüm modülü olmayan anahtar "
                f"içeriyor: {non_modules}. 'practice' kendi ekranlarını "
                "(practice_intro / practice_end) kullanır, module_instructions'a "
                "yazılmaz"
            )
        if self.cross_hearing_check.enabled and self.screens.cross_hearing_intro is None:
            raise ValueError(
                "cross_hearing_check.enabled ama screens.cross_hearing_intro yok "
                "— çapraz dinleme kontrolü katılımcıya yönergesiz başlardı"
            )
        return self

    @model_validator(mode="after")
    def _design_matches_the_stimulus_set(self) -> ExperimentConfig:
        problems = self.design_problems()
        if problems:
            raise ValueError(
                "Tasarım ile uyaran seti uyuşmuyor:\n  - " + "\n  - ".join(problems)
            )
        return self

    def design_problems(self) -> list[str]:
        """Every speaker and token the design uses must be preparable.

        Without this, a typo in ``av_pairs`` or a ``speaker_id`` with no
        recording folder surfaces as a missing file — either when the stimuli
        are prepared, or worse, halfway through a session.

        Returned rather than raised so the loader can run it a second time,
        after it has read the AVSR word lists: those items are not knowable at
        schema-validation time, and this layer never touches the disk.
        """
        problems: list[str] = []

        known_ids = set(self.stimulus_prep.speaker_ids())
        unknown_ids = [i for i in self.required_speaker_ids() if i not in known_ids]
        if unknown_ids:
            problems.append(
                f"stimulus_prep.speakers içinde olmayan speaker_id: {unknown_ids} "
                f"(tanımlı: {sorted(known_ids)})"
            )

        known_tokens = set(self.stimulus_prep.tokens)
        for module_name, tokens in self.required_tokens().items():
            unknown = [t for t in tokens if t not in known_tokens]
            if unknown:
                problems.append(
                    f"modules.{module_name} stimulus_prep.tokens içinde olmayan "
                    f"token kullanıyor: {unknown} (tanımlı: {sorted(known_tokens)})"
                )

        # A gap inside the segment's own fade would be presented at a lower
        # level than the ones outside it, so its detectability — the whole
        # measurement — would depend on where it happened to land.
        if self.modules.gin.enabled:
            ramp_s = self.stimulus_prep.gin.segment_ramp_ms / 1000.0
            if ramp_s > self.modules.gin.min_gap_separation_s:
                problems.append(
                    f"stimulus_prep.gin.segment_ramp_ms ({ramp_s * 1000:.0f} ms) "
                    f"modules.gin.min_gap_separation_s "
                    f"({self.modules.gin.min_gap_separation_s * 1000:.0f} ms) "
                    "değerini aşıyor — boşluk segmentin kendi rampasının içine "
                    "düşebilir"
                )

        return problems

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
