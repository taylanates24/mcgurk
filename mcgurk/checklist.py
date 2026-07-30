"""``python -m mcgurk.checklist`` — the operator's pre-session pre-flight.

steps.md §C Adım 8: a GREEN/RED check the operator runs before every
``data_collection`` session, readable by someone who does not know Python.  Any
RED line means a ``data_collection`` session must not start; the session flow
(Adım 8b) calls the same :func:`run_checks` and refuses to begin.

The checks split in two.  The **pure** ones — the photodiode offset, the
calibration file's age, the stimulus manifest, disk space, the latest backup —
read only files and never touch PsychoPy, so they run in CI and the
acceptance-criterion test ("RED on a missing or stale calibration blocks the
session") needs no hardware.  The **hardware** probes — the audio backend really
being PTB, the device being the expected one, the measured refresh matching the
config — open the speaker and the window, and are imported lazily so this module
imports without PsychoPy installed.

Nothing here is printed with a character outside cp1254: the Turkish Windows
console raises rather than degrades, and a checklist that crashes on its own
report is worse than no checklist (§Don'ts).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .config.calibration import CalibrationError, load_calibration
from .config.loader import ConfigError, load_config, resolve_path
from .config.schema import ExperimentConfig
from .db.backup import latest_backup
from .stimuli import verify as stimuli_verify

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Status(Enum):
    """A check's verdict.  The value is the word printed in the report."""

    GREEN = "YESIL"
    RED = "KIRMIZI"
    WARN = "UYARI"


@dataclass(frozen=True)
class Check:
    """One line of the report: a name, a verdict and a one-line explanation."""

    name: str
    status: Status
    detail: str = ""


def _green(name: str, detail: str = "") -> Check:
    return Check(name, Status.GREEN, detail)


def _red(name: str, detail: str = "") -> Check:
    return Check(name, Status.RED, detail)


def _warn(name: str, detail: str = "") -> Check:
    return Check(name, Status.WARN, detail)


# --------------------------------------------------------------- pure checks


def _check_mode(config: ExperimentConfig) -> Check:
    if config.experiment.mode == "data_collection":
        return _green("Mod", "veri toplama (data_collection)")
    # Development is a legitimate state to run the checklist in — the operator
    # is setting up.  It is not RED, because the RED gate is about starting a
    # data-collection session, and in development that gate does not apply.
    return _warn(
        "Mod",
        "development — kapılar uygulanmaz. Veri toplamak için config'te "
        "experiment.mode: data_collection yapın.",
    )


def _check_av_offset(config: ExperimentConfig) -> Check:
    offset = config.timing.system_av_offset_ms
    if offset is None:
        # Only reachable in development: the schema refuses a null offset in
        # data_collection, so a data-collection config never gets here empty.
        return _warn(
            "A/V gecikmesi (D)",
            "ölçülmedi (fotodiyot, docs/01_av_gecikme_olcumu.md). Motor 0 kabul "
            "eder; development'ta serbest.",
        )
    measured = config.timing.measured_on
    return _green(
        "A/V gecikmesi (D)",
        f"{offset:g} ms, ölçüm {measured.isoformat() if measured else '?'}",
    )


def _check_calibration(config: ExperimentConfig, project_root: Path) -> Check:
    max_age = config.checklist.calibration_max_age_days
    path = config.audio.calibration_file
    if path is None:
        # Development only — the schema requires a calibration file in
        # data_collection.
        return _warn(
            "Kalibrasyon",
            "dosya belirtilmemiş (development). Veri toplamak için "
            "docs/02_kalibrasyon.md çıktısı gerekir.",
        )

    resolved = resolve_path(project_root, path)
    try:
        calibration = load_calibration(resolved)
    except CalibrationError as exc:
        return _red("Kalibrasyon", str(exc))

    age_days = calibration.age_days()
    if age_days > max_age:
        return _red(
            "Kalibrasyon",
            f"{age_days:.0f} gün önce yapılmış, en fazla {max_age} gün. "
            "Yeniden kalibre edin (docs/02_kalibrasyon.md).",
        )
    return _green(
        "Kalibrasyon",
        f"{age_days:.0f} gün önce, K={calibration.k_mean_db:.1f} dB, "
        f"{resolved.name}",
    )


