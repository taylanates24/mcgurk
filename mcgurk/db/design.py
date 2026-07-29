"""Validation for the ``trials.design_extra`` JSON column.

Modules differ in what a trial *is*: a dichotic trial carries two simultaneous
audio tokens, a GIN trial carries a list of gap onsets, an oddball trial
carries a tone type.  Giving each of them its own column would leave the table
mostly NULL and force a schema migration every time a module is added — during
a 12-month study that is a worse risk than a JSON column.

The column is not a free-for-all: every module declares its extra fields here,
unknown keys are rejected, and ``db/schema.sql`` exposes the known keys as real
columns in ``v_trials_flat`` so analysis never sees JSON.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class DesignExtraError(ValueError):
    """Raised when a trial's module-specific design fields are malformed."""


class _Extra(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoExtra(_Extra):
    """Modules whose design fits entirely in the shared trial columns."""


class _SpeakerExtra(_Extra):
    """Which speaker was seen, and which noise waveform was heard.

    ``speaker_id`` is recorded per trial rather than left to the config
    snapshot: the snapshot only pins it down while
    ``speaker_selection.strategy`` is ``fixed``, and §F.4 leaves ``balanced``
    and ``random`` open.

    ``noise_instance`` is 1-based, matching the manifest, and None wherever no
    noise was mixed in — the quiet condition, and AVSR's V-only trials, which
    carry no audio at all.  Adım 2 prepares several noise waveforms per cell so
    that the repetitions of a cell are not repetitions of one waveform; which
    one a trial used is part of the trial.
    """

    speaker_id: int = Field(ge=1)
    noise_instance: int | None = Field(default=None, ge=1)


class McGurkExtra(_SpeakerExtra):
    pass


class AVSRExtra(_SpeakerExtra):
    """The item that was presented, and which kind of item it was.

    ``item`` is the syllable or word itself rather than a row number: it is
    what the response is scored against, and a number would need the config
    snapshot to be interpretable.
    """

    stimulus_type: Literal["syllable", "word"]
    item: str = Field(min_length=1)


class TBWExtra(_SpeakerExtra):
    """Which speaker the SOA was presented on.

    ``noise_instance`` is always None here — TBW is presented in quiet — but it
    comes with the base rather than being forbidden: the field means "which
    noise waveform", and "none" is the honest answer for a quiet trial.
    """


class OddballExtra(_Extra):
    """Which tone was presented, and how long after the previous one.

    ``isi_ms`` is the *nominal* interval from the preceding tone's onset, None
    for the first tone of the run.  The realised interval is recoverable by
    differencing ``trials.audio_onset_s``; keeping the nominal one alongside is
    what lets QC compare the two without re-running the design generator.
    """

    tone_type: Literal["standard", "target"]
    tone_hz: float = Field(gt=0)
    isi_ms: float | None = Field(default=None, gt=0)


class DichoticExtra(_SpeakerExtra):
    """The two simultaneous tokens, and which speaker they came from.

    ``trials.audio_token`` is NULL on a dichotic trial: there are two of them,
    and picking one for the column would make the other invisible to anything
    reading it.  Both are exposed by ``v_trials_flat`` as
    ``dichotic_left_token`` / ``dichotic_right_token``.

    ``noise_instance`` is always None here — the module is presented in quiet,
    because the competition between the ears is itself the difficult condition —
    but it comes with the base rather than being forbidden, exactly as in TBW:
    the field means "which noise waveform", and "none" is the honest answer.
    """

    left_token: str = Field(min_length=1)
    right_token: str = Field(min_length=1)


class GINExtra(_Extra):
    """Gap positions inside one noise segment.

    Onsets are seconds from segment start; durations are in milliseconds,
    matching ``modules.gin.gap_durations_ms`` in the config.
    """

    gap_onsets_s: list[float]
    gap_durations_ms: list[float]

    def model_post_init(self, _context: object) -> None:
        if len(self.gap_onsets_s) != len(self.gap_durations_ms):
            raise ValueError(
                "gap_onsets_s ve gap_durations_ms aynı uzunlukta olmalı "
                f"({len(self.gap_onsets_s)} != {len(self.gap_durations_ms)})"
            )
        if any(onset < 0 for onset in self.gap_onsets_s):
            raise ValueError("gap_onsets_s negatif olamaz")
        if sorted(self.gap_onsets_s) != self.gap_onsets_s:
            raise ValueError("gap_onsets_s artan sırada olmalı")


class CrossHearingExtra(_Extra):
    signal_present: bool


_BY_MODULE: dict[str, type[_Extra]] = {
    "practice": NoExtra,
    "mcgurk": McGurkExtra,
    "avsr": AVSRExtra,
    "tbw": TBWExtra,
    "oddball": OddballExtra,
    "dichotic": DichoticExtra,
    "gin": GINExtra,
    "cross_hearing": CrossHearingExtra,
}


def known_modules() -> frozenset[str]:
    return frozenset(_BY_MODULE)


def validate_design_extra(module: str, data: dict[str, object] | None) -> str:
    """Validate *data* for *module* and return it as a JSON string.

    Raises:
        DesignExtraError: unknown module, unknown key, or a bad value.
    """
    model = _BY_MODULE.get(module)
    if model is None:
        raise DesignExtraError(
            f"Bilinmeyen modül: {module!r}. Tanımlı olanlar: "
            f"{sorted(_BY_MODULE)}"
        )
    try:
        validated = model.model_validate(data or {})
    except ValidationError as exc:
        raise DesignExtraError(
            f"{module} denemesinin design_extra alanı geçersiz:\n{exc}"
        ) from exc
    return json.dumps(validated.model_dump(), ensure_ascii=False, sort_keys=True)


def parse_design_extra(module: str, raw: str) -> dict[str, object]:
    """Inverse of :func:`validate_design_extra`, with the same validation."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DesignExtraError(
            f"{module} denemesinin design_extra alanı JSON değil: {raw!r}"
        ) from exc
    if not isinstance(data, dict):
        raise DesignExtraError(
            f"{module} denemesinin design_extra alanı nesne olmalı: {raw!r}"
        )
    validate_design_extra(module, data)
    return data
