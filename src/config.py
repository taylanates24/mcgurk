"""Configuration loader for the McGurk experiment."""

from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load experiment configuration from a YAML file.

    Args:
        path: Path to config file. Uses project root config.yaml if None.

    Returns:
        Configuration dictionary.
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def get_active_sections(config: dict[str, Any]) -> list[str]:
    """Return list of section names that are enabled in config."""
    return [name for name, enabled in config.get("sections", {}).items() if enabled]


def get_syllables(config: dict[str, Any]) -> list[str]:
    """Return list of syllables from config."""
    return config.get("syllables", ["ba", "da", "ga"])


def get_response_key_map(config: dict[str, Any]) -> dict[str, str]:
    """Return mapping of syllable -> keyboard key."""
    return config.get("response_keys", {"ba": "1", "da": "2", "ga": "3"})


def get_key_to_syllable_map(config: dict[str, Any]) -> dict[str, str]:
    """Return inverse mapping: keyboard key -> syllable."""
    return {v: k for k, v in get_response_key_map(config).items()}
