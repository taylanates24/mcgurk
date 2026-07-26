"""Seeding, ordering and packaging — the parts every module shares.

No PsychoPy: reproducibility of the trial order is a property of the design
layer, and it has to be checkable on a machine with no screen.
"""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

import pytest

from mcgurk.db.models import Trial
from mcgurk.engine.av_presenter import TrialSpec
from mcgurk.modules.base import (
    ModuleError,
    PlannedTrial,
    balanced_cycle,
    block_shuffle,
    chunk,
    derive_seed,
    full_shuffle,
    order_cells,
    spread_rounds,
)

CELLS = ("a", "b", "c")


# ------------------------------------------------------------------- seeding


def test_derived_seed_is_stable() -> None:
    assert derive_seed(1234, "mcgurk") == derive_seed(1234, "mcgurk")


def test_modules_get_different_streams_from_one_session_seed() -> None:
    assert derive_seed(1234, "mcgurk") != derive_seed(1234, "avsr")


def test_different_sessions_get_different_streams() -> None:
    assert derive_seed(1234, "mcgurk") != derive_seed(1235, "mcgurk")


# ------------------------------------------------------------------ ordering


def test_every_repetition_is_presented() -> None:
    ordered = block_shuffle(CELLS, [3, 2, 1], random.Random(0))
    assert Counter(ordered) == {"a": 3, "b": 2, "c": 1}


def test_a_round_holds_each_cell_at_most_once() -> None:
    rounds = spread_rounds([3, 3, 3])
    assert len(rounds) == 3
    for members in rounds:
        assert sorted(members) == [0, 1, 2]


def test_fewer_repetitions_are_spread_not_front_loaded() -> None:
    """The congruent controls have half the repetitions of the incongruent
    pairs; putting them all in the first rounds would leave the second half of
    the module entirely incongruent."""
    rounds = spread_rounds([10, 5])
    holding_the_short_cell = [index for index, members in enumerate(rounds) if 1 in members]
    assert holding_the_short_cell == [0, 2, 4, 6, 8]


def test_block_shuffle_keeps_conditions_evenly_distributed() -> None:
    ordered = block_shuffle(CELLS, [4, 4, 4], random.Random(7))
    halves = (Counter(ordered[:6]), Counter(ordered[6:]))
    for cell in CELLS:
        assert halves[0][cell] == 2
        assert halves[1][cell] == 2


def test_full_shuffle_does_not_promise_that() -> None:
    """Documenting the difference: ``full_shuffle`` is one pool, so a cell can
    cluster anywhere.  It exists because a design may prefer it, not because it
    behaves like ``block_shuffle``."""
    ordered = full_shuffle(CELLS, [4, 4, 4], random.Random(3))
    assert Counter(ordered) == {"a": 4, "b": 4, "c": 4}


def test_same_seed_same_order() -> None:
    first = block_shuffle(CELLS, [5, 5, 3], random.Random(99))
    second = block_shuffle(CELLS, [5, 5, 3], random.Random(99))
    assert first == second


def test_different_seed_different_order() -> None:
    many = tuple(f"cell{index}" for index in range(12))
    reps = [3] * len(many)
    assert block_shuffle(many, reps, random.Random(1)) != block_shuffle(
        many, reps, random.Random(2)
    )


def test_unknown_randomisation_is_refused() -> None:
    with pytest.raises(ModuleError, match="randomizasyon"):
        order_cells(CELLS, [1, 1, 1], random.Random(0), "sometimes")


def test_mismatched_lengths_are_refused() -> None:
    with pytest.raises(ModuleError, match="aynı uzunlukta"):
        block_shuffle(CELLS, [1, 1], random.Random(0))


def test_zero_repetitions_are_refused() -> None:
    with pytest.raises(ModuleError, match="pozitif"):
        spread_rounds([2, 0])


# ---------------------------------------------------------- noise instances


def test_instances_are_balanced_over_the_repetitions() -> None:
    counts = Counter(balanced_cycle(3, 9, random.Random(0)))
    assert set(counts.values()) == {3}


def test_instances_stay_as_balanced_as_the_count_allows() -> None:
    counts = Counter(balanced_cycle(3, 10, random.Random(0)))
    assert sorted(counts.values()) == [3, 3, 4]


def test_instance_order_is_seeded() -> None:
    assert balanced_cycle(3, 10, random.Random(5)) == balanced_cycle(
        3, 10, random.Random(5)
    )


def test_at_least_one_option_is_needed() -> None:
    with pytest.raises(ModuleError):
        balanced_cycle(0, 4, random.Random(0))


# -------------------------------------------------------------- packaging


def _planned() -> PlannedTrial:
    return PlannedTrial(
        spec=TrialSpec(audio_path=Path("a.wav")),
        trial=Trial(block_id=0, trial_index=0, module="mcgurk", condition_label="x"),
    )


def test_block_and_index_are_filled_in_by_the_runner() -> None:
    item = _planned()
    trial = item.for_block(block_id=42, trial_index=7)
    assert (trial.block_id, trial.trial_index) == (42, 7)
    # The plan itself is untouched, so it can be replanned or reused.
    assert (item.trial.block_id, item.trial.trial_index) == (0, 0)


def test_chunking_splits_at_the_commit_boundary() -> None:
    chunks = chunk(list(range(10)), 4)
    assert [len(part) for part in chunks] == [4, 4, 2]


def test_chunking_a_short_list_gives_one_block() -> None:
    assert chunk([1, 2], 60) == [[1, 2]]


def test_chunk_size_must_be_positive() -> None:
    with pytest.raises(ModuleError):
        chunk([1, 2], 0)
