"""Pieces every assessment module needs: seeding, ordering, trial packaging.

Pure Python — no PsychoPy, no I/O.  What a session presents and in what order
is decided here, so the whole design side of a module can be tested in CI
(steps.md §C Adım 4: "Aynı seed → aynı deneme sırası").

Nothing in this file is McGurk-specific.  It is deliberately small: the trial
*loop* differs between modules (GIN collects several responses inside one
stimulus, oddball is a continuous stream), so only the parts that genuinely
repeat live here.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, TypeVar

from ..db.models import Trial
from ..engine.av_presenter import TrialSpec

T = TypeVar("T")

#: ``trials.noise_condition`` when nothing was mixed in.  A noisy trial is
#: named after ``stimulus_prep.noise.type`` instead, so the column says what
#: was heard rather than merely that something was.  NULL is reserved for
#: "not applicable" — an AVSR V-only trial, which carries no audio at all.
QUIET = "quiet"


class ModuleError(RuntimeError):
    """A module cannot build the design it was asked for."""


def derive_seed(session_seed: int, module: str) -> int:
    """A per-module RNG seed derived from the session seed (§A.11).

    Every module drawing from one shared ``Random`` would make its trial order
    depend on the modules before it: moving ``mcgurk`` after ``avsr`` in
    ``session.module_order`` would change McGurk's order even though nothing
    about McGurk changed.  Deriving per module keeps ``sessions.seed`` a
    complete description of every order in the session while leaving them
    independent of each other.
    """
    digest = hashlib.sha256(f"{session_seed}:{module}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def spread_rounds(reps: Sequence[int]) -> list[list[int]]:
    """Which cells appear in which round of presentation.

    A round holds at most one presentation of every cell.  A cell with fewer
    repetitions than the maximum is spread over the whole sequence
    (``floor(k · R / reps)``) rather than filling the first rounds: with
    ``reps: 10`` on the incongruent pairs and ``reps: 5`` on the congruent
    controls, the naive version would put every control in the first half of
    the module and leave the second half entirely incongruent.

    Returns:
        One list of cell indices per round, in round order.
    """
    if not reps:
        return []
    if any(count <= 0 for count in reps):
        raise ModuleError(f"Tekrar sayısı pozitif olmalı: {list(reps)}")

    total_rounds = max(reps)
    rounds: list[list[int]] = [[] for _ in range(total_rounds)]
    for cell, count in enumerate(reps):
        for k in range(count):
            rounds[(k * total_rounds) // count].append(cell)
    return rounds


def block_shuffle(
    cells: Sequence[T], reps: Sequence[int], rng: random.Random
) -> list[T]:
    """Order the cells round by round, shuffling within each round.

    This is what ``randomization: block_shuffle`` means: conditions stay evenly
    distributed over the module, so a participant who tires or adapts halfway
    through affects every condition equally rather than whichever ones happened
    to be scheduled late.
    """
    _check_lengths(cells, reps)
    ordered: list[T] = []
    for members in spread_rounds(reps):
        drawn = [cells[index] for index in members]
        rng.shuffle(drawn)
        ordered.extend(drawn)
    return ordered


def full_shuffle(
    cells: Sequence[T], reps: Sequence[int], rng: random.Random
) -> list[T]:
    """Put every repetition of every cell in one pool and shuffle it once."""
    _check_lengths(cells, reps)
    pool = [
        cell for cell, count in zip(cells, reps, strict=True) for _ in range(count)
    ]
    rng.shuffle(pool)
    return pool


def order_cells(
    cells: Sequence[T],
    reps: Sequence[int],
    rng: random.Random,
    strategy: str,
) -> list[T]:
    """Dispatch on ``modules.*.randomization``."""
    if strategy == "block_shuffle":
        return block_shuffle(cells, reps, rng)
    if strategy == "full_shuffle":
        return full_shuffle(cells, reps, rng)
    raise ModuleError(f"Bilinmeyen randomizasyon: {strategy!r}")


def _check_lengths(cells: Sequence[object], reps: Sequence[int]) -> None:
    if len(cells) != len(reps):
        raise ModuleError(
            f"Hücre ve tekrar listeleri aynı uzunlukta olmalı "
            f"({len(cells)} != {len(reps)})"
        )


def balanced_cycle(n_options: int, n_draws: int, rng: random.Random) -> list[int]:
    """*n_draws* choices from *n_options*, as balanced as the count allows.

    Used for the noise instances: three waveforms over ten repetitions should
    be 4/3/3, not the 7/2/1 that independent draws can produce.  Each cycle
    through the options is shuffled, so the sequence is still unpredictable
    from the participant's side.
    """
    if n_options < 1:
        raise ModuleError(f"Seçenek sayısı en az 1 olmalı (verilen: {n_options})")
    order: list[int] = []
    while len(order) < n_draws:
        cycle = list(range(n_options))
        rng.shuffle(cycle)
        order.extend(cycle)
    return order[:n_draws]


def row_value(row: Any, key: str) -> Any:
    """Read *key* from a mapping or a ``sqlite3.Row``; None when absent.

    The measure functions of every module read ``v_trials_flat`` rows, which are
    ``sqlite3.Row`` objects in a run and plain dicts in a test.  One helper
    rather than one per module: two copies of "how do I read a column" is two
    places for a KeyError to be swallowed differently.
    """
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


@dataclass(frozen=True)
class PlannedTrial:
    """One trial, ready for both halves of the system.

    ``spec`` goes to the presenter, ``trial`` goes to the database.  They are
    built together so a trial cannot be presented with one stimulus and
    recorded as another; ``block_id`` and ``trial_index`` are the only fields
    the runner fills in, because they are not known until the block exists.
    """

    spec: TrialSpec
    trial: Trial

    def for_block(self, block_id: int, trial_index: int) -> Trial:
        return replace(self.trial, block_id=block_id, trial_index=trial_index)


def chunk(items: Sequence[T], size: int) -> list[list[T]]:
    """Split *items* into consecutive chunks of at most *size*.

    Blocks are the commit boundary (§A.5), so a module of 140 trials is not one
    block: a crash would take the whole module's uncommitted data with it.
    """
    if size < 1:
        raise ModuleError(f"Blok boyutu en az 1 olmalı (verilen: {size})")
    return [list(items[start : start + size]) for start in range(0, len(items), size)]
