"""The ``stimulus_prep`` section and its cross-checks against the design.

Its real job is to make two things impossible: a ``speaker_id`` that names no
recording folder, and a token in the design that was never prepared.  Both
used to surface as a missing file — at best when the stimuli were built, at
worst halfway through a session.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.config.schema import ExperimentConfig


def _build(data: dict[str, Any]) -> ExperimentConfig:
    return ExperimentConfig.model_validate(data)


def test_the_shipped_config_declares_its_speakers(config_dict: dict[str, Any]) -> None:
    config = _build(config_dict)
    assert config.stimulus_prep.speaker_ids() == [1, 2, 3, 4, 5, 6, 7, 8]
    assert config.stimulus_prep.source_for(2).as_posix().endswith("speaker_2_male")


def test_every_speaker_has_a_name_the_operator_can_read(
    config_dict: dict[str, Any]
) -> None:
    """The session menu (Adım 12) lists labels; an id is not a face.

    Adding a ninth speaker without one would put a blank row in the menu.
    """
    for speaker in _build(config_dict).stimulus_prep.speakers:
        assert speaker.label, f"konuşmacı {speaker.id} etiketsiz"


def test_an_unknown_speaker_id_is_named(config_dict: dict[str, Any]) -> None:
    config_dict["modules"]["mcgurk"]["speaker_id"] = 99
    with pytest.raises(ValueError, match="olmayan speaker_id"):
        _build(config_dict)


def test_a_token_with_no_recording_is_named(config_dict: dict[str, Any]) -> None:
    # A congruent (control) pair, so the categorisation-map validator — which
    # would otherwise catch this first — is not what fires.
    config_dict["modules"]["mcgurk"]["av_pairs"][2]["visual"] = "pa"
    with pytest.raises(ValueError, match="olmayan token"):
        _build(config_dict)


def test_a_dichotic_token_with_no_recording_is_named(
    config_dict: dict[str, Any]
) -> None:
    config_dict["modules"]["dichotic"]["pairs"][0]["left"] = "ka"
    with pytest.raises(ValueError, match="modules.dichotic"):
        _build(config_dict)


def test_a_disabled_module_does_not_constrain_the_stimulus_set(
    config_dict: dict[str, Any]
) -> None:
    """Turning a module off should not force its stimuli to exist."""
    config_dict["modules"]["dichotic"]["enabled"] = False
    config_dict["modules"]["dichotic"]["pairs"][0]["left"] = "ka"
    config_dict["session"]["module_order"].remove("dichotic")
    assert "dichotic" not in _build(config_dict).required_tokens()


def test_duplicate_speaker_ids_are_rejected(config_dict: dict[str, Any]) -> None:
    config_dict["stimulus_prep"]["speakers"][1]["id"] = 1
    with pytest.raises(ValueError, match="tekrarlı id"):
        _build(config_dict)


def test_duplicate_source_folders_are_rejected(config_dict: dict[str, Any]) -> None:
    speakers = config_dict["stimulus_prep"]["speakers"]
    speakers[1]["source"] = speakers[0]["source"]
    with pytest.raises(ValueError, match="tekrarlı kaynak"):
        _build(config_dict)


def test_an_inverted_gin_band_is_rejected(config_dict: dict[str, Any]) -> None:
    config_dict["stimulus_prep"]["gin"]["bandwidth_hz"] = [8000.0, 100.0]
    with pytest.raises(ValueError, match="bandwidth_hz"):
        _build(config_dict)


def test_a_segment_ramp_longer_than_the_gap_margin_is_rejected(
    config_dict: dict[str, Any]
) -> None:
    """A gap inside the segment's own fade would be quieter than the others.

    Its detectability — which is the entire measurement — would then depend on
    where it happened to land in the segment.
    """
    config_dict["stimulus_prep"]["gin"]["segment_ramp_ms"] = 1500.0
    config_dict["modules"]["gin"]["min_gap_separation_s"] = 1.0
    with pytest.raises(ValueError, match="segment_ramp_ms"):
        _build(config_dict)


def test_the_shipped_segment_ramp_clears_the_first_possible_gap(
    config_dict: dict[str, Any]
) -> None:
    config = _build(config_dict)
    assert (
        config.stimulus_prep.gin.segment_ramp_ms / 1000.0
        <= config.modules.gin.min_gap_separation_s
    )


def test_an_unknown_field_is_still_an_error(config_dict: dict[str, Any]) -> None:
    config_dict["stimulus_prep"]["definitely_not_a_field"] = 1
    with pytest.raises(ValueError):
        _build(config_dict)


def test_snrs_come_from_the_modules_not_from_a_second_list(
    config_dict: dict[str, Any]
) -> None:
    """One list, so the prepared noise cannot disagree with the design."""
    config_dict["modules"]["mcgurk"]["noise_conditions"] = [None, 5.0]
    config_dict["modules"]["avsr"]["noise_conditions"] = [None, 0.0, 5.0]
    assert _build(config_dict).required_snrs() == [0.0, 5.0]


def test_no_noise_condition_means_no_snr(config_dict: dict[str, Any]) -> None:
    config_dict["modules"]["mcgurk"]["noise_conditions"] = [None]
    config_dict["modules"]["avsr"]["noise_conditions"] = [None]
    assert _build(config_dict).required_snrs() == []


def test_the_loader_reports_the_field_path(
    config_dict: dict[str, Any], write_config
) -> None:
    config_dict["stimulus_prep"]["audio"]["bit_depth"] = 8
    with pytest.raises(ConfigError, match="bit_depth"):
        load_config(write_config(config_dict), check_filesystem=False)
