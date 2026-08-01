"""Build the Windows operator app with PyInstaller (steps.md ADIM 10c-ii).

    python tools/build_exe.py            # build from packaging/mcgurk.spec
    python tools/build_exe.py --clean    # also wipe build/ and dist/ first

Output is ``dist/McGurkSSD/McGurkSSD.exe`` (onedir).  ``stimuli/`` is *not*
bundled — copy it next to the exe afterwards (see packaging/README.md).

Run on the Windows machine that has the full ``requirements.txt`` installed plus
``pyinstaller`` (``pip install -r requirements-dev.txt``).  This is the most
iteration-heavy step; PsychoPy freezing quirks are solved here, on the real
machine (steps.md ADIM_10 SD10).

Exit code 0 = build finished; non-zero = PyInstaller failed (read its output).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SPEC = _PROJECT_ROOT / "packaging" / "mcgurk.spec"
_DIST = _PROJECT_ROOT / "dist" / "McGurkSSD"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_exe", description="McGurk/SSD Windows .exe derle (PyInstaller)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="derlemeden önce build/ ve dist/ klasörlerini sil",
    )
    args = parser.parse_args(argv)

    if not _SPEC.is_file():
        print(f"HATA: spec bulunamadi: {_SPEC}", file=sys.stderr)
        return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "HATA: PyInstaller kurulu degil. Kurulum:\n"
            "  pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return 1

    if args.clean:
        for path in (_PROJECT_ROOT / "build", _PROJECT_ROOT / "dist"):
            if path.exists():
                print(f"Siliniyor: {path}")
                shutil.rmtree(path)

    print(f"PyInstaller ile derleniyor: {_SPEC.name}")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(_SPEC)],
        cwd=str(_PROJECT_ROOT),
        check=False,
    )
    if result.returncode != 0:
        print(
            f"\nHATA: PyInstaller cikis kodu {result.returncode}. "
            "Ciktidaki eksik import/veri dosyasi mesajlarina bakin (SD10).",
            file=sys.stderr,
        )
        return result.returncode

    print("\nDerleme tamam.")
    print(f"  Uygulama : {_DIST / 'McGurkSSD.exe'}")
    print(f"  Klasor   : {_DIST}")
    print(
        "\nSonraki adim: stimuli/ klasorunu uygulamanin yanina kopyalayin:\n"
        f"  {_DIST / 'stimuli'}\n"
        "data/, backups/, logs/, config/ ilk calistirmada burada olusur."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