def _check_stimuli(config: ExperimentConfig, project_root: Path) -> Check:
    # deep=False: presence and checksums only.  A checklist has to finish in a
    # second, and the deep re-measurement is what tools/verify_stimuli.py is for.
    report = stimuli_verify.verify(config, project_root, deep=False)
    if report.failures == 0:
        return _green(
            "Uyaran seti", "manifest ve dosyalar yerinde (hızlı kontrol)."
        )
    return _red(
        "Uyaran seti",
        f"{report.failures} sorun. Ayrıntı: python tools/verify_stimuli.py",
    )


def _nearest_existing(path: Path) -> Path:
    """The closest ancestor of *path* that exists — for measuring free space.

    ``paths.data`` may not exist yet on a fresh machine; its volume still does,
    and that is what the free-space figure is about.
    """
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return Path(path.anchor or ".")


def _check_disk(config: ExperimentConfig, project_root: Path) -> Check:
    min_free_mb = config.checklist.min_free_disk_mb
    data_dir = resolve_path(project_root, config.paths.data)
    backups_dir = resolve_path(project_root, config.paths.backups)

    try:
        usage = shutil.disk_usage(_nearest_existing(data_dir))
    except OSError as exc:
        return _red("Disk ve yedek klasörü", f"disk alanı okunamadı: {exc}")

    free_mb = usage.free / (1024.0 * 1024.0)

    # The backup directory has to be writable — a session that cannot write its
    # closing backup has lost its safety net (steps.md Adım 1).
    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
        probe = backups_dir / ".checklist_write_test"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        return _red(
            "Disk ve yedek klasörü",
            f"yedek klasörüne yazılamıyor ({backups_dir}): {exc}",
        )

    if free_mb < min_free_mb:
        return _red(
            "Disk ve yedek klasörü",
            f"boş alan {free_mb:.0f} MB, en az {min_free_mb} MB gerekli.",
        )
    return _green(
        "Disk ve yedek klasörü",
        f"{free_mb:.0f} MB boş, yedek klasörü yazılabilir.",
    )


def _check_backup(config: ExperimentConfig, project_root: Path) -> Check:
    backups_dir = resolve_path(project_root, config.paths.backups)
    latest = latest_backup(backups_dir)
    if latest is None:
        # Not RED: the first session legitimately runs before any backup exists;
        # the backup is written when a session closes.
        return _warn(
            "Son yedek",
            "henüz yedek yok — ilk oturum kapanışında oluşacak.",
        )
    return _green("Son yedek", latest.name)


# ------------------------------------------------------------ hardware probes


def _hardware_checks(config: ExperimentConfig) -> list[Check]:
    """Probe the audio backend/device and the measured refresh.

    Lazily imported: this whole module has to import on a CI machine with no
    PsychoPy.  Both probes fail closed — a probe that raises becomes a RED line
    with the engine's own operator-facing message, never a traceback that ends
    the checklist before it has reported.
    """
    from .engine import EngineError

    checks: list[Check] = []

    # -- audio backend and device --
    try:
        from .engine.audio import open_speaker, require_ptb_backend
        from .engine.psychopy_prefs import configure_psychopy

        configure_psychopy(audio_device=config.audio.device)
        require_ptb_backend()
        speaker = open_speaker(
            device_name=config.audio.device,
            latency_class=config.timing.audio_latency_mode,
            sample_rate=config.audio.sample_rate,
        )
        name = str(getattr(speaker, "name", "") or "?")
        checks.append(
            _green("Ses backend ve aygıt", f"ptb, aygıt: {name}")
        )
    except EngineError as exc:
        logger.warning("Ses kontrolü başarısız: %s", exc)
        checks.append(_red("Ses backend ve aygıt", _first_line(str(exc))))

    # -- measured refresh vs expected --
    try:
        from .engine.window import measure_refresh_hz, open_window

        win = open_window(config.display)
        try:
            measured = measure_refresh_hz(win)
        finally:
            win.close()
        expected = config.display.expected_refresh_hz
        from .engine.scheduling import refresh_deviation_pct

        deviation = refresh_deviation_pct(measured, expected)
        detail = f"ölçülen {measured:.1f} Hz, beklenen {expected:g} Hz"
        # The same 2% the engine's check_refresh_hz uses; over it, the config's
        # expected_refresh_hz and the monitor disagree, and every SOA is off.
        if deviation <= 2.0:
            checks.append(_green("Yenileme hızı", detail))
        else:
            checks.append(
                _red("Yenileme hızı", f"{detail} (%{deviation:.1f} sapma).")
            )
    except EngineError as exc:
        logger.warning("Yenileme hızı kontrolü başarısız: %s", exc)
        checks.append(_red("Yenileme hızı", _first_line(str(exc))))

    return checks


