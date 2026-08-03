"""The operator's session menu (steps.md ADIM 12c).

Shown after login and **before** the fullscreen window opens: which speaker this
participant is tested with, and which modules are run.  It comes pre-filled with
the full design and the speaker ``speaker_selection`` would have chosen, so
pressing OK without touching anything runs exactly the Adım 8 session (§A12.3).

The split is ``login.py``'s: :func:`build_form` and :func:`build_selection` are
pure and tested in CI (§A12.4), :func:`ask_session_setup` is the thin
``gui.DlgFromDict`` shell.  What the menu decides ends up in the config the
session starts with (``config.selection.apply``), so it travels with the data in
``sessions.config_snapshot`` rather than beside it.

A resumed session never sees this menu: it already has a design, and offering a
different one would contradict the snapshot it continues under.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from ..config.schema import ExperimentConfig
from ..config.selection import (
    SelectionError,
    SessionSelection,
    available_modules,
    available_speakers,
)

logger = logging.getLogger(__name__)

#: Field keys.  Turkish, and shared by the form builder and the parser so the
#: dialog and what reads it back cannot drift (the ``login.py`` rule).
FIELD_PARTICIPANT = "Katılımcı"
FIELD_PREVIOUS = "Önceki konuşmacısı"
FIELD_COUNTS = "Konuşmacı başına oturum"
FIELD_SPEAKER = "Konuşmacı"
FIELD_PRACTICE = "Alıştırma"
FIELD_CROSS = "Çapraz dinleme kontrolü"

_TITLE = "McGurk / SSD - Oturum kurulumu"

#: Answers to "this participant was tested with another speaker — sure?".  The
#: refusing answer is first because ``DlgFromDict`` preselects the first choice,
#: and the safe default for a question about mixing speakers is "no".
_CONFIRM_CHOICES = {
    "Hayır, menüye dön": False,
    "Evet, bu konuşmacıyla devam et": True,
}


@dataclass
class SetupForm:
    """The dialog's fields and the maps needed to read them back.

    ``fields`` is what ``DlgFromDict`` mutates in place, so after the dialog the
    same object holds the operator's answers — which is what makes
    :func:`build_selection` a pure function over it.
    """

    fields: OrderedDict[str, Any]
    fixed: list[str]
    tips: dict[str, str]
    speaker_by_label: dict[str, int]
    module_by_field: dict[str, str]
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def order(self) -> list[str]:
        return list(self.fields.keys())


def module_field_label(label: str, n_trials: int) -> str:
    """Checkbox text: what the module is, and what it costs."""
    return f"{label} — {n_trials} deneme"


def _speaker_lines(
    config: ExperimentConfig, counts: dict[int, int]
) -> tuple[dict[str, int], list[str]]:
    """Menu labels for every prepared speaker, and the order to show them in."""
    by_label: dict[str, int] = {}
    labels: list[str] = []
    for choice in available_speakers(config):
        n = counts.get(choice.speaker_id, 0)
        label = f"{choice.label} ({n} oturum)"
        by_label[label] = choice.speaker_id
        labels.append(label)
    return by_label, labels


def build_form(
    config: ExperimentConfig,
    default: SessionSelection,
    *,
    participant_code: str = "",
    previous_speaker_id: int | None = None,
    speaker_counts: dict[int, int] | None = None,
) -> SetupForm:
    """The menu, pre-filled with *default*.

    The speaker list is rotated so the pre-selected one is first: a
    ``DlgFromDict`` dropdown always selects its first choice, and a menu whose
    default is not what the config would have chosen is a menu that silently
    changes the design.
    """
    counts = speaker_counts or {}
    by_label, labels = _speaker_lines(config, counts)

    chosen_label = next(
        (label for label, sid in by_label.items() if sid == default.speaker_id),
        None,
    )
    if chosen_label is not None:
        labels = [chosen_label] + [label for label in labels if label != chosen_label]

    fields: OrderedDict[str, Any] = OrderedDict()
    fixed: list[str] = []
    if participant_code:
        fields[FIELD_PARTICIPANT] = participant_code
        fixed.append(FIELD_PARTICIPANT)
    if previous_speaker_id is not None:
        fields[FIELD_PREVIOUS] = str(previous_speaker_id)
        fixed.append(FIELD_PREVIOUS)
    fields[FIELD_COUNTS] = _counts_line(counts)
    fixed.append(FIELD_COUNTS)

    fields[FIELD_SPEAKER] = labels

    module_by_field: dict[str, str] = {}
    trial_counts: dict[str, int] = {}
    for choice in available_modules(config):
        key = module_field_label(choice.label, choice.n_trials)
        module_by_field[key] = choice.name
        trial_counts[key] = choice.n_trials
        fields[key] = choice.name in default.modules

    fields[FIELD_PRACTICE] = default.practice
    fields[FIELD_CROSS] = default.cross_hearing

    tips = {
        FIELD_SPEAKER: "Bu oturumun konuşmacısı. İlk sıradaki önceden seçilidir.",
        FIELD_PREVIOUS: "Bu katılımcının önceki oturumlarında sunulan konuşmacı.",
        FIELD_COUNTS: "Konuşmacıların bugüne kadar kaç oturumda kullanıldığı.",
    }
    return SetupForm(
        fields=fields,
        fixed=fixed,
        tips=tips,
        speaker_by_label=by_label,
        module_by_field=module_by_field,
        counts=trial_counts,
    )


def _counts_line(counts: dict[int, int]) -> str:
    if not counts:
        return "henüz oturum yok"
    return ", ".join(f"{sid}: {n}" for sid, n in sorted(counts.items()))


def build_selection(form: SetupForm) -> SessionSelection:
    """Read the operator's answers back out of *form*.

    Raises:
        SelectionError: with a Turkish message the dialog shows before re-asking.
    """
    raw_speaker = form.fields.get(FIELD_SPEAKER)
    if isinstance(raw_speaker, (list, tuple)):
        # Still the list of choices: the dialog has not written an answer back
        # yet.  An untouched dropdown is its first entry, which is the speaker
        # the form was pre-filled with — so reading an unanswered form gives the
        # default rather than an error.
        raw_speaker = raw_speaker[0] if raw_speaker else ""
    label = raw_speaker if isinstance(raw_speaker, str) else ""
    if label not in form.speaker_by_label:
        raise SelectionError(
            "Konuşmacı seçilmedi. Listeden bir konuşmacı seçin."
        )

    modules = tuple(
        name
        for key, name in form.module_by_field.items()
        if bool(form.fields.get(key))
    )
    if not modules:
        raise SelectionError(
            "Hiç ölçüm modülü seçilmedi. Yalnız alıştırma ve çapraz dinleme "
            "koşan bir oturum veri üretmez."
        )

    return SessionSelection(
        modules=modules,
        speaker_id=form.speaker_by_label[label],
        practice=bool(form.fields.get(FIELD_PRACTICE, True)),
        cross_hearing=bool(form.fields.get(FIELD_CROSS, True)),
    )


def selected_trial_total(form: SetupForm) -> int:
    """Trials the current answers add up to — for the log, not the dialog."""
    return sum(
        n for key, n in form.counts.items() if bool(form.fields.get(key))
    )


# --------------------------------------------------------------- the dialogs


def ask_session_setup(
    config: ExperimentConfig,
    default: SessionSelection,
    *,
    participant_code: str = "",
    previous_speaker_id: int | None = None,
    speaker_counts: dict[int, int] | None = None,
) -> SessionSelection | None:
    """Show the menu; return the selection, or None if the operator cancelled.

    Re-shown when the answers cannot be turned into a design, so a mis-click
    does not abort a session with the participant already seated — the same
    treatment ``show_login_dialog`` gives a typo.
    """
    from psychopy import gui

    form = build_form(
        config,
        default,
        participant_code=participant_code,
        previous_speaker_id=previous_speaker_id,
        speaker_counts=speaker_counts,
    )
    while True:
        dlg = gui.DlgFromDict(
            dictionary=form.fields,
            title=_TITLE,
            order=form.order,
            fixed=form.fixed,
            tip=form.tips,
        )
        if not dlg.OK:
            return None
        try:
            return build_selection(form)
        except SelectionError as exc:
            gui.DlgFromDict(
                OrderedDict([("Hata", str(exc))]), title="Geçersiz seçim"
            )


def confirm_speaker_change(*, previous_id: int, chosen_id: int) -> bool:
    """Ask before testing a participant with a different speaker than before.

    Allowed but never silent (user decision, 2026-08-03): measuring one
    participant's modules with two faces is a design problem, so the code makes
    it visible and the operator decides.
    """
    from psychopy import gui

    info: OrderedDict[str, Any] = OrderedDict(
        [
            (
                "Uyarı",
                f"Bu katılımcı daha önce konuşmacı {previous_id} ile ölçüldü; "
                f"şimdi konuşmacı {chosen_id} seçildi. Aynı katılımcının "
                "modüllerini farklı yüzlerle ölçmek denek-içi karşılaştırmayı "
                "zorlaştırır.",
            ),
            ("Devam edilsin mi?", list(_CONFIRM_CHOICES)),
        ]
    )
    dlg = gui.DlgFromDict(
        info, title="Farklı konuşmacı", order=list(info.keys()), fixed=["Uyarı"]
    )
    if not dlg.OK:
        return False
    return _CONFIRM_CHOICES.get(str(info["Devam edilsin mi?"]), False)
