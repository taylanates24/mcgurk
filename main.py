"""McGurk / SSD experiment — entry point.

Runs the new platform's full session flow (``mcgurk.ui``): participant login,
the pre-session checklist, practice, every module in order with its breaks, the
cross-hearing check, and the closing backup — with resume for an interrupted
session.  All arguments are forwarded (``--limit``, ``--db``, ``--device``,
``--new-session``); see ``python main.py --help``.

The Adım 0 baseline that used to live here — the ``src/`` package, the old
``main.py``/``admin.py`` and ``config.yaml`` — is frozen under ``legacy/`` and is
no longer run (see ``legacy/README.md``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcgurk.ui.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
