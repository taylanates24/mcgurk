"""Adım 11a — editing the repetition counts in ``config/experiment.yaml``.

Everything here runs without a screen, PsychoPy or PyQt6: the panel's Ayarlar
tab is a Qt shell over these functions, and what lands on disk is decided here.

The tests work on a **verbatim byte copy** of the shipped config, not on the
``write_config`` fixture's pyyaml re-dump: the whole point is that comments and
layout survive a write, and a re-dumped file has no comments left to lose.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcgurk.config import edit
from mcgurk.config.loader import ConfigError, load_config
from mcgurk.config.schema import ExperimentConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = PROJECT_ROOT / "config" / "experiment.yaml"

#: A comment that has to survive every write.  Picked because it explains the
#: very field the tab edits — if any comment is going to be lost by a save, the
#: one sitting next to the changed scalar is the first casualty.
CELL_COMMENT = "reps is PER CELL"

#: A long single-line Turkish string.  ruamel's default line width would wrap
#: it, turning an unrelated save into a several-hundred-line diff.
LONG_LINE = "Katıldığınız için teşekkürler."


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A byte-for-byte copy of the shipped config, in a writable directory."""
    destination = tmp_path / "config" / "experiment.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(SHIPPED_CONFIG.read_bytes())
    return destination


@pytest.fixture
def config(config_file: Path, tmp_path: Path) -> ExperimentConfig:
    return load_config(config_file, project_root=tmp_path, check_filesystem=False)


def _text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    """Pairs of lines that differ, for files of equal line count."""
    old, new = before.split("\n"), after.split("\n")
    assert len(old) == len(new), "satır sayısı değişmemeli"
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


# --------------------------------------------------------------------- read


def test_read_reps_covers_every_editable_count(config: ExperimentConfig) -> None:
    keys = [field.key for field in edit.read_reps(config)]
    assert keys == [
        "session.practice_trials",
        "modules.mcgurk.av_pairs[0].reps",
        "modules.mcgurk.av_pairs[1].reps",
        "modules.mcgurk.av_pairs[2].reps",
        "modules.mcgurk.av_pairs[3].reps",
        "modules.mcgurk.av_pairs[4].reps",
        "modules.avsr.stimulus_sets[0].reps",
        "modules.tbw.reps_per_soa",
        "modules.oddball.n_trials",
        "modules.dichotic.reps",
        "cross_hearing_check.n_trials",
    ]


def test_read_reps_values_come_from_the_config(config: ExperimentConfig) -> None:
    values = {field.key: field.value for field in edit.read_reps(config)}
    assert values["session.practice_trials"] == config.session.practice_trials
    assert values["modules.mcgurk.av_pairs[0].reps"] == (
        config.modules.mcgurk.av_pairs[0].reps
    )
    assert values["modules.tbw.reps_per_soa"] == config.modules.tbw.reps_per_soa
    assert values["modules.oddball.n_trials"] == config.modules.oddball.n_trials
    assert values["cross_hearing_check.n_trials"] == (
        config.cross_hearing_check.n_trials
    )


def test_read_reps_leaves_gin_out(config: ExperimentConfig) -> None:
    """GIN's segments come from the prepared set, not from a repetition knob.

    ``reps_per_gap`` is tied to the 4-of-6 threshold rule and the published
    norms; exposing it as a spin box would let the operator break both.
    """
    assert config.modules.gin.enabled
    assert not any("gin" in field.key for field in edit.read_reps(config))


def test_read_reps_skips_a_disabled_stimulus_set(config: ExperimentConfig) -> None:
    """The AVSR word set is disabled (§F.2), so it has no field yet."""
    assert config.modules.avsr.stimulus_sets[1].enabled is False
    keys = {field.key for field in edit.read_reps(config)}
    assert "modules.avsr.stimulus_sets[1].reps" not in keys


def test_read_reps_skips_a_disabled_module(
    config_file: Path, tmp_path: Path
) -> None:
    text = _text(config_file)
    # Disable dichotic, and take it out of the session order the schema checks.
    text = text.replace(
        "  dichotic:\n    enabled: true", "  dichotic:\n    enabled: false"
    )
    text = text.replace(
        "module_order: [practice, mcgurk, avsr, tbw, oddball, dichotic, gin]",
        "module_order: [practice, mcgurk, avsr, tbw, oddball, gin]",
    )
    config_file.write_bytes(text.encode("utf-8"))
    config = load_config(config_file, project_root=tmp_path, check_filesystem=False)

    keys = {field.key for field in edit.read_reps(config)}
    assert "modules.dichotic.reps" not in keys
    assert "modules.mcgurk.av_pairs[0].reps" in keys


