"""Trial counts and the duration estimate (steps.md §G).

These numbers are what the §F.1 design decision gets made against, and from
Adım 4 onwards they are what the module generators must reproduce, so they are
pinned here rather than left to inspection.
"""

from __future__ import annotations

from typing import Any

from mcgurk.config import load_config, summarise_design


def _load(write_config, data: dict[str, Any]):
    return load_config(write_config(data), check_filesystem=False)


def test_mcgurk_count_is_pairs_by_noise_by_ear(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    # 35 repetitions across five pairs × 2 noise conditions × 2 ears
    assert config.modules.mcgurk.total_trials() == 140


def test_mcgurk_count_follows_the_config(write_config, config_dict) -> None:
    config_dict["modules"]["mcgurk"]["ears"] = ["right"]
    config = _load(write_config, config_dict)
    assert config.modules.mcgurk.total_trials() == 70


def test_reps_are_per_cell_not_per_module(write_config, config_dict) -> None:
    # `reps: 10` on a pair means ten presentations in *each* noise × ear cell,
    # so the participant sees that stimulus forty times.  Easy to misread when
    # choosing the design, so it is pinned.
    config_dict["modules"]["mcgurk"]["av_pairs"] = [
        {"visual": "ga", "audio": "ba", "label": "fusion_pair", "reps": 10}
    ]
    config_dict["modules"]["mcgurk"]["fusion_map"] = {"ga|ba": ["da", "ta"]}
    config_dict["modules"]["mcgurk"]["combination_map"] = {}
    config = _load(write_config, config_dict)
    assert config.modules.mcgurk.total_trials() == 10 * 2 * 2


def test_v_only_is_not_crossed_with_noise_or_ear(write_config, config_dict) -> None:
    # steps.md §C Adım 5: V-only carries no audio, so crossing it with SNR and
    # ear would quadruple the block for nothing.
    config = _load(write_config, config_dict)
    assert config.modules.avsr.total_trials() == 135  # 15 V + 60 A + 60 AV

    config_dict["modules"]["avsr"]["presentation_modes"] = ["V"]
    only_visual = _load(write_config, config_dict)
    assert only_visual.modules.avsr.total_trials() == 15


def test_tbw_count(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    assert config.modules.tbw.total_trials() == 13 * 10


def test_oddball_counts(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    assert config.modules.oddball.total_trials() == 200
    assert config.modules.oddball.n_targets() == 36


def test_dichotic_count(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    assert config.modules.dichotic.total_trials() == 30


def test_gin_counts_segments_not_gaps(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    assert config.modules.gin.total_trials() == 30      # segments = trials
    assert config.modules.gin.total_gaps() == 60        # 10 durations × 6 reps
    assert config.modules.gin.threshold_rule() == (4, 6)


def test_gin_duration_uses_segment_and_interval(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    assert config.modules.gin.estimated_duration_s() == 30 * (6.0 + 2.0)


def test_trial_counts_cover_every_ordered_module(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    counts = config.trial_counts()
    for name in config.session.module_order:
        assert name in counts
    assert counts["practice"] == config.session.practice_trials
    assert counts["cross_hearing"] == config.cross_hearing_check.n_trials


def test_disabled_module_contributes_nothing(write_config, config_dict) -> None:
    config_dict["modules"]["dichotic"]["enabled"] = False
    config_dict["session"]["module_order"].remove("dichotic")
    config = _load(write_config, config_dict)
    assert "dichotic" not in config.trial_counts()
    assert "dichotic" not in config.enabled_modules()


def test_estimated_duration_includes_breaks(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    modules_only = sum(
        config.modules.by_name()[name].estimated_duration_s()
        for name in config.enabled_modules()
    )
    assert config.estimated_duration_s() > modules_only


def test_summary_lists_every_module_and_a_total(write_config, config_dict) -> None:
    config = _load(write_config, config_dict)
    summary = summarise_design(config)
    for name in ("mcgurk", "avsr", "tbw", "oddball", "dichotic", "gin"):
        assert name in summary
    assert "TOPLAM" in summary
    assert str(sum(config.trial_counts().values())) in summary
