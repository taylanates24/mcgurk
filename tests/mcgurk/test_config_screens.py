"""Session screen texts: shipped config is complete, gaps fail loudly (Adım 8a).

Every participant-facing string lives in the config (§A.9), and the coverage
rule — an instruction screen for every enabled module, none for a module that is
never presented — is enforced at load so a missing or dangling screen is caught
before anyone sits down, not mid-session.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcgurk.config import ConfigError, load_config


def _load(write_config, data: dict[str, Any]):
    return load_config(write_config(data), check_filesystem=False)


def test_shipped_config_covers_every_enabled_module() -> None:
    config = load_config(check_filesystem=False)
    presented = config.enabled_modules()
    assert set(config.screens.module_instructions) == set(presented)
    # cross_hearing_check is enabled in the shipped config, so its screen is set.
    assert config.cross_hearing_check.enabled
    assert config.screens.cross_hearing_intro is not None


def test_break_field_reads_from_its_yaml_alias() -> None:
    # ``break`` is a keyword, so the field is break_screen with an alias.
    config = load_config(check_filesystem=False)
    assert config.screens.break_screen.strip()


def test_missing_module_instruction_is_rejected(write_config, config_dict) -> None:
    del config_dict["screens"]["module_instructions"]["gin"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    message = str(exc.value)
    assert "module_instructions" in message
    assert "gin" in message


def test_instruction_for_an_unpresented_module_is_rejected(
    write_config, config_dict
) -> None:
    # practice has its own screens (practice_intro/end); it is not a measurement
    # module, so an instruction keyed to it is text nobody reaches.
    config_dict["screens"]["module_instructions"]["practice"] = "x"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "practice" in str(exc.value)


def test_empty_instruction_text_is_rejected(write_config, config_dict) -> None:
    config_dict["screens"]["module_instructions"]["mcgurk"] = ""
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "mcgurk" in str(exc.value)


def test_unknown_screens_field_is_rejected(write_config, config_dict) -> None:
    config_dict["screens"]["reklam"] = "al bir tane"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "reklam" in str(exc.value)


def test_cross_hearing_intro_required_when_the_check_is_enabled(
    write_config, config_dict
) -> None:
    config_dict["cross_hearing_check"]["enabled"] = True
    del config_dict["screens"]["cross_hearing_intro"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "cross_hearing_intro" in str(exc.value)


def test_cross_hearing_intro_optional_when_the_check_is_disabled(
    write_config, config_dict
) -> None:
    config_dict["cross_hearing_check"]["enabled"] = False
    del config_dict["screens"]["cross_hearing_intro"]
    config = _load(write_config, config_dict)
    assert config.screens.cross_hearing_intro is None
    assert not config.cross_hearing_check.enabled