def _first_line(text: str) -> str:
    """The first line of a multi-line engine message, for a one-line report."""
    return text.strip().splitlines()[0] if text.strip() else text


# ----------------------------------------------------------------- assembling


def run_checks(
    config: ExperimentConfig,
    project_root: Path,
    *,
    probe_hardware: bool = True,
) -> list[Check]:
    """Run every check and return the results, most useful line first.

    The pure checks always run; the hardware probes only when *probe_hardware*
    is set, so the design can be tested without a sound card or a screen.
    """
    checks = [
        _check_mode(config),
        _check_av_offset(config),
        _check_calibration(config, project_root),
        _check_stimuli(config, project_root),
        _check_disk(config, project_root),
        _check_backup(config, project_root),
    ]
    if probe_hardware:
        checks.extend(_hardware_checks(config))
    return checks


def any_red(checks: list[Check]) -> bool:
    """Whether any check is RED — the gate a data_collection session honours."""
    return any(check.status is Status.RED for check in checks)


def render(checks: list[Check], *, title: str) -> str:
    """Format the report for the operator's console (cp1254-safe)."""
    lines = [title, "=" * max(50, len(title))]
    for check in checks:
        lines.append(f"{check.status.value:<9}{check.name}")
        if check.detail:
            lines.append(f"         {check.detail}")
    reds = sum(1 for c in checks if c.status is Status.RED)
    warns = sum(1 for c in checks if c.status is Status.WARN)
    lines.append("-" * max(50, len(title)))
    if reds:
        lines.append(
            f"SONUÇ: {reds} KIRMIZI — data_collection oturumu başlatılamaz "
            f"({warns} uyarı)."
        )
    else:
        lines.append(f"SONUÇ: KIRMIZI yok ({warns} uyarı).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcgurk.checklist",
        description="Oturum öncesi YEŞİL/KIRMIZI kontrol (steps.md Adım 8)",
    )
    parser.add_argument("--config", type=Path, default=None, help="config dosyası")
    parser.add_argument(
        "--no-hardware",
        action="store_true",
        help="ses/pencere donanım kontrollerini atla (yalnızca dosya kontrolleri)",
    )
    args = parser.parse_args(argv)

    try:
        # check_filesystem=False: the file gates are reported as RED lines here,
        # not raised as a ConfigError.  The schema still applies its
        # data_collection gates (a null offset, an unset device), and those DO
        # stop the load — that is the config being genuinely unusable, and the
        # message names exactly which field is missing.
        config = load_config(
            args.config, project_root=_PROJECT_ROOT, check_filesystem=False
        )
    except ConfigError as exc:
        print(f"KIRMIZI  Config yüklenemedi:\n{exc}", file=sys.stderr)
        return 1

    checks = run_checks(
        config, _PROJECT_ROOT, probe_hardware=not args.no_hardware
    )
    title = (
        f"Oturum öncesi kontrol — {config.experiment.name} "
        f"v{config.experiment.version} ({config.experiment.mode})"
    )
    print(render(checks, title=title))
    return 1 if any_red(checks) else 0


if __name__ == "__main__":
    sys.exit(main())
