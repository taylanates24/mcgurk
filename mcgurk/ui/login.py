"""Participant entry for the new package (steps.md §C Adım 8).

Only an anonymous code is collected — never a name, surname or date of birth
(§A.6, KVKK).  The code<->identity mapping is kept by the operator outside this
repository and never synchronised to cloud storage.

The form values are turned into a :class:`Participant` by :func:`build_participant`,
which is pure — no PsychoPy — so the mapping and the validation are tested in CI.
:func:`show_login_dialog` is the thin ``gui.DlgFromDict`` shell around it.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from ..db.models import (
    GROUP_CONTROL,
    GROUP_SSD_LEFT,
    GROUP_SSD_RIGHT,
    Participant,
)

#: A participant code ends up in filenames and export headers, so restrict it to
#: characters that are safe on every filesystem.
_CODE_ALLOWED = re.compile(r"[^A-Za-z0-9_-]")
_CODE_MAX_LEN = 32

# Inclusion criterion from the method document (§4), also a database CHECK.
_AGE_MIN = 18
_AGE_MAX = 60

# Turkish field labels — the keys of the dialog dict and of the value map that
# build_participant reads.  One place, so the dialog and the parser cannot drift.
FIELD_CODE = "Katılımcı Kodu"
FIELD_AGE = "Yaş"
FIELD_SEX = "Cinsiyet"
FIELD_GROUP = "Grup"
FIELD_DEPRIVATION = "Deprivasyon (ay)"
FIELD_PTA_RIGHT = "PTA Sağ (dB)"
FIELD_PTA_LEFT = "PTA Sol (dB)"
FIELD_POSTLINGUAL = "Postlingual"
FIELD_NOTES = "Notlar"

#: Displayed option -> stored code.  The stored codes match the database CHECK
#: constraints (group_code, sex).
SEX_MAP = {
    "Kadın": "F",
    "Erkek": "M",
    "Diğer": "OTHER",
    "Belirtmek istemiyor": "UNDISCLOSED",
}
GROUP_MAP = {
    "Kontrol": GROUP_CONTROL,
    "SSD-Sağ": GROUP_SSD_RIGHT,
    "SSD-Sol": GROUP_SSD_LEFT,
}
POSTLINGUAL_MAP: dict[str, bool | None] = {
    "Bilinmiyor": None,
    "Evet": True,
    "Hayır": False,
}


class LoginError(ValueError):
    """The entered participant data is invalid — the dialog is re-shown."""


def sanitize_participant_code(raw: str) -> str:
    """Return *raw* reduced to a filesystem-safe, uppercase participant code.

    Everything outside ``[A-Za-z0-9_-]`` is dropped, so path separators and
    traversal sequences cannot survive.  Returns "" when nothing usable remains.
    """
    return _CODE_ALLOWED.sub("", str(raw).strip())[:_CODE_MAX_LEN].upper()


def _optional_int(value: Any, label: str) -> int | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        number = int(float(text))
    except (TypeError, ValueError) as exc:
        raise LoginError(f"{label} bir tam sayı olmalı (boş bırakılabilir).") from exc
    if number < 0:
        raise LoginError(f"{label} negatif olamaz.")
    return number


def _optional_float(value: Any, label: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise LoginError(f"{label} bir sayı olmalı (boş bırakılabilir).") from exc


def build_participant(fields: dict[str, Any]) -> Participant:
    """Turn the dialog's field values into a :class:`Participant`.

    Raises:
        LoginError: with a Turkish message the dialog shows before re-asking.
    """
    code = sanitize_participant_code(fields.get(FIELD_CODE, ""))
    if not code:
        raise LoginError(
            "Katılımcı kodu boş olamaz. Yalnızca harf, rakam, '-' ve '_' "
            "kullanın (örn. SSD-R-007)."
        )

    try:
        age = int(float(str(fields.get(FIELD_AGE, "")).strip()))
    except (TypeError, ValueError) as exc:
        raise LoginError("Yaş bir tam sayı olmalıdır.") from exc
    if not _AGE_MIN <= age <= _AGE_MAX:
        raise LoginError(
            f"Yaş {_AGE_MIN} ile {_AGE_MAX} arasında olmalıdır (dahil etme "
            "kriteri)."
        )

    sex_label = str(fields.get(FIELD_SEX, ""))
    if sex_label not in SEX_MAP:
        raise LoginError(f"Cinsiyet seçilmeli: {sorted(SEX_MAP)}")
    group_label = str(fields.get(FIELD_GROUP, ""))
    if group_label not in GROUP_MAP:
        raise LoginError(f"Grup seçilmeli: {sorted(GROUP_MAP)}")

    return Participant(
        participant_code=code,
        group_code=GROUP_MAP[group_label],
        age=age,
        sex=SEX_MAP[sex_label],
        deprivation_months=_optional_int(
            fields.get(FIELD_DEPRIVATION, ""), FIELD_DEPRIVATION
        ),
        pta_right_db=_optional_float(fields.get(FIELD_PTA_RIGHT, ""), FIELD_PTA_RIGHT),
        pta_left_db=_optional_float(fields.get(FIELD_PTA_LEFT, ""), FIELD_PTA_LEFT),
        postlingual=POSTLINGUAL_MAP.get(str(fields.get(FIELD_POSTLINGUAL, ""))),
        notes=str(fields.get(FIELD_NOTES, "")).strip(),
    )


def _default_fields() -> OrderedDict[str, Any]:
    """The dialog's fields and their initial values, in display order."""
    return OrderedDict(
        [
            (FIELD_CODE, ""),
            (FIELD_AGE, 25),
            (FIELD_SEX, list(SEX_MAP)),
            (FIELD_GROUP, list(GROUP_MAP)),
            (FIELD_DEPRIVATION, ""),
            (FIELD_PTA_RIGHT, ""),
            (FIELD_PTA_LEFT, ""),
            (FIELD_POSTLINGUAL, list(POSTLINGUAL_MAP)),
            (FIELD_NOTES, ""),
        ]
    )


