"""McGurk / SSD assessment platform.

This package replaces the Adım 0 baseline in ``src/``.  It is built alongside
it: ``src/`` keeps running the legacy experiment until the session flow moves
over in Adım 8 (see progress.md, decision A0-1).

Nothing under ``mcgurk.config`` or ``mcgurk.db`` may import PsychoPy.  Those
layers have to stay importable on a headless CI runner with no audio device,
and PsychoPy's import has side effects (preference files, audio probing) that
do not belong in a config parser.
"""

__version__ = "1.0.0"
