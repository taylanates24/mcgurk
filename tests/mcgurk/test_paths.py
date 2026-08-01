"""Adım 10c-i — the shared source/frozen path layer.

``resolve_roots`` is already covered via ``test_panel_core``; here the concern is
``detect_runtime``'s frozen branch (mocked ``sys.frozen``/``_MEIPASS``) and
``ensure_writable_config``'s first-run copy — the two pieces that decide where a
frozen build reads its code and writes its data.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcgurk import paths


def test_detect_runtime_source_uses_repo_root() -> None:
    runtime = paths.detect_runtime()
    assert runtime.frozen is False
    assert runtime.resource_root == runtime.writable_root
    # mcgurk/paths.py -> repo root, which holds the package and tools/.
    assert (runtime.resource_root / "mcgurk" / "paths.py").is_file()


def test_detect_runtime_frozen_splits_roots(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "dist" / "mcgurk.exe"
    exe.parent.mkdir(parents=True)
    meipass = tmp_path / "meipass"
    meipass.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))

    runtime = paths.detect_runtime()

    assert runtime.frozen is True
    assert runtime.resource_root == meipass  # read-only bundle
    assert runtime.writable_root == exe.parent  # beside the .exe


def _runtime(frozen: bool, resource: Path, writable: Path) -> paths.Runtime:
    return paths.Runtime(
        frozen=frozen,
        executable="mcgurk.exe" if frozen else "python",
        resource_root=resource,
        writable_root=writable,
    )


def test_ensure_writable_config_source_returns_repo_config(tmp_path: Path) -> None:
    runtime = _runtime(False, tmp_path, tmp_path)
    assert paths.ensure_writable_config(runtime) == (
        tmp_path / "config" / "experiment.yaml"
    )


def test_ensure_writable_config_frozen_copies_default_on_first_run(
    tmp_path: Path,
) -> None:
    resource = tmp_path / "res"
    writable = tmp_path / "wr"
    (resource / "config").mkdir(parents=True)
    (resource / "config" / "experiment.yaml").write_text(
        "mode: development\n", encoding="utf-8"
    )

    result = paths.ensure_writable_config(_runtime(True, resource, writable))

    assert result == writable / "config" / "experiment.yaml"
    assert result.read_text(encoding="utf-8") == "mode: development\n"


def test_ensure_writable_config_frozen_does_not_overwrite_edits(
    tmp_path: Path,
) -> None:
    resource = tmp_path / "res"
    writable = tmp_path / "wr"
    (resource / "config").mkdir(parents=True)
    (resource / "config" / "experiment.yaml").write_text("default", encoding="utf-8")
    (writable / "config").mkdir(parents=True)
    (writable / "config" / "experiment.yaml").write_text("edited", encoding="utf-8")

    result = paths.ensure_writable_config(_runtime(True, resource, writable))

    # The operator's edited copy survives a re-run; the default never clobbers it.
    assert result.read_text(encoding="utf-8") == "edited"