def show_login_dialog() -> Participant | None:
    """Show the participant form; return a Participant, or None if cancelled.

    The dialog is re-shown when the entered data is invalid, so a typo does not
    abort the session.  ``DlgFromDict`` is used rather than ``gui.Dlg`` because
    the latter has field-parsing problems in this PsychoPy version (CLAUDE.md).
    """
    from psychopy import gui

    info = _default_fields()
    while True:
        dlg = gui.DlgFromDict(
            dictionary=info,
            title="McGurk / SSD - Katılımcı Bilgileri",
            order=list(info.keys()),
        )
        if not dlg.OK:
            return None
        try:
            return build_participant(info)
        except LoginError as exc:
            gui.DlgFromDict(
                OrderedDict([("Hata", str(exc))]), title="Geçersiz giriş"
            )
            # Loop and re-show the form; the operator's entries are preserved
            # because DlgFromDict rewrote them into `info` in place.


#: Operator's choice when a half-finished session is found (Adım 8c-i).
_RESUME_CHOICES = {
    "Devam et (kaldığı yerden)": "resume",
    "Yeni oturum başlat": "new",
    "İptal": "cancel",
}


def ask_resume_or_new(*, session_id: int, started_at: str, status: str) -> str:
    """Ask the operator what to do with a resumable session.

    Returns ``"resume"``, ``"new"`` or ``"cancel"`` (cancel also on close).
    """
    from psychopy import gui

    info: OrderedDict[str, Any] = OrderedDict(
        [
            ("Yarım oturum", f"#{session_id} — {started_at} ({status})"),
            ("Ne yapmak istersiniz?", list(_RESUME_CHOICES)),
        ]
    )
    dlg = gui.DlgFromDict(
        info, title="Kaldığı yerden devam?", order=list(info.keys())
    )
    if not dlg.OK:
        return "cancel"
    return _RESUME_CHOICES.get(str(info["Ne yapmak istersiniz?"]), "cancel")
