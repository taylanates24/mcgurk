"""Login/demographics dialog using PsychoPy GUI."""

from collections import OrderedDict

from psychopy import gui

from ..data.models import Participant


def show_login_dialog() -> Participant | None:
    """Show a demographics form and return a Participant, or None if cancelled."""
    info = OrderedDict(
        [
            ("Ad Soyad", ""),
            ("Yaş", 25),
            ("Cinsiyet", ["Kadın", "Erkek"]),
            ("Grup", ["Kontrol", "SSD-Sağ", "SSD-Sol"]),
            ("Notlar", ""),
        ]
    )

    dlg = gui.DlgFromDict(
        dictionary=info,
        title="McGurk Deney - Katılımcı Bilgileri",
        order=list(info.keys()),
    )

    if not dlg.OK:
        return None

    group_map = {
        "Kontrol": "control",
        "SSD-Sağ": "SSD-right",
        "SSD-Sol": "SSD-left",
    }
    gender_map = {"Kadın": "female", "Erkek": "male"}

    return Participant(
        name=str(info["Ad Soyad"]).strip(),
        age=int(info["Yaş"]),
        gender=gender_map.get(info["Cinsiyet"], info["Cinsiyet"]),
        group=group_map.get(info["Grup"], info["Grup"]),
        notes=str(info["Notlar"]).strip(),
    )
