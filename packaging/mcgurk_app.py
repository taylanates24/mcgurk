"""PyInstaller entry point for the frozen operator app (Adım 10c-ii).

PyInstaller runs the entry script as ``__main__``, where a relative import
(``from . import ...``) has no package to resolve against.  So the real entry —
``mcgurk.app_entry`` — is reached through an **absolute** import here; that module
does the ``--run`` dispatch (panel by default, experiment/checklist/tools behind
``--run``).

Running this from a source checkout works too (``python packaging/mcgurk_app.py``):
the repository root is put on ``sys.path`` first, so ``mcgurk`` imports without an
install.  Frozen, that insert is harmless — the package is already importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcgurk.app_entry import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
