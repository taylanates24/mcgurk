"""Importing the delivered recordings into ``assets/`` (ADIM 12a).

The corpus arrives as one flat folder holding every visual x auditory
combination of every speaker.  Two things have to be true of the import, and
neither is visible afterwards if it goes wrong: only the congruent takes are
read (the pipeline builds the incongruent presentations itself, §A.1), and a
take already in the project is never silently replaced — speakers 1 and 2 were
prepared and run before the delivery arrived.

No mp4 is needed here: the importer copies bytes and compares digests, so the
files are plain byte blobs and the tests run without ffmpeg.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from mcgurk.config.schema import ExperimentConfig
from mcgurk.stimuli import StimulusError
from mcgurk.stimuli.import_sources import (
    Verdict,
    apply_import,
    plan_import,
)

TOKENS = ("ba", "da", "ga")
DELIVERY = "delivery"


def _config(config_dict: dict[str, Any]) -> ExperimentConfig:
    """The shipped design with two speakers in throwaway folders."""
    data = yaml.safe_load(yaml.safe_dump(config_dict))
    data["stimulus_prep"]["speakers"] = [
        {"id": 1, "source": "assets/one", "label": "Bir"},
        {"id": 2, "source": "assets/two", "label": "İki"},
    ]
    for module in ("mcgurk", "avsr", "tbw", "dichotic"):
        data["modules"][module]["speaker_id"] = 1
    data["speaker_selection"]["fixed_id"] = 1
    return ExperimentConfig.model_validate(data)


def _write_delivery(root: Path, speaker_ids: tuple[int, ...] = (1, 2)) -> Path:
    """Every combination of every speaker, as the corpus actually arrives."""
    delivery = root / DELIVERY
    delivery.mkdir(parents=True, exist_ok=True)
    for speaker_id in speaker_ids:
        for visual in TOKENS:
            for audio in TOKENS:
                name = f"Vis-{visual}_Aud-{audio}_Speaker-{speaker_id}.mp4"
                (delivery / name).write_bytes(
                    f"{speaker_id}:{visual}:{audio}".encode()
                )
    return delivery


@pytest.fixture
def project(config_dict: dict[str, Any], tmp_path: Path):
    config = _config(config_dict)
    delivery = _write_delivery(tmp_path)
    return config, tmp_path, delivery


# ------------------------------------------------------------ what is copied


def test_only_the_congruent_takes_are_imported(project) -> None:
    config, root, delivery = project
    apply_import(plan_import(config, root, delivery))

    for folder, speaker_id in (("one", 1), ("two", 2)):
        files = sorted(p.name for p in (root / "assets" / folder).iterdir())
        assert files == [f"Vis-{token}_Aud-{token}.mp4" for token in TOKENS]
        for token in TOKENS:
            copied = (root / "assets" / folder / f"Vis-{token}_Aud-{token}.mp4")
            assert copied.read_bytes() == f"{speaker_id}:{token}:{token}".encode()


def test_the_destination_name_drops_the_speaker_suffix(project) -> None:
    """The pipeline reads Vis-<t>_Aud-<t>.mp4; the id is the folder."""
    config, root, delivery = project
    items = plan_import(config, root, delivery)
    assert {item.destination.name for item in items} == {
        f"Vis-{token}_Aud-{token}.mp4" for token in TOKENS
    }


def test_a_single_speaker_can_be_imported(project) -> None:
    config, root, delivery = project
    report = apply_import(plan_import(config, root, delivery, speaker_ids=[2]))

    assert len(report.copied) == len(TOKENS)
    assert not (root / "assets" / "one").exists()
    assert (root / "assets" / "two").is_dir()


def test_an_unknown_speaker_id_is_refused(project) -> None:
    config, root, delivery = project
    with pytest.raises(StimulusError, match="olmayan konuşmacı"):
        plan_import(config, root, delivery, speaker_ids=[9])


def test_dry_run_writes_nothing(project) -> None:
    config, root, delivery = project
    report = apply_import(plan_import(config, root, delivery), dry_run=True)

    assert len(report.copied) == 2 * len(TOKENS)
    assert not (root / "assets").exists()


# --------------------------------------------------- what is already in place


def test_an_identical_take_is_skipped_not_rewritten(project) -> None:
    """Speakers 1 and 2 must stay the byte the earlier sessions used."""
    config, root, delivery = project
    destination = root / "assets" / "one" / "Vis-ba_Aud-ba.mp4"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"1:ba:ba")
    before = destination.stat().st_mtime_ns

    items = plan_import(config, root, delivery)
    verdicts = {
        item.destination: item.verdict for item in items
    }
    assert verdicts[destination] is Verdict.IDENTICAL

    report = apply_import(items)
    assert destination not in [item.destination for item in report.copied]
    assert destination.stat().st_mtime_ns == before


def test_a_different_take_stops_the_whole_import(project) -> None:
    """Not "overwrite the conflict and copy the rest" — nothing is written.

    A half-imported corpus looks complete from the outside, and which recording
    the prepared set came from is exactly what the conflict puts in doubt.
    """
    config, root, delivery = project
    destination = root / "assets" / "one" / "Vis-ba_Aud-ba.mp4"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"an older take")

    items = plan_import(config, root, delivery)
    assert any(item.verdict is Verdict.CONFLICT for item in items)

    with pytest.raises(StimulusError, match="FARKLI"):
        apply_import(items)

    assert destination.read_bytes() == b"an older take"
    assert not (root / "assets" / "two").exists()
    assert not (root / "assets" / "one" / "Vis-da_Aud-da.mp4").exists()


def test_a_missing_source_names_the_file(project) -> None:
    config, root, delivery = project
    (delivery / "Vis-da_Aud-da_Speaker-2.mp4").unlink()

    items = plan_import(config, root, delivery)
    with pytest.raises(StimulusError, match="Vis-da_Aud-da_Speaker-2.mp4"):
        apply_import(items)

    assert not (root / "assets").exists()


def test_a_missing_source_is_fine_once_the_take_is_in_place(project) -> None:
    """Re-running the import after the delivery folder is gone must not fail.

    The verdict is deliberately not IDENTICAL: nothing was compared, so saying
    the two match would be a claim this branch cannot make.
    """
    config, root, delivery = project
    (delivery / "Vis-da_Aud-da_Speaker-2.mp4").unlink()
    destination = root / "assets" / "two" / "Vis-da_Aud-da.mp4"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"prepared before the delivery arrived")

    items = plan_import(config, root, delivery)
    kept = [item for item in items if item.verdict is Verdict.KEPT]
    assert [item.destination for item in kept] == [destination]

    report = apply_import(items)
    assert destination in [item.destination for item in report.skipped]
    assert destination.read_bytes() == b"prepared before the delivery arrived"
