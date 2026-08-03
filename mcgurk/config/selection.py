"""What the operator chooses at the start of a session (steps.md ADIM 12).

Two decisions that used to be config-only: **which speaker** the participant is
tested with, and **which modules** are run.  The menu that asks them is a
PsychoPy dialog (12c) and the flags that bypass it are on ``python -m
mcgurk.ui``; both are thin shells over this module, which is pure and tested in
CI (§A12.4) — the same split as ``ui/login.py``'s ``build_participant`` /
``show_login_dialog``.

**The selection is applied to the config, not carried alongside it** (§A12.1).
:func:`apply` returns a config in which the unselected modules are disabled,
``session.module_order`` is shortened to what will actually run, and
``speaker_selection`` is pinned to the chosen id.  That config is what the
session starts with, so it is what lands in ``sessions.config_snapshot`` — and
the snapshot is already the authority for resume, analysis and QC.  Nothing
downstream has to learn about "selection": a module that was not chosen is
simply not in this session's design, which is a statement the rest of the
platform already understands.

The alternative — editing ``config/experiment.yaml`` before each session —
would change the design for everyone, including sessions already planned.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .loader import ConfigError
from .schema import ExperimentConfig

#: Modules whose design picks one speaker's recordings.  oddball presents pure
#: tones and gin broadband noise; neither has a face.
SPEAKER_MODULES = ("mcgurk", "avsr", "tbw", "dichotic")

#: Operator-facing names.  Turkish and cp1254-safe (the em dash is 0x97 there).
#: These are read by the operator, not the participant, so they are code rather
#: than config — the §A.9 rule covers what the *participant* is shown.  Keys
#: cover the two session steps as well, since both are selectable.
MODULE_LABELS = {
    "practice": "Alıştırma",
    "mcgurk": "Modül 1 — McGurk",
    "avsr": "Modül 2 — AVSR",
    "tbw": "Modül 3 — TBW (zamansal bağlama penceresi)",
    "oddball": "Modül 4 — Oddball (dikkat kontrolü)",
    "dichotic": "Modül 5 — Dikotik dinleme",
    "gin": "Modül 6 — GIN (sessizlik aralığı)",
    "cross_hearing": "Çapraz dinleme kontrolü",
}


class SelectionError(ConfigError):
    """The operator's choice cannot be turned into a runnable design."""


@dataclass(frozen=True)
class SpeakerChoice:
    """One row of the menu's speaker list."""

    speaker_id: int
    label: str
    source: Path


@dataclass(frozen=True)
class ModuleChoice:
    """One row of the menu's module list, with what it costs."""

    name: str
    label: str
    n_trials: int


@dataclass(frozen=True)
class SessionSelection:
    """What will be run, and with whom.

    ``modules`` holds measurement modules only; ``practice`` and
    ``cross_hearing`` are session-flow steps, so they are their own flags — the
    same distinction ``session.module_order`` and ``cross_hearing_check`` make.

    ``speaker_id`` is ``None`` when the operator did not override the speaker —
    then ``speaker_selection`` is left exactly as configured and its strategy
    still decides.  The menu (12c) always fills it in; the command line does not
    have to, so ``--modules`` alone changes only what it says it changes.
    """

    modules: tuple[str, ...]
    speaker_id: int | None = None
    practice: bool = True
    cross_hearing: bool = True

    def describe(self) -> str:
        """One line for the operator note and the log."""
        modules = ", ".join(self.modules)
        speaker = "(config)" if self.speaker_id is None else str(self.speaker_id)
        extras = [
            name
            for name, on in (("alıştırma", self.practice), ("çapraz", self.cross_hearing))
            if on
        ]
        suffix = f" (+{', '.join(extras)})" if extras else ""
        return f"konuşmacı={speaker} modüller={modules}{suffix}"


# ------------------------------------------------------------------ choices


def available_speakers(config: ExperimentConfig) -> list[SpeakerChoice]:
    """The prepared speakers, in config order.

    A speaker with no ``label`` still gets a readable row: an unnamed line in a
    menu is one the operator cannot choose between.
    """
    return [
        SpeakerChoice(
            speaker_id=speaker.id,
            label=speaker.label or f"Konuşmacı {speaker.id}",
            source=speaker.source,
        )
        for speaker in config.stimulus_prep.speakers
    ]


def available_modules(config: ExperimentConfig) -> list[ModuleChoice]:
    """The measurement modules this config enables, in session order.

    The menu chooses *within* the config, never around it: a module switched off
    in ``config/experiment.yaml`` is a design decision (§A.9) and turning it back
    on is a config edit, not a checkbox.
    """
    counts = config.trial_counts()
    return [
        ModuleChoice(
            name=name,
            label=MODULE_LABELS.get(name, name),
            n_trials=counts.get(name, 0),
        )
        for name in config.enabled_modules()
    ]


