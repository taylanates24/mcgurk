# PyInstaller spec — McGurk / SSD operator app (Adim 10c-ii)
#
# Build:  pyinstaller packaging/mcgurk.spec        (or: python tools/build_exe.py)
# Output: dist/McGurkSSD/McGurkSSD.exe             (onedir — see packaging/README.md)
#
# This is a first pass.  PyInstaller + PsychoPy is notorious (hidden imports,
# data files, the ptb/audio backend); expect a few iterations on the real
# Windows machine (steps.md ADIM_10 SD10).  The comments mark the knobs.
#
# onedir, not onefile: the PsychoPy + Qt + ffmpeg payload is a few hundred MB;
# onefile would unpack it to a temp dir on every launch (slow, fragile).  onedir
# also puts the .exe in a folder where data/, backups/, logs/, config/ and
# stimuli/ sit beside it — exactly the writable_root the app resolves to
# (mcgurk/paths.py, Adim 10c-i).

import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

_HERE = SPECPATH  # the packaging/ directory  (injected by PyInstaller)  # noqa: F821
_ROOT = os.path.dirname(_HERE)  # repository root

datas = []
binaries = []
hiddenimports = []

# The heavy, freeze-hostile packages: collect their data files, native libs and
# submodules wholesale.  collect_all is the blunt-but-reliable tool here.
for _pkg in (
    "psychopy",
    "psychtoolbox",
    "pyglet",
    "ffpyplayer",
    "sounddevice",
    "soundfile",
    "imageio_ffmpeg",
    "questplus",
    # ruamel.yaml lives under the `ruamel` *namespace* package and pulls its
    # submodules in lazily, so PyInstaller's static scan sees only the few the
    # panel names.  The Ayarlar tab writes experiment.yaml through it (Adim 11)
    # and a missing submodule would surface only when the operator pressed
    # Kaydet.  The C accelerator (_ruamel_yaml.pyd) is deliberately not chased:
    # it serves the safe/unsafe parsers, and the writer here is round-trip mode,
    # which is pure Python.
    "ruamel.yaml",
):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# Several packages read their own installed version at runtime via
# importlib.metadata (PsychoPy's __version__, pydantic, numpy...); without the
# dist-info the frozen app raises PackageNotFoundError on import.
for _pkg in (
    "psychopy",
    "numpy",
    "scipy",
    "pandas",
    "pydantic",
    "soundfile",
    "sounddevice",
):
    datas += copy_metadata(_pkg)

# setuptools 78 vendors jaraco.context, which does `from backports import
# tarfile`.  From source, setuptools' VendorImporter remaps that; frozen, it
# does not, so the pkg_resources runtime hook dies with "No module named
# 'backports'" unless the real package is bundled (installed via
# requirements-dev.txt).
hiddenimports += ["backports", "backports.tarfile"]

# Project data the code reads at runtime, kept relative to the bundle root so it
# lands where the source layout expects it (resource_root == _MEIPASS frozen):
#   * schema.sql   — mcgurk/db/database.py reads it via Path(__file__).with_name
#   * experiment.yaml — the bundled default; copied to the writable config on
#     first run (mcgurk/paths.ensure_writable_config)
#   * experiment.defaults.yaml — the factory repetition counts the Ayarlar
#     tab's "Varsayilana don" reads (Adim 11).  Read from resource_root, never
#     the writable copy: the whole point is that the operator cannot have
#     edited it.
#   * word_lists/  — AVSR list templates (disabled today; bundled for later)
#   * tools/       — the --run dispatcher runs verify_stimuli / verify_backup /
#     run_module via runpy, so the scripts must be in the bundle
datas += [
    (os.path.join(_ROOT, "mcgurk", "db", "schema.sql"), os.path.join("mcgurk", "db")),
    (os.path.join(_ROOT, "config", "experiment.yaml"), "config"),
    (os.path.join(_ROOT, "config", "experiment.defaults.yaml"), "config"),
    (os.path.join(_ROOT, "config", "word_lists"), os.path.join("config", "word_lists")),
    (os.path.join(_ROOT, "tools"), "tools"),
]

# stimuli/ is NOT bundled (hundreds of MB); the operator places it beside the
# .exe (dist/McGurkSSD/stimuli/).  See packaging/README.md and TEST_ADIM_10C.md.

# Exclusions.
#   * PySide6/shiboken6: the env has PySide6 too, but PyInstaller refuses two Qt
#     bindings in one frozen app.  PsychoPy's dialogs (psychopy.gui) import PyQt
#     directly (never PySide6), so the whole app standardises on PyQt6 and
#     PySide6 is the binding dropped.
#   * matplotlib is deliberately NOT excluded: PsychoPy imports it in places, and
#     a size pass is safer once the build runs.
excludes = [
    "PySide6",
    "PySide2",
    "shiboken6",
    "tkinter",
    "pytest",
    "_pytest",
    "IPython",
    "jedi",
    "ruff",
    "mypy",
]

block_cipher = None

a = Analysis(  # noqa: F821
    [os.path.join(_HERE, "mcgurk_app.py")],
    pathex=[_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

# Drop the stray ICU that PyInstaller's dependency scan pulls in (icuuc.dll /
# icudt*.dll — grabbed from conda's Library\bin on the build PATH).  It is an
# older ICU than Qt6 6.11 needs and, being under _internal/, it shadows the ICU
# that ships in Windows at runtime, so Qt6Core.dll fails to load with
# "procedure not found" (DLL load failed while importing QtWidgets).  No env
# package depends on it (a source run has no bundled ICU either); removing it
# lets Qt fall back to the system ICU, exactly as from source.
a.binaries = [
    b for b in a.binaries if not os.path.basename(b[0]).lower().startswith("icu")
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="McGurkSSD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=False (windowed) for the release: the operator sees no console
    # window.  A windowed frozen build has sys.stdout = None, so app_entry
    # reattaches stdout/stderr to the panel's pipe for --run subcommands (see
    # mcgurk/app_entry._setup_stdio).  For build debugging, flip back to True to
    # see import/startup errors in a terminal.
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="McGurkSSD",
)
