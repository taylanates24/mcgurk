"""List available audio output devices for PsychoPy's ptb backend.

Run with:
    python scripts/list_audio_devices.py

Copy the desired device name into config.yaml as:
    audio_device: "Device Name Here"
"""

from psychopy import prefs
prefs.hardware["audioLib"] = ["ptb", "sounddevice", "pygame"]

import traceback
import sys

print(f"Python: {sys.executable}\n")

print("=== sounddevice ===")
try:
    import sounddevice as sd
    print(f"sounddevice version: {sd.__version__}")
    devs = sd.query_devices()
    output_devs = [d for d in devs if d["max_output_channels"] > 0]
    if output_devs:
        for dev in output_devs:
            print(f"  [{dev['index']}] {dev['name']}")
    else:
        print("  (hiç çıkış cihazı bulunamadı)")
    print(f"\n  Varsayılan çıkış: {sd.query_devices(kind='output')['name']}")
except Exception:
    traceback.print_exc()

print("\n=== psychtoolbox ===")
try:
    import psychtoolbox as ptb
    devices = ptb.GetDevices(3)
    for dev in devices:
        print(f"  [{dev.get('DeviceIndex','?')}] {dev.get('DeviceName', dev)}")
except Exception:
    traceback.print_exc()
