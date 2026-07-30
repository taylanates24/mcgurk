"""The abort confirmer (Adım 8b-ii).

ESC no longer stops the session outright: it asks first.  The mechanism is a
module-level confirmer routed through :func:`should_abort`; with none installed
the abort is immediate, which is what the dev harness and every test rely on.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mcgurk.engine import set_abort_confirmer, should_abort


@pytest.fixture(autouse=True)
def _clear_confirmer() -> Iterator[None]:
    # Never leak a confirmer into another test — the default is "abort at once".
    set_abort_confirmer(None)
    yield
    set_abort_confirmer(None)


def test_no_confirmer_means_immediate_abort() -> None:
    assert should_abort() is True


def test_confirmer_that_cancels_stops_the_abort() -> None:
    set_abort_confirmer(lambda: False)
    assert should_abort() is False


def test_confirmer_that_confirms_lets_the_abort_through() -> None:
    set_abort_confirmer(lambda: True)
    assert should_abort() is True


def test_confirmer_can_be_cleared() -> None:
    set_abort_confirmer(lambda: False)
    assert should_abort() is False
    set_abort_confirmer(None)
    assert should_abort() is True
