"""Create a PsychoPy monitor profile for the experiment.

Run once on each machine:
    python scripts/setup_monitor.py

Adjust width_cm and distance_cm for your lab setup.
"""

from psychopy import monitors

MONITOR_NAME = "default"
WIDTH_PX = 1920
HEIGHT_PX = 1080
WIDTH_CM = 53.0       # physical screen width in cm (measure your monitor)
DISTANCE_CM = 60.0    # viewing distance in cm

mon = monitors.Monitor(MONITOR_NAME)
mon.setSizePix((WIDTH_PX, HEIGHT_PX))
mon.setWidth(WIDTH_CM)
mon.setDistance(DISTANCE_CM)
mon.save()

print(
    f"Monitor '{MONITOR_NAME}' saved: {WIDTH_PX}x{HEIGHT_PX}, "
    f"{WIDTH_CM}cm wide, {DISTANCE_CM}cm distance"
)
