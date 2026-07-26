"""Participant entry dialog using PsychoPy GUI.

Only an anonymous participant code is collected — never a name, surname or
date of birth (KVKK).  The code↔identity mapping is kept by the operator
outside this repository and must never be synchronised to cloud storage.
"""

import re
from collections import OrderedDict
from typing import Any

from psychopy import gui

from ..data.models import Participant

# A participant code ends up in filenames and export headers, so restrict it
# to characters that are safe on every filesystem.
_CODE_ALLOWED = re.compile(r"[^A-Za-z0-9_-]")
_CODE_MAX_LEN = 32


def sanitize_participant_code(raw: str) -> str:
    """Return *raw* reduced to a filesystem-safe, uppercase participant code.

    Everything outside ``[A-Za-z0-9_-]`` is dropped, so path separators and
    traversal sequences cannot survive.  Returns an empty string when nothing
    usable remains — callers must treat that as invalid input.
    """
    return _CODE_ALLOWED.sub("", raw.strip())[:_CODE_MAX_LEN].upper()


def _show_error(message: str) -> None:
    """Show a blocking error dialog."""
    gui.DlgFromDict(OrderedDict([("Hata", message)]), title="Geçersiz giriş")


def show_login_dialog() -> Participant | None:
    """Show the participant form and return a Participant, or None if cancelled.

    The dialog is re-shown when the entered data is invalid, so a typo does
    not abort the session.
    """
    # DlgFromDict rewrites the values in place with whatever the operator
    # entered, so the field types are heterogeneous by design.
    info: OrderedDict[str, Any] = OrderedDict(
        [
            ("Katılımcı Kodu", ""),
            ("Yaş", 25),
            ("Cinsiyet", ["Kadın", "Erkek"]),
            ("Grup", ["Kontrol", "SSD-Sağ", "SSD-Sol"]),
            ("Notlar", ""),
        ]
    )

    group_map = {
        "Kontrol": "control",
        "SSD-Sağ": "SSD-right",
        "SSD-Sol": "SSD-left",
    }
    gender_map = {"Kadın": "female", "Erkek": "male"}

    while True:
        dlg = gui.DlgFromDict(
            dictionary=info,
            title="McGurk Deney - Katılımcı Bilgileri",
            order=list(info.keys()),
        )

        if not dlg.OK:
            return None

        code = sanitize_participant_code(str(info["Katılımcı Kodu"]))
        if not code:
            _show_error(
                "Katılımcı kodu boş olamaz. Yalnızca harf, rakam, '-' ve '_' "
                "kullanın (örn. SSD-R-007)."
            )
            continue

        try:
            age = int(info["Yaş"])
        except (TypeError, ValueError):
            _show_error("Yaş bir tam sayı olmalıdır.")
            continue

        if not 18 <= age <= 60:
            # Inclusion criterion from the method document (§4): 18–60 years.
            _show_error("Yaş 18 ile 60 arasında olmalıdır (dahil etme kriteri).")
            continue

        gender = str(info["Cinsiyet"])
        group = str(info["Grup"])

        return Participant(
            participant_code=code,
            age=age,
            gender=gender_map.get(gender, gender),
            group=group_map.get(group, group),
            notes=str(info["Notlar"]).strip(),
        )
