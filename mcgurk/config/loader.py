"""Loading, validating and summarising ``config/experiment.yaml``."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from .calibration import CalibrationError, load_calibration
from .schema import ExperimentConfig
from .word_lists import WordListError, load_word_list

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/experiment.yaml")


class ConfigError(RuntimeError):
    """Raised when the configuration is missing, unparseable or invalid."""


def resolve_path(project_root: Path, path: Path) -> Path:
    """Resolve *path* against the project root unless it is already absolute."""
    return path if path.is_absolute() else (project_root / path)


def _format_validation_error(exc: ValidationError) -> str:
    """Render a pydantic error as a flat, readable list of field problems."""
    lines = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "(kök)"
        lines.append(f"  - {location}: {error['msg']}")
    return "\n".join(lines)


def load_config(
    path: Path | str | None = None,
    *,
    project_root: Path | str | None = None,
    check_filesystem: bool = True,
) -> ExperimentConfig:
    """Load and validate the experiment configuration.

    Args:
        path: Config file. Defaults to ``<project_root>/config/experiment.yaml``.
        project_root: Root that relative paths in the config resolve against.
            Defaults to the repository root (two levels above this file).
        check_filesystem: Run the ``data_collection`` file checks. Turn off in
            tests that only exercise the schema.

    Raises:
        ConfigError: for every failure mode, with the field paths spelled out.
    """
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
    config_path = Path(path) if path else root / DEFAULT_CONFIG_PATH

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Config dosyası okunamadı: {config_path} ({exc})") from exc

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config geçerli YAML değil: {config_path}\n{exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Config bir eşleme (mapping) olmalı: {config_path}")

    try:
        config = ExperimentConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(
            f"Config doğrulaması başarısız: {config_path}\n"
            f"{_format_validation_error(exc)}"
        ) from exc

    _resolve_word_lists(config, root, config_path)

    if check_filesystem:
        _check_filesystem(config, root, config_path)

    return config


def _resolve_word_lists(
    config: ExperimentConfig, root: Path, config_path: Path
) -> None:
    """Read the AVSR word lists and re-check the design against them.

    Unconditional, unlike the ``data_collection`` gates below: without the
    items the module's trial count is not computable at all, so a word set that
    cannot be read has to fail here rather than produce a smaller design.
    Disabled sets are left alone — a list that is not being presented does not
    have to exist yet, which is exactly the state §F.2 is in.
    """
    if not config.modules.avsr.enabled:
        return

    resolved = False
    for index, stimulus_set in enumerate(config.modules.avsr.stimulus_sets):
        if not stimulus_set.enabled or stimulus_set.type != "word":
            continue
        assert stimulus_set.word_list is not None  # the schema guarantees it
        path = resolve_path(root, stimulus_set.word_list)
        try:
            word_list = load_word_list(path)
        except WordListError as exc:
            raise ConfigError(
                f"modules.avsr.stimulus_sets[{index}] okunamadı: {config_path}\n{exc}"
            ) from exc
        stimulus_set.attach_items(word_list.items)
        resolved = True
        logger.info(
            "AVSR kelime listesi: %s (%d kelime, %s)",
            word_list.name,
            len(word_list.items),
            path,
        )

    if not resolved:
        return

    # The schema could not check these words: it never touches the disk, so at
    # validation time the set reported no items at all.
    problems = config.design_problems()
    if problems:
        raise ConfigError(
            "Kelime listesi tasarımla uyuşmuyor:\n  - "
            + "\n  - ".join(problems)
            + "\n  Kelimeler stimulus_prep.tokens'a eklenip "
            "'python tools/prepare_stimuli.py' ile hazırlanmalı."
        )


def _check_filesystem(
    config: ExperimentConfig, root: Path, config_path: Path
) -> None:
    """Filesystem gates that the schema itself cannot check.

    Only ``data_collection`` is gated.  Development runs are expected to have
    no calibration and an incomplete stimulus tree.
    """
    if config.experiment.mode != "data_collection":
        return

    problems: list[str] = []

    stimuli_dir = resolve_path(root, config.paths.stimuli)
    if not stimuli_dir.is_dir():
        problems.append(f"paths.stimuli dizini yok: {stimuli_dir}")

    # The schema already rejected a null calibration_file in this mode.
    assert config.audio.calibration_file is not None
    calibration_path = resolve_path(root, config.audio.calibration_file)
    try:
        calibration = load_calibration(calibration_path)
    except CalibrationError as exc:
        problems.append(str(exc))
    else:
        logger.info(
            "Kalibrasyon: %s (%.1f gün önce), K=%.2f dB",
            calibration.measured_on.isoformat(timespec="seconds"),
            calibration.age_days(),
            calibration.k_mean_db,
        )

    if problems:
        raise ConfigError(
            f"mode: data_collection dosya kontrolleri başarısız: {config_path}\n  - "
            + "\n  - ".join(problems)
        )


def summarise_design(config: ExperimentConfig) -> str:
    """Human-readable trial counts and duration estimate.

    steps.md §G: this is the output the trial-count decision (§F.1) gets made
    against, so it is printed every time the config loads.
    """
    counts = config.trial_counts()
    lines = [
        f"Tasarım özeti — {config.experiment.name} v{config.experiment.version} "
        f"({config.experiment.mode})",
        f"{'Modül':<16}{'Deneme':>8}{'Tahmini süre':>16}",
        "-" * 40,
    ]

    modules = config.modules.by_name()
    for name, count in counts.items():
        if name in modules and modules[name].enabled:
            seconds = modules[name].estimated_duration_s()
            duration = f"{seconds / 60:.1f} dk"
        else:
            duration = "—"
        lines.append(f"{name:<16}{count:>8}{duration:>16}")

    total_trials = sum(counts.values())
    total_minutes = config.estimated_duration_s() / 60
    lines.append("-" * 40)
    lines.append(f"{'TOPLAM':<16}{total_trials:>8}{f'{total_minutes:.1f} dk':>16}")
    lines.append(
        "Not: süre tahmini estimated_trial_duration_s değerlerinden gelir, "
        "ölçüm değildir."
    )
    return "\n".join(lines)
