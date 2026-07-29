"""Assessment modules.

Each module answers three questions, and they live in separate files because
they need different things in order to run:

``base.py``, ``mcgurk.py``, ``avsr.py``, ``tbw.py``, ``oddball.py``,
``dichotic.py``
    *What is presented, in what order, and what does a response mean.*  Pure
    Python — the design, the categorisation, the scoring, the psychometric fit
    and the signal-detection measures are testable in CI, which is where "same
    seed → same trial order", "Vis-/ga/ + Aud-/ba/ → /da/ is a fusion", "V-only
    is not crossed with noise and ear", "a known PSS and sigma are recovered
    from simulated data" and "this press belongs to that tone" are actually
    checked.
``response.py``
    *How the answer is collected.*  PsychoPy: the option grid, the keyboard, the
    two reaction times, the free-text field.
``block.py``
    *The trial loop.*  Sequences fixation → presentation → response → database
    and owns the block boundaries that §A.5 puts the commits on.  One loop
    serves every module that takes a single forced choice; what differs between
    them arrives as a ``TrialPolicy``.
``stream.py``
    *The continuous-stream loop.*  Oddball is not a sequence of trials: tones
    flow on their own schedule and presses are attributed to them afterwards, so
    it needs its own runner rather than a ``TrialPolicy``.

Adım 4 fills in McGurk, Adım 5 AVSR, Adım 6 TBW, Adım 7 Oddball and Adım 7b
Dichotic.  GIN (Adım 7c) follows; its design is already described by
``mcgurk.config.schema`` and its trials already have a place in the database.
It cannot share ``block.py`` as it stands — a GIN segment collects several
responses inside one stimulus — and will join ``stream.py`` instead, which is
why ``base.py`` holds only what is genuinely shared.
"""
