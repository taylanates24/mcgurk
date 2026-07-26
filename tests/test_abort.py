"""Aborting the session must work at any point, not only at the response screen.

The abort key used to be handled solely inside ``collect_response``, so a
session could only be stopped while a response was being awaited — pressing it
during the fixation cross or mid-stimulus did nothing.
"""

from collections.abc import Iterator

import pytest
from psychopy import event

from src.experiment.response import collect_response
from src.experiment.stimuli import ABORT_KEY, AbortSession, check_abort


class _FakeClock:
    """Minimal stand-in for core.Clock — collect_response only reads it."""

    def getTime(self) -> float:
        return 0.0


@pytest.fixture(autouse=True)
def clear_key_buffer() -> Iterator[None]:
    event.clearEvents()
    yield
    event.clearEvents()


def test_check_abort_is_silent_without_a_keypress(monkeypatch):
    monkeypatch.setattr(event, "getKeys", lambda keyList=None: [])

    check_abort()  # must not raise


def test_check_abort_raises_on_abort_key(monkeypatch):
    monkeypatch.setattr(event, "getKeys", lambda keyList=None: [ABORT_KEY])

    with pytest.raises(AbortSession):
        check_abort()


def test_check_abort_only_watches_the_abort_key(monkeypatch):
    """The filter must be narrow — a response key must not abort the session."""
    captured = {}

    def fake_get_keys(keyList=None):
        captured["keyList"] = keyList
        return []

    monkeypatch.setattr(event, "getKeys", fake_get_keys)
    check_abort()

    assert captured["keyList"] == [ABORT_KEY]


def test_response_screen_abort_raises(monkeypatch):
    monkeypatch.setattr(
        event, "waitKeys", lambda keyList=None, timeStamped=None: [(ABORT_KEY, 1.0)]
    )

    with pytest.raises(AbortSession):
        collect_response(
            valid_keys=["1", "2", "3"],
            key_to_syllable={"1": "ba", "2": "da", "3": "ga"},
            video_end_time=0.0,
            options_shown_time=0.0,
            clock=_FakeClock(),
        )


def test_interrupted_wait_is_treated_as_abort(monkeypatch):
    """An empty waitKeys result must not be recorded as a given response."""
    monkeypatch.setattr(
        event, "waitKeys", lambda keyList=None, timeStamped=None: []
    )

    with pytest.raises(AbortSession):
        collect_response(
            valid_keys=["1"],
            key_to_syllable={"1": "ba"},
            video_end_time=0.0,
            options_shown_time=0.0,
            clock=_FakeClock(),
        )


def test_normal_response_is_returned(monkeypatch):
    monkeypatch.setattr(
        event, "waitKeys", lambda keyList=None, timeStamped=None: [("2", 1.5)]
    )

    resp = collect_response(
        valid_keys=["1", "2", "3"],
        key_to_syllable={"1": "ba", "2": "da", "3": "ga"},
        video_end_time=1.0,
        options_shown_time=1.2,
        clock=_FakeClock(),
    )

    assert resp.syllable == "da"
    assert resp.rt_from_video_end_ms == pytest.approx(500.0)
    assert resp.rt_from_options_shown_ms == pytest.approx(300.0)


def test_abort_key_is_offered_alongside_response_keys(monkeypatch):
    """The abort key must be in the accepted set, or waitKeys would ignore it."""
    captured = {}

    def fake_wait_keys(keyList=None, timeStamped=None):
        captured["keyList"] = keyList
        return [("1", 1.0)]

    monkeypatch.setattr(event, "waitKeys", fake_wait_keys)
    collect_response(
        valid_keys=["1"],
        key_to_syllable={"1": "ba"},
        video_end_time=0.0,
        options_shown_time=0.0,
        clock=_FakeClock(),
    )

    assert ABORT_KEY in captured["keyList"]
