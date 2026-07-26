"""Assessment modules.

Each module answers three questions, and they live in separate files because
they need different things in order to run:

``base.py``, ``mcgurk.py``
    *What is presented, in what order, and what does a response mean.*  Pure
    Python — the design and the categorisation are testable in CI, which is
    where "same seed → same trial order" and "Vis-/ga/ + Aud-/ba/ → /da/ is a
    fusion" are actually checked.
``response.py``
    *How the answer is collected.*  PsychoPy: the option grid, the keyboard, the
    two reaction times, the free-text field.
``block.py``
    *The trial loop.*  Sequences fixation → presentation → response → database
    and owns the block boundaries that §A.5 puts the commits on.

Adım 4 fills in McGurk.  AVSR (Adım 5), TBW (Adım 6), Oddball (Adım 7),
Dichotic (Adım 7b) and GIN (Adım 7c) follow; their designs are already described
by ``mcgurk.config.schema`` and their trials already have a place in the
database.  ``base.py`` holds only what is genuinely shared — the trial loop is
not, because a GIN segment collects several responses inside one stimulus and an
oddball block is a continuous stream.
"""