def default_selection(
    config: ExperimentConfig, *, session_count: int, seed: int
) -> SessionSelection:
    """What the menu comes pre-filled with: today's session, unchanged.

    The full design and the speaker ``speaker_selection`` would have picked
    anyway, so confirming without touching anything runs exactly the Adım 8
    session (§A12.3).
    """
    return SessionSelection(
        speaker_id=select_speaker(config, session_count=session_count, seed=seed),
        modules=tuple(config.enabled_modules()),
        practice="practice" in config.session.module_order,
        cross_hearing=config.cross_hearing_check.enabled,
    )


def select_speaker(config: ExperimentConfig, *, session_count: int, seed: int) -> int:
    """Which speaker this participant is tested with (§F.4).

    ``fixed`` pins one; ``balanced`` rotates by how many sessions have run so a
    fresh participant takes the next in turn; ``random`` draws one, seeded from
    the session seed so the choice is reproducible from the stored data.

    Since Adım 12 this is the menu's *pre-selection* rather than the last word;
    the operator can pick any prepared speaker over it.
    """
    selection = config.speaker_selection
    ids = config.stimulus_prep.speaker_ids()
    if selection.strategy == "fixed":
        assert selection.fixed_id is not None  # the schema guarantees it
        return selection.fixed_id
    if selection.strategy == "balanced":
        return ids[session_count % len(ids)]
    return random.Random(seed).choice(ids)


# -------------------------------------------------------------------- apply


def apply(config: ExperimentConfig, selection: SessionSelection) -> ExperimentConfig:
    """The design this session will actually run (§A12.1).

    Built by round-tripping the config through its own JSON form — the exact
    representation ``sessions.config_snapshot`` stores and
    ``config_from_snapshot`` reads back — so anything the schema would refuse is
    refused here, at the menu, rather than halfway through the session.
    """
    _check(config, selection)

    data = json.loads(config.model_dump_json())
    chosen = set(selection.modules)

    for name, module in data["modules"].items():
        module["enabled"] = bool(module["enabled"]) and name in chosen
    if selection.speaker_id is not None:
        for name in SPEAKER_MODULES:
            data["modules"][name]["speaker_id"] = selection.speaker_id
        data["speaker_selection"] = {
            "strategy": "fixed",
            "fixed_id": selection.speaker_id,
        }

    # Every enabled module has to be in module_order and nothing else may be
    # (the schema checks both), so the order is filtered rather than rebuilt —
    # the operator chose which modules run, not in what order.
    data["session"]["module_order"] = [
        name
        for name in data["session"]["module_order"]
        if (name in chosen) or (name == "practice" and selection.practice)
    ]
    data["cross_hearing_check"]["enabled"] = (
        config.cross_hearing_check.enabled and selection.cross_hearing
    )

    try:
        return ExperimentConfig.model_validate(data)
    except ValueError as exc:  # pragma: no cover - a schema change would land here
        raise SelectionError(
            f"Seçimden geçerli bir tasarım kurulamadı: {exc}"
        ) from exc


def _check(config: ExperimentConfig, selection: SessionSelection) -> None:
    if not selection.modules:
        raise SelectionError(
            "Hiç ölçüm modülü seçilmedi. Yalnız alıştırma ve çapraz dinleme "
            "koşan bir oturum veri üretmez."
        )

    known = set(config.modules.by_name())
    enabled = set(config.enabled_modules())

    unknown = sorted(set(selection.modules) - known)
    if unknown:
        raise SelectionError(
            f"Bilinmeyen modül: {', '.join(unknown)}. "
            f"Seçilebilecekler: {', '.join(sorted(known))}"
        )

    disabled = sorted(set(selection.modules) - enabled)
    if disabled:
        raise SelectionError(
            f"Config'te kapalı modül seçildi: {', '.join(disabled)}. "
            "Bir modülü koşmak için önce config/experiment.yaml'da açın — "
            "hangi modüllerin var olduğu tasarımın kendisidir, menü onun "
            "içinden seçer."
        )

    prepared = config.stimulus_prep.speaker_ids()
    if selection.speaker_id is not None and selection.speaker_id not in prepared:
        raise SelectionError(
            f"Hazır sette olmayan konuşmacı: {selection.speaker_id}. "
            f"Hazır olanlar: {', '.join(str(i) for i in prepared)}"
        )
