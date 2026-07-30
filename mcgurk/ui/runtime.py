"""Shared session runtime: opening the hardware and writing the session row.

The dev harness (``tools/run_module.py``) and the real session flow
(``mcgurk/ui/session.py``) both have to configure PsychoPy, open the speaker and
the window, measure the refresh rate and start the ``sessions`` row.  That setup
lives here so the two cannot drift: the harness is explicitly "not the session
flow" (its own docstring), but the way it opens the hardware has to be the same
one the session uses, or a timing difference could hide between them.

Top-level imports stay PsychoPy-free so this module imports on a CI machine; the
engine — and through it PsychoPy — is imported inside :func:`open_hardware`,
which only a machine with a screen and a sound card ever calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.schema import ExperimentConfig
from ..db.database import Database
from ..db.models import SessionRecord
from ..engine.scheduling import TimingParams
from ..provenance import collect as collect_provenance

logger = logging.getLogger(__name__)


@dataclass
class Hardware:
    """The opened hardware and the timing it runs at."""

    win: Any
    speaker: Any
    refresh_hz: float
    params: TimingParams


def open_hardware(config: ExperimentConfig) -> Hardware:
    """Configure PsychoPy, open the speaker and window, measure the refresh.

    Raises:
        EngineError: if the backend is not PTB, the device cannot be opened at
            the configured rate, or the refresh rate cannot be measured — every
            one of which is a broken timing chain, not a recoverable state.
    """
    from ..engine.audio import open_speaker, require_ptb_backend
    from ..engine.psychopy_prefs import configure_psychopy
    from ..engine.window import check_refresh_hz, measure_refresh_hz, open_window

    configure_psychopy(audio_device=config.audio.device)
    require_ptb_backend()
    speaker = open_speaker(
        device_name=config.audio.device,
        latency_class=config.timing.audio_latency_mode,
        sample_rate=config.audio.sample_rate,
    )
    win = open_window(config.display)
    try:
        refresh_hz = measure_refresh_hz(win)
        # Non-strict: a mismatch is logged, not raised.  The data_collection gate
        # for the refresh rate is the checklist's job (Adım 8a); here a
        # development run on a 60 Hz laptop must still be able to open.
        check_refresh_hz(refresh_hz, config.display)
    except Exception:
        # An unmeasurable refresh leaves the window open otherwise — close it
        # before the error unwinds, then re-raise (the caller reports it).
        win.close()
        raise
    params = TimingParams(
        frame_period_s=1.0 / refresh_hz,
        lead_frames=config.timing.lead_frames,
        system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
        dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
    )
    return Hardware(win=win, speaker=speaker, refresh_hz=refresh_hz, params=params)


def start_session(
    db: Database,
    config: ExperimentConfig,
    *,
    project_root: Path,
    participant_id: int,
    seed: int,
    hardware: Hardware,
    operator_notes: str = "",
) -> int:
    """Write the ``sessions`` row and return its id.

    The row carries the seed, the verbatim config snapshot and the environment,
    so the data can be interpreted years later without the working tree.
    """
    provenance = collect_provenance(project_root)
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=seed,
            config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
            config_mode=config.experiment.mode,
            app_version=provenance.app_version,
            git_commit=provenance.git_commit,
            psychopy_version=provenance.psychopy_version,
            python_version=provenance.python_version,
            os_name=provenance.os_name,
            audio_backend="ptb",
            audio_device=str(getattr(hardware.speaker, "name", "") or ""),
            measured_refresh_hz=hardware.refresh_hz,
            system_av_offset_ms=config.timing.system_av_offset_ms,
            operator_notes=operator_notes,
        )
    )