def test_rep_field_bounds_follow_the_schema(config: ExperimentConfig) -> None:
    fields = {field.key: field for field in edit.read_reps(config)}
    # practice_trials is ge=0 (a session may skip practice), every rep is gt=0.
    assert fields["session.practice_trials"].minimum == 0
    assert fields["modules.tbw.reps_per_soa"].minimum == 1
    assert all(field.maximum > field.value for field in fields.values())


# ------------------------------------------------------------------ preview


def test_preview_reps_recomputes_the_trial_counts(config: ExperimentConfig) -> None:
    before = config.trial_counts()["tbw"]
    preview = edit.preview_reps(config, {"modules.tbw.reps_per_soa": 20})
    # 13 SOA values x 20 reps x 1 ear
    assert preview.trial_counts()["tbw"] == 2 * before
    assert preview.estimated_duration_s() > config.estimated_duration_s()


def test_preview_reps_does_not_touch_the_original(config: ExperimentConfig) -> None:
    original = config.modules.dichotic.reps
    edit.preview_reps(config, {"modules.dichotic.reps": original + 3})
    assert config.modules.dichotic.reps == original


def test_preview_reps_does_not_touch_the_disk(
    config: ExperimentConfig, config_file: Path
) -> None:
    before = _text(config_file)
    edit.preview_reps(config, {"modules.oddball.n_trials": 400})
    assert _text(config_file) == before


def test_preview_reps_rejects_an_impossible_value(config: ExperimentConfig) -> None:
    # 1 trial x 0.18 target probability rounds to zero targets.
    with pytest.raises(ConfigError):
        edit.preview_reps(config, {"modules.oddball.n_trials": 1})


def test_preview_reps_rejects_an_unknown_key(config: ExperimentConfig) -> None:
    with pytest.raises(ConfigError, match="modules.gin.reps_per_gap"):
        edit.preview_reps(config, {"modules.gin.reps_per_gap": 8})


# -------------------------------------------------------------------- write


def test_write_reps_changes_only_the_named_scalar(
    config_file: Path, tmp_path: Path
) -> None:
    before = _text(config_file)
    edit.write_reps(config_file, tmp_path, {"modules.tbw.reps_per_soa": 14})
    after = _text(config_file)

    changed = _changed_lines(before, after)
    assert len(changed) == 1
    assert changed[0][0].strip() == "reps_per_soa: 10"
    assert changed[0][1].strip() == "reps_per_soa: 14"


def test_write_reps_preserves_the_comments(config_file: Path, tmp_path: Path) -> None:
    assert CELL_COMMENT in _text(config_file)
    edit.write_reps(config_file, tmp_path, {"modules.mcgurk.av_pairs[0].reps": 12})
    after = _text(config_file)

    assert CELL_COMMENT in after, "yorumlar round-trip'te silinmemeli"
    assert LONG_LINE in after, "uzun satırlar sarılmamalı"
    assert "{visual: ga, audio: ba, label: fusion_pair, reps: 12}" in after
    # Explicit nulls stay explicit rather than becoming empty values.
    assert "system_av_offset_ms: null" in after


def test_write_reps_without_changes_is_byte_identical(
    config_file: Path, tmp_path: Path
) -> None:
    """The guard behind "only the edited key changes".

    If ruamel ever stops reproducing this file exactly — a new construct, a new
    version — the first save would silently reformat several hundred lines.
    Here that shows up as a failing test instead.
    """
    before = config_file.read_bytes()
    edit.write_reps(config_file, tmp_path, {})
    assert config_file.read_bytes() == before


def test_write_reps_applies_several_fields_at_once(
    config_file: Path, tmp_path: Path
) -> None:
    config = edit.write_reps(
        config_file,
        tmp_path,
        {
            "session.practice_trials": 8,
            "modules.dichotic.reps": 7,
            "cross_hearing_check.n_trials": 24,
        },
    )
    assert config.session.practice_trials == 8
    assert config.modules.dichotic.reps == 7
    assert config.cross_hearing_check.n_trials == 24

    # …and the returned config is what a fresh load sees.
    reloaded = load_config(config_file, project_root=tmp_path, check_filesystem=False)
    assert reloaded.trial_counts() == config.trial_counts()


