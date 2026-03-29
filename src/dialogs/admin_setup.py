"""Admin setup dialog: speaker and section selection using PsychoPy GUI."""

from collections import OrderedDict
from dataclasses import dataclass, field

from psychopy import gui

from ..config import get_active_sections
from ..utils.assets import Speaker, discover_speakers, get_assets_dir


# Sections that support noise (visual_only and dichotic are excluded)
_NOISE_COMPATIBLE = {"mcgurk", "av_congruent", "audio_only"}

_SECTION_LABELS = {
    "mcgurk": "McGurk (Uyumsuz)",
    "av_congruent": "AV Uyumlu",
    "audio_only": "Sadece Ses",
    "visual_only": "Sadece Görüntü",
    "dichotic": "Dikotik Dinleme",
}


@dataclass
class ExperimentSetup:
    """Result of admin setup dialog."""

    speaker: Speaker
    selected_sections: list[str]
    noisy_sections: list[str]   # subset of selected_sections that also run in noisy mode
    audio_device: str           # empty string = system default


def show_admin_setup_dialog(config: dict) -> ExperimentSetup | None:
    """Show admin setup dialog (two steps if noise is requested).

    Returns ExperimentSetup or None if cancelled.
    """
    assets_dir = get_assets_dir(config)
    speakers = discover_speakers(assets_dir)

    if not speakers:
        info = {"Hata": f"'{assets_dir}' klasöründe konuşmacı bulunamadı!"}
        gui.DlgFromDict(info, title="Hata")
        return None

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

    available_sections = get_active_sections(config)

    # ------------------------------------------------------------------
    # Dialog 1: speaker, audio device, sections, noise toggle
    # ------------------------------------------------------------------
    info = OrderedDict()
    info["Konuşmacı"] = speaker_choices
    info["Ses Çıkış Cihazı"] = audio_device_choices
    for section_key in available_sections:
        info[_SECTION_LABELS.get(section_key, section_key)] = False
    info["Gürültülü koşul ekle"] = False

    dlg = gui.DlgFromDict(
        dictionary=info,
        title="McGurk Deney - Admin Ayarları",
        order=list(info.keys()),
    )
    if not dlg.OK:
        return None

    speaker = speaker_map[info["Konuşmacı"]]

    selected_sections = [
        key for key in available_sections
        if info.get(_SECTION_LABELS.get(key, key), False)
    ]

    selected_device = info["Ses Çıkış Cihazı"]
    audio_device = (
        _system_default_device if selected_device == _DEFAULT_DEVICE else selected_device
    )

    noise_requested = bool(info["Gürültülü koşul ekle"])

    # ------------------------------------------------------------------
    # Dialog 2 (only if noise requested): which sections run noisy?
    # ------------------------------------------------------------------
    noisy_sections: list[str] = []

    if noise_requested:
        # Offer all noise-compatible sections regardless of what was checked
        # in dialog 1 — admin may want noisy-only runs too.
        noise_candidates = [s for s in available_sections if s in _NOISE_COMPATIBLE]

        noise_info = OrderedDict()
        for key in noise_candidates:
            noise_info[_SECTION_LABELS.get(key, key)] = False

        noise_dlg = gui.DlgFromDict(
            dictionary=noise_info,
            title="Gürültülü Koşul — Hangi bölümler?",
            order=list(noise_info.keys()),
        )
        if not noise_dlg.OK:
            return None

        noisy_sections = [
            key for key in noise_candidates
            if noise_info.get(_SECTION_LABELS.get(key, key), False)
        ]

    return ExperimentSetup(
        speaker=speaker,
        selected_sections=selected_sections,
        noisy_sections=noisy_sections,
        audio_device=audio_device,
    )
