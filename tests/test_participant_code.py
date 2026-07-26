"""Participant code sanitisation.

The code reaches filenames and export headers, so anything that could act as
a path or break a CSV must not survive.
"""

import pytest

from src.dialogs.login import sanitize_participant_code


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SSD-R-007", "SSD-R-007"),
        ("  ctrl_012  ", "CTRL_012"),
        ("ssd-l-1", "SSD-L-1"),
    ],
)
def test_valid_codes_are_normalised(raw: str, expected: str):
    assert sanitize_participant_code(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "ETCPASSWD"),
        (r"C:\Windows\System32", "CWINDOWSSYSTEM32"),
        ("kod;DROP TABLE", "KODDROPTABLE"),
        ("a b\tc", "ABC"),
    ],
)
def test_path_and_separator_characters_are_stripped(raw: str, expected: str):
    assert sanitize_participant_code(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "///", "!!!"])
def test_codes_without_usable_characters_become_empty(raw: str):
    """An empty result signals invalid input; the dialog re-prompts."""
    assert sanitize_participant_code(raw) == ""


def test_code_is_length_capped():
    assert len(sanitize_participant_code("A" * 100)) == 32
