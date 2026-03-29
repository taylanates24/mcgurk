"""Admin setup dialog: speaker and section selection using PsychoPy GUI."""

from collections import OrderedDict
from dataclasses import dataclass

from psychopy import gui

from ..config import get_active_sections
from ..utils.assets import Speaker, discover_speakers, get_assets_dir


@dataclass
class ExperimentSetup:
    """Result of admin setup dialog."""

    speaker: Speaker
    selected_sections: list[str]
    noise_enabled: bool
    audio_device: str  # empty string = system default


_SECTION_LABELS = {
    "mcgurk": "McGurk (Uyumsuz)",
    "av_congruent": "AV Uyumlu",
    "audio_only": "Sadece Ses",
    "visual_only": "Sadece Görüntü",
    "dichotic": "Dikotik Dinleme",
}


def show_admin_setup_dialog(
    config: dict,
) -> ExperimentSetup | None:
    """Show admin setup dialog for speaker and section selection.

    Returns ExperimentSetup or None if cancelled.
    """
    assets_dir = get_assets_dir(config)
    speakers = discover_speakers(assets_dir)

    if not speakers:
        info = {"Hata": f"'{assets_dir}' klasöründe konuşmacı bulunamadı!"}
        gui.DlgFromDict(info, title="Hata")
        return None

    # Build speaker choice list
    speaker_choices = [s.display_name for s in speakers]
    speaker_map = {s.display_name: s for s in speakers}

    # Discover audio output devices
    _DEFAULT_DEVICE = "Sistem varsayılanı"
    _system_default_device = ""
    audio_device_choices = [_DEFAULT_DEVICE]
    try:
        import sounddevice as sd
        _system_default_device = sd.query_devices(kind="output")["name"]
        for dev in sd.query_devices():
            if dev["max_output_channels"] > 0:
                audio_device_choices.append(dev["name"])
    except Exception:
        pass

    # Build dialog fields
    available_sections = get_active_sections(config)

    info = OrderedDict()
    info["Konuşmacı"] = speaker_choices
    info["Ses Çıkış Cihazı"] = audio_device_choices

    for section_key in available_sections:
        label = _SECTION_LABELS.get(section_key, section_key)
        info[label] = False

    info["Gürültülü koşul ekle"] = True

    dlg = gui.DlgFromDict(
        dictionary=info,
        title="McGurk Deney - Admin Ayarları",
        order=list(info.keys()),
    )

    if not dlg.OK:
        return None

    # Parse results
    speaker = speaker_map[info["Konuşmacı"]]

    # Map labels back to section keys
    label_to_key = {v: k for k, v in _SECTION_LABELS.items()}
    selected_sections = []
    for section_key in available_sections:
        label = _SECTION_LABELS.get(section_key, section_key)
        if info.get(label, False):
            selected_sections.append(section_key)

    noise_enabled = info["Gürültülü koşul ekle"]

    selected_device = info["Ses Çıkış Cihazı"]
    if selected_device == _DEFAULT_DEVICE:
        # Pass the actual system default name to ptb so it doesn't pick
        # an arbitrary device (ptb ignores the OS default without a hint).
        audio_device = _system_default_device
    else:
        audio_device = selected_device

    if not selected_sections:
        warn = {"Uyarı": "En az bir bölüm seçmelisiniz!"}
        gui.DlgFromDict(warn, title="Uyarı")
        return None

    return ExperimentSetup(
        speaker=speaker,
        selected_sections=selected_sections,
        noise_enabled=noise_enabled,
        audio_device=audio_device,
    )
