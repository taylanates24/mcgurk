"""Environment facts stored on every session row."""

from __future__ import annotations

from pathlib import Path

from mcgurk import provenance

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_collect_fills_the_session_fields() -> None:
    facts = provenance.collect(PROJECT_ROOT)
    assert facts.python_version.startswith("3.")
    assert facts.os_name
    assert facts.app_version


def test_package_version_of_an_installed_package() -> None:
    assert provenance.package_version("pytest") is not None


def test_package_version_of_a_missing_package() -> None:
    # An analysis machine without PsychoPy is a legitimate state, not an error.
    assert provenance.package_version("bu-paket-yok-12345") is None


def test_git_commit_inside_the_repository() -> None:
    commit = provenance.git_commit(PROJECT_ROOT)
    assert commit is not None
    assert len(commit.split("+")[0]) >= 7


def test_git_commit_outside_a_repository(tmp_path: Path) -> None:
    assert provenance.git_commit(tmp_path) is None


def test_provenance_is_serialisable() -> None:
    facts = provenance.collect(PROJECT_ROOT).as_dict()
    assert set(facts) == {
        "app_version",
        "git_commit",
        "python_version",
        "os_name",
        "psychopy_version",
        "psychtoolbox_version",
    }
