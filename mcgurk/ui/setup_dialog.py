"""The operator's module menu at the start of a session (steps.md ADIM 12c).

Shown after login and **before** the fullscreen window opens: which modules this
session runs, plus practice and the cross-hearing check.  It comes pre-filled
with the full design, so pressing OK without touching anything runs exactly the
Adım 8 session (§A12.3).

**The speaker is not asked here** (Adım 12c-ii).  It is a property of the
installation rather than of the sitting — one participant is measured with one
face — so it is chosen in the operator panel's "Konuşmacı" tab, where it can be
picked from photographs, and written into ``config/experiment.yaml``.  What
remains per session is which modules run, which really does change from
participant to participant.  The session still *warns* when the config's speaker
is not the one this participant was measured with before.

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
)

logger = logging.getLogger(__name__)

#: Field keys.  Turkish, and shared by the form builder and the parser so the
#: dialog and what reads it back cannot drift (the ``login.py`` rule).
FIELD_PARTICIPANT = "Katılımcı"
FIELD_SPEAKER = "Konuşmacı (panelden)"
FIELD_PRACTICE = "Alıştırma"
FIELD_CROSS = "Çapraz dinleme kontrolü"

_TITLE = "McGurk / SSD - Oturum kurulumu"

#: Answers to "this participant was measured with another speaker — sure?".  The
#: refusing answer is first because ``DlgFromDict`` preselects the first choice,
#: and the safe default for a question about mixing speakers is "no".
_CONFIRM_CHOICES = {
    "Hayır, iptal et": False,
    "Evet, bu konuşmacıyla devam et": True,
}


@dataclass
class SetupForm:
    """The dialog's fields and the map needed to read them back.

    ``fields`` is what ``DlgFromDict`` mutates in place, so after the dialog the
    same object holds the operator's answers — which is what makes
    :func:`build_selection` a pure function over it.
    """

    fields: OrderedDict[str, Any]
    fixed: list[str]
    tips: dict[str, str]
    module_by_field: dict[str, str]
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def order(self) -> list[str]:
        return list(self.fields.keys())


def module_field_label(label: str, n_trials: int) -> str:
    """Checkbox text: what the module is, and what it costs."""
    return f"{label} — {n_trials} deneme"


def build_form(
    config: ExperimentConfig,
    default: SessionSelection,
    *,
    participant_code: str = "",
    speaker_label: str = "",
) -> SetupForm:
    """The menu, pre-filled with *default*."""
    fields: OrderedDict[str, Any] = OrderedDict()
    fixed: list[str] = []
    if participant_code:
        fields[FIELD_PARTICIPANT] = participant_code
        fixed.append(FIELD_PARTICIPANT)
    if speaker_label:
        # Shown, not asked: the operator has to see which face this session will
        # use, but changing it here would leave the panel and the config saying
        # something else.
        fields[FIELD_SPEAKER] = speaker_label
        fixed.append(FIELD_SPEAKER)

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
        FIELD_SPEAKER: (
            "Panelin 'Konuşmacı' sekmesinden seçilir; burada değiştirilemez."
        ),
    }
    return SetupForm(
        fields=fields,
        fixed=fixed,
        tips=tips,
        module_by_field=module_by_field,
        counts=trial_counts,
    )


def build_selection(form: SetupForm) -> SessionSelection:
    """Read the operator's answers back out of *form*.

    ``speaker_id`` stays None: the speaker is the config's, and this menu does
    not override it (Adım 12c-ii).

    Raises:
        SelectionError: with a Turkish message the dialog shows before re-asking.
    """
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
    speaker_label: str = "",
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
        speaker_label=speaker_label,
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
    """Ask before measuring a participant with a different speaker than before.

    Allowed but never silent (user decision, 2026-08-03): measuring one
    participant's modules with two faces is a design problem, so the code makes
    it visible and the operator decides.  Refusing cancels the session — the
    speaker is changed in the panel, not in the middle of a sitting.
    """
    from psychopy import gui

    info: OrderedDict[str, Any] = OrderedDict(
        [
            (
                "Uyarı",
                f"Bu katılımcı daha önce konuşmacı {previous_id} ile ölçüldü; "
                f"config şu an konuşmacı {chosen_id} diyor. Aynı katılımcının "
                "modüllerini farklı yüzlerle ölçmek denek-içi karşılaştırmayı "
                "zorlaştırır. Değiştirmek için: panel > Konuşmacı sekmesi.",
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