def test_write_reps_rolls_back_an_invalid_value(
    config_file: Path, tmp_path: Path
) -> None:
    """A value the schema refuses must leave the file exactly as it was."""
    before = config_file.read_bytes()
    with pytest.raises(ConfigError, match="geri alındı"):
        edit.write_reps(config_file, tmp_path, {"modules.oddball.n_trials": 2})
    assert config_file.read_bytes() == before
    # The rolled-back file still loads.
    load_config(config_file, project_root=tmp_path, check_filesystem=False)


def test_write_reps_rolls_back_a_zero_repetition(
    config_file: Path, tmp_path: Path
) -> None:
    before = config_file.read_bytes()
    with pytest.raises(ConfigError):
        edit.write_reps(config_file, tmp_path, {"modules.dichotic.reps": 0})
    assert config_file.read_bytes() == before


def test_write_reps_rejects_an_unknown_key(config_file: Path, tmp_path: Path) -> None:
    before = config_file.read_bytes()
    with pytest.raises(ConfigError):
        edit.write_reps(config_file, tmp_path, {"modules.tbw.bootstrap_samples": 500})
    assert config_file.read_bytes() == before


def test_write_reps_leaves_no_temporary_file(config_file: Path, tmp_path: Path) -> None:
    edit.write_reps(config_file, tmp_path, {"modules.dichotic.reps": 6})
    leftovers = [p.name for p in config_file.parent.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_write_reps_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        edit.write_reps(tmp_path / "yok.yaml", tmp_path, {})


# ----------------------------------------------------------------- defaults


def test_default_reps_matches_the_editable_fields(config: ExperimentConfig) -> None:
    """The defaults file has to track the design (§A11.4).

    If a new AV pair is added or the word set is enabled, this fails until
    ``config/experiment.defaults.yaml`` gains the key — which is the point: a
    "Varsayılana dön" that silently skips a field is worse than one that is
    known to be stale.
    """
    assert set(edit.default_reps()) == {
        field.key for field in edit.read_reps(config)
    }


def test_default_reps_are_the_shipped_values(config: ExperimentConfig) -> None:
    """Today the live config *is* the factory design, so the two agree."""
    assert edit.default_reps() == {
        field.key: field.value for field in edit.read_reps(config)
    }


def test_default_reps_survive_an_edit_to_the_live_config(
    config_file: Path, tmp_path: Path
) -> None:
    """The reset source must not be the file being edited (§Açık nokta)."""
    edit.write_reps(config_file, tmp_path, {"modules.dichotic.reps": 9})
    assert edit.default_reps()["modules.dichotic.reps"] == 5


def test_default_reps_reads_from_the_given_root(tmp_path: Path) -> None:
    path = tmp_path / "config" / "experiment.defaults.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("version: 1\nreps:\n  modules.tbw.reps_per_soa: 3\n", "utf-8")
    assert edit.default_reps(tmp_path) == {"modules.tbw.reps_per_soa": 3}


def test_default_reps_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        edit.default_reps(tmp_path)


def test_default_reps_rejects_a_non_integer(tmp_path: Path) -> None:
    path = tmp_path / "config" / "experiment.defaults.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("reps:\n  modules.tbw.reps_per_soa: cok\n", "utf-8")
    with pytest.raises(ConfigError, match="tam sayı"):
        edit.default_reps(tmp_path)


def test_defaults_can_be_applied_to_a_changed_config(
    config_file: Path, tmp_path: Path
) -> None:
    """The reset round trip: edit, then write the defaults back."""
    edited = edit.write_reps(
        config_file,
        tmp_path,
        {"modules.tbw.reps_per_soa": 20, "session.practice_trials": 4},
    )
    assert edited.modules.tbw.reps_per_soa == 20

    restored = edit.write_reps(config_file, tmp_path, edit.default_reps())
    assert restored.modules.tbw.reps_per_soa == 10
    assert restored.session.practice_trials == 12
    # Back to the shipped design, comments included.
    assert config_file.read_bytes() == SHIPPED_CONFIG.read_bytes()
