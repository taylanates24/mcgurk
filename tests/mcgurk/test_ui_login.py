"""Participant form -> Participant mapping (Adım 8b-i).

The gui is not tested — build_participant is, because it is where the Turkish
labels become the database's group/sex codes and where the age criterion is
enforced.  A wrong mapping here would mis-group a participant silently.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcgurk.ui.login import (
    FIELD_AGE,
    FIELD_CODE,
    FIELD_DEPRIVATION,
    FIELD_GROUP,
    FIELD_POSTLINGUAL,
    FIELD_PTA_LEFT,
    FIELD_PTA_RIGHT,
    FIELD_SEX,
    LoginError,
    build_participant,
    sanitize_participant_code,
)


def _fields(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        FIELD_CODE: "SSD-R-007",
        FIELD_AGE: 34,
        FIELD_SEX: "Erkek",
        FIELD_GROUP: "SSD-Sağ",
        FIELD_DEPRIVATION: "18",
        FIELD_PTA_RIGHT: "72.5",
        FIELD_PTA_LEFT: "8",
        FIELD_POSTLINGUAL: "Evet",
        "Notlar": "  pilot  ",
    }
    base.update(overrides)
    return base


def test_full_form_maps_to_a_participant() -> None:
    participant = build_participant(_fields())
    assert participant.participant_code == "SSD-R-007"
    assert participant.group_code == "SSD_R"
    assert participant.sex == "M"
    assert participant.age == 34
    assert participant.deprivation_months == 18
    assert participant.pta_right_db == 72.5
    assert participant.pta_left_db == 8.0
    assert participant.postlingual is True
    assert participant.notes == "pilot"


def test_group_and_sex_codes() -> None:
    assert build_participant(_fields(**{FIELD_GROUP: "Kontrol"})).group_code == "CTRL"
    assert build_participant(_fields(**{FIELD_GROUP: "SSD-Sol"})).group_code == "SSD_L"
    assert build_participant(_fields(**{FIELD_SEX: "Kadın"})).sex == "F"
    assert build_participant(_fields(**{FIELD_SEX: "Diğer"})).sex == "OTHER"
    assert (
        build_participant(_fields(**{FIELD_SEX: "Belirtmek istemiyor"})).sex
        == "UNDISCLOSED"
    )


def test_optional_fields_default_to_none() -> None:
    participant = build_participant(
        _fields(
            **{
                FIELD_DEPRIVATION: "",
                FIELD_PTA_RIGHT: "",
                FIELD_PTA_LEFT: "",
                FIELD_POSTLINGUAL: "Bilinmiyor",
            }
        )
    )
    assert participant.deprivation_months is None
    assert participant.pta_right_db is None
    assert participant.pta_left_db is None
    assert participant.postlingual is None


def test_code_is_sanitized() -> None:
    assert sanitize_participant_code("  ssd/r 007..  ") == "SSDR007"
    assert build_participant(_fields(**{FIELD_CODE: "a/b\\c"})).participant_code == "ABC"


def test_empty_code_is_rejected() -> None:
    with pytest.raises(LoginError):
        build_participant(_fields(**{FIELD_CODE: "  ///  "}))


@pytest.mark.parametrize("age", [17, 61, 0, "abc", ""])
def test_age_outside_the_criterion_is_rejected(age: Any) -> None:
    with pytest.raises(LoginError):
        build_participant(_fields(**{FIELD_AGE: age}))


def test_negative_deprivation_is_rejected() -> None:
    with pytest.raises(LoginError):
        build_participant(_fields(**{FIELD_DEPRIVATION: "-3"}))


def test_non_numeric_pta_is_rejected() -> None:
    with pytest.raises(LoginError):
        build_participant(_fields(**{FIELD_PTA_LEFT: "iyi"}))
