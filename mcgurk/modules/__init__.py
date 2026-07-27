"""Assessment modules.

Each module answers three questions, and they live in separate files because
they need different things in order to run:

``base.py``, ``mcgurk.py``, ``avsr.py``, ``tbw.py``
    *What is presented, in what order, and what does a response mean.*  Pure
    Python — the design, the categorisation, the scoring and the psychometric
    fit are testable in CI, which is where "same seed → same trial order",
    "Vis-/ga/ + Aud-/ba/ → /da/ is a fusion", "V-only is not crossed with noise
    and ear" and "a known PSS and sigma are recovered from simulated data" are
    actually checked.
``response.py``
    *How the answer is collected.*  PsychoPy: the option grid, the keyboard, the
    two reaction times, the free-text field.
``block.py``
    *The trial loop.*  Sequences fixation → presentation → response → database
    and owns the block boundaries that §A.5 puts the commits on.  One loop
    serves every module that takes a single forced choice; what differs between
    them arrives as a ``TrialPolicy``.

Adım 4 fills in McGurk, Adım 5 AVSR and Adım 6 TBW.  Oddball (Adım 7),
Dichotic (Adım 7b) and GIN (Adım 7c) follow; their designs are already described
by ``mcgurk.config.schema`` and their trials already have a place in the
database.  The last two cannot share the loop as it stands — a GIN segment
collects several responses inside one stimulus and an oddball block is a
continuous stream — which is why ``base.py`` holds only what is genuinely
shared.
"""
