"""Editing the repetition counts in ``config/experiment.yaml`` (Adım 11a).

The trial counts are the one part of the design a researcher realistically has
to change without a developer: §F.1 ships *minimums*, and raising them is a
config edit and nothing else.  Until now that edit meant opening a 450-line
commented YAML file in a text editor.  This module is what the panel's
"Ayarlar" tab drives instead — and it is deliberately GUI-free (§A11.3), so the
part that decides what lands on disk is testable in CI without PyQt6.

Three rules shape it:

* **Comments survive the write (§A11.1).**  ``experiment.yaml`` is mostly
  explanation — why 10 reps and not 5, why the oddball count was *not* reduced.
  Re-dumping it with pyyaml would delete all of it, so writing goes through
  ``ruamel.yaml``'s round-trip mode, which touches only the scalars that
  changed.  Reading stays on pyyaml (:mod:`mcgurk.config.loader`); only the
  writer needs the fidelity.  A test asserts that a write with no changes leaves
  the file byte-identical, which is what keeps "only the edited key changes"
  true rather than merely intended.
* **Validate, or roll back (§A11.2).**  After the new text is on disk it is
  loaded through :func:`~mcgurk.config.loader.load_config`.  A value the schema
  refuses — a rep count of zero, an oddball trial count too small to carry its
  targets — restores the previous bytes and raises.  A broken config is never
  left behind: the operator's next session must start.
* **The defaults are data, not constants (§A11.4).**  "Varsayılana dön" reads
  ``config/experiment.defaults.yaml``, a read-only file kept in git beside the
  live one.  Hard-coding the factory numbers here would put the design in the
  code, which is exactly what §A.9 forbids; and the live file cannot be its own
  reference, because from a source checkout it *is* the file being edited.

This module imports no PsychoPy and no PyQt6.
"""

from __future__ import annotations

import io
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .loader import ConfigError, load_config
from .schema import ExperimentConfig

#: Canonical factory values, relative to a root.  Read-only: nothing writes it,
#: and "Varsayılana dön" is the only thing that reads it.
DEFAULTS_RELATIVE_PATH = Path("config") / "experiment.defaults.yaml"

#: Upper bounds for the spin boxes.  These are *UI guardrails*, not design
#: rules — the design is whatever the config says, and the schema is what
#: refuses an impossible one.  They exist so a stray keystroke cannot ask for a
#: 40-hour session; anything genuinely larger is still a text-editor edit away.
_MAX_REPS = 100
_MAX_TRIALS = 5000


@dataclass(frozen=True)
class RepField:
    """One editable repetition count.

    ``key`` is the YAML path written out flat (``modules.tbw.reps_per_soa``,
    ``modules.mcgurk.av_pairs[0].reps``) and is what
    ``config/experiment.defaults.yaml`` is keyed by; ``path`` is the same thing
    as a tuple, which is what walks the document.  Keys are positional rather
    than named after ``label``: the schema does not require the labels to be
    unique, and a duplicate would silently make two fields one.
    """

    key: str
    #: Grouping for the panel: a module name, ``practice`` or ``cross_hearing``.
    module: str
    #: Turkish, operator-facing.
    label: str
    value: int
    minimum: int
    maximum: int
    #: Keys and list indices from the document root down to the scalar.
    path: tuple[str | int, ...]
    #: One line of Turkish context — what this number gets multiplied by.
    note: str = ""


def _as_int(value: Any) -> int | None:
    """*value* if it is a plain integer, else None (bools are not counts)."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _fields_from_mapping(data: Mapping[str, Any]) -> list[RepField]:
    """The editable counts of a config, given as a nested mapping.

    Taking a mapping rather than an :class:`ExperimentConfig` is what lets the
    reader and the writer share one definition: :func:`read_reps` passes a
    model dump, :func:`write_reps` passes the ruamel document it is about to
    edit.  Two derivations of the same field list would drift, and the drift
    would show up as a panel that edits a key the defaults file has never heard
    of.

    Disabled modules contribute nothing: their counts do not reach a session,
    so a spin box for them would be a control with no effect.  ``gin`` is
    absent on purpose — its trials are prepared noise segments (Adım 2), not a
    repetition knob, and changing ``reps_per_gap`` would invalidate the 4-of-6
    threshold rule and the published norms with it.
    """
    fields: list[RepField] = []
    session = _mapping(data.get("session"))
    modules = _mapping(data.get("modules"))

    practice = _as_int(session.get("practice_trials"))
    if practice is not None:
        fields.append(
            RepField(
                key="session.practice_trials",
                module="practice",
                label="Alıştırma denemesi",
                value=practice,
                minimum=0,
                maximum=_MAX_TRIALS,
                path=("session", "practice_trials"),
                note="Kaydedilmez; yalnızca göreve alışma içindir.",
            )
        )

    mcgurk = _mapping(modules.get("mcgurk"))
    if mcgurk.get("enabled"):
        n_cells = len(_sequence(mcgurk.get("noise_conditions"))) * len(
            _sequence(mcgurk.get("ears"))
        )
        for index, pair in enumerate(_sequence(mcgurk.get("av_pairs"))):
            entry = _mapping(pair)
            value = _as_int(entry.get("reps"))
            if value is None:
                continue
            fields.append(
                RepField(
                    key=f"modules.mcgurk.av_pairs[{index}].reps",
                    module="mcgurk",
                    label="{} (V:{} / A:{})".format(
                        entry.get("label", index),
                        entry.get("visual", "?"),
                        entry.get("audio", "?"),
                    ),
                    value=value,
                    minimum=1,
                    maximum=_MAX_REPS,
                    path=("modules", "mcgurk", "av_pairs", index, "reps"),
                    note=(
                        f"Hücre başına: gürültü x kulak = {n_cells} ile çarpılır."
                    ),
                )
            )

    avsr = _mapping(modules.get("avsr"))
    if avsr.get("enabled"):
        for index, stimulus_set in enumerate(_sequence(avsr.get("stimulus_sets"))):
            entry = _mapping(stimulus_set)
            value = _as_int(entry.get("reps"))
            if value is None or not entry.get("enabled"):
                continue
            tokens = _sequence(entry.get("tokens"))
            if entry.get("type") == "syllable":
                label = "Hece seti"
                if tokens:
                    label += " (" + ", ".join(str(t) for t in tokens) + ")"
            else:
                label = "Kelime listesi"
            fields.append(
                RepField(
                    key=f"modules.avsr.stimulus_sets[{index}].reps",
                    module="avsr",
                    label=label,
                    value=value,
                    minimum=1,
                    maximum=_MAX_REPS,
                    path=("modules", "avsr", "stimulus_sets", index, "reps"),
                    note=(
                        "Öğe başına: sunum modu x gürültü x kulak ile çarpılır "
                        "(yalnız-görüntü modu çaprazlanmaz)."
                    ),
                )
            )

    tbw = _mapping(modules.get("tbw"))
    if tbw.get("enabled"):
        value = _as_int(tbw.get("reps_per_soa"))
        if value is not None:
            n_soa = len(_sequence(tbw.get("soa_values_ms")))
            fields.append(
                RepField(
                    key="modules.tbw.reps_per_soa",
                    module="tbw",
                    label="SOA değeri başına tekrar",
                    value=value,
                    minimum=1,
                    maximum=_MAX_REPS,
                    path=("modules", "tbw", "reps_per_soa"),
                    note=f"{n_soa} SOA değeri ile çarpılır.",
                )
            )

    oddball = _mapping(modules.get("oddball"))
    if oddball.get("enabled"):
        value = _as_int(oddball.get("n_trials"))
        if value is not None:
            fields.append(
                RepField(
                    key="modules.oddball.n_trials",
                    module="oddball",
                    label="Toplam ton sayısı",
                    value=value,
                    minimum=1,
                    maximum=_MAX_TRIALS,
                    path=("modules", "oddball", "n_trials"),
                    note=(
                        "Toplamdır, çarpılmaz; hedef sayısı hedef oranıyla "
                        "belirlenir."
                    ),
                )
            )

    dichotic = _mapping(modules.get("dichotic"))
    if dichotic.get("enabled"):
        value = _as_int(dichotic.get("reps"))
        if value is not None:
            n_pairs = len(_sequence(dichotic.get("pairs")))
            fields.append(
                RepField(
                    key="modules.dichotic.reps",
                    module="dichotic",
                    label="Çift başına tekrar",
                    value=value,
                    minimum=1,
                    maximum=_MAX_REPS,
                    path=("modules", "dichotic", "reps"),
                    note=f"{n_pairs} çift ile çarpılır.",
                )
            )

    cross_hearing = _mapping(data.get("cross_hearing_check"))
    if cross_hearing.get("enabled"):
        value = _as_int(cross_hearing.get("n_trials"))
        if value is not None:
            fields.append(
                RepField(
                    key="cross_hearing_check.n_trials",
                    module="cross_hearing",
                    label="Deneme sayısı",
                    value=value,
                    minimum=1,
                    maximum=_MAX_TRIALS,
                    path=("cross_hearing_check", "n_trials"),
                    note="Yarısı sessiz (catch) denemedir.",
                )
            )

    return fields


def read_reps(config: ExperimentConfig) -> list[RepField]:
    """Every repetition count the panel may edit, with its current value."""
    return _fields_from_mapping(config.model_dump(mode="python"))


def _set_on_model(model: ExperimentConfig, path: tuple[str | int, ...], value: int) -> None:
    target: Any = model
    for part in path[:-1]:
        target = target[part] if isinstance(part, int) else getattr(target, part)
    last = path[-1]
    assert isinstance(last, str)  # every path ends at a named scalar
    setattr(target, last, value)


def preview_reps(
    config: ExperimentConfig, changes: Mapping[str, int]
) -> ExperimentConfig:
    """A copy of *config* with the given counts applied — nothing is written.

    This is what makes the tab's "Toplam: N deneme / ~X dk" live: the numbers
    come from :meth:`ExperimentConfig.trial_counts` on the preview, so the
    estimate the operator reads is produced by the same code the session will
    run, not by arithmetic repeated in the GUI.

    ``validate_assignment`` is on for every model (§G), so an impossible value
    is refused here too and comes back as a :class:`ConfigError` rather than as
    a total.  That is a convenience, not the gate: the real one is
    :func:`write_reps`, which re-loads the whole file.
    """
    fields = {field.key: field for field in read_reps(config)}
    _reject_unknown_keys(changes, fields)

    preview = config.model_copy(deep=True)
    for key, value in changes.items():
        field = fields[key]
        try:
            _set_on_model(preview, field.path, int(value))
        except ValidationError as exc:
            raise ConfigError(
                f"{field.label}: {value} geçerli değil.\n{_first_message(exc)}"
            ) from exc
    return preview


def _first_message(exc: ValidationError) -> str:
    errors = exc.errors()
    return str(errors[0]["msg"]) if errors else str(exc)


def _reject_unknown_keys(
    changes: Mapping[str, int], fields: Mapping[str, RepField]
) -> None:
    unknown = sorted(set(changes) - set(fields))
    if unknown:
        raise ConfigError(
            "Düzenlenebilir olmayan ayar anahtarı: "
            + ", ".join(unknown)
            + ". Düzenlenebilenler: "
            + ", ".join(sorted(fields))
        )


def _round_trip_yaml() -> YAML:
    """A ruamel loader/dumper tuned to reproduce ``experiment.yaml`` exactly.

    Three settings, each for a failure this file actually shows:

    * ``width`` — the default of 80 re-wraps long plain scalars, and the
      participant-facing screen texts are single lines of several hundred
      characters.  Re-wrapped, they still parse, but every one of them turns
      into a multi-line diff on an unrelated save.
    * ``indent`` — the file indents block sequences under their key
      (``  - {…}`` beneath ``av_pairs:``); ruamel's default would pull the
      dashes back to the key's own column.
    * the null representer — round-trip mode writes ``None`` as an empty
      value, so ``system_av_offset_ms: null`` would silently become
      ``system_av_offset_ms:``.  It parses the same, but the explicit ``null``
      is what tells a reader the field is deliberately unset rather than
      forgotten.
    """
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    yaml_rt.width = 1_000_000
    yaml_rt.indent(mapping=2, sequence=4, offset=2)
    yaml_rt.representer.add_representer(
        type(None),
        lambda representer, _data: representer.represent_scalar(
            "tag:yaml.org,2002:null", "null"
        ),
    )
    return yaml_rt


def _atomic_write(path: Path, text: str) -> None:
    """Replace *path*'s contents in one step.

    A plain write truncates first, so a crash between truncate and write leaves
    an empty config — and the config is what the next session needs to start.
    ``os.replace`` is atomic on Windows and POSIX alike.  Newlines are written
    verbatim (LF, as the repository stores them): text mode would translate
    them to CRLF on Windows and turn the next save into a whole-file diff.
    """
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(text.encode("utf-8"))
    os.replace(temporary, path)


def write_reps(
    config_path: Path | str,
    project_root: Path | str,
    changes: Mapping[str, int],
) -> ExperimentConfig:
    """Write the given repetition counts into *config_path* and re-validate.

    Only the named scalars change; comments, ordering and layout survive
    (§A11.1).  The file is then loaded again, and if it does not validate the
    previous bytes are put back and :class:`ConfigError` is raised (§A11.2) —
    the operator sees a message and the config on disk is the one that worked.

    ``check_filesystem`` is off in that re-load on purpose: the filesystem gates
    are about calibration and the prepared stimulus set, neither of which a
    repetition count can affect.  Leaving them on would roll back a perfectly
    good edit because, say, ``stimuli/`` had not been copied out yet.

    Returns the reloaded config, so the caller does not have to read the file a
    second time to refresh itself.
    """
    path = Path(config_path)
    try:
        original = path.read_bytes().decode("utf-8")
    except OSError as exc:
        raise ConfigError(f"Config dosyası okunamadı: {path} ({exc})") from exc

    yaml_rt = _round_trip_yaml()
    try:
        document = yaml_rt.load(original)
    except YAMLError as exc:
        raise ConfigError(f"Config geçerli YAML değil: {path}\n{exc}") from exc
    if not isinstance(document, Mapping):
        raise ConfigError(f"Config bir eşleme (mapping) olmalı: {path}")

    fields = {field.key: field for field in _fields_from_mapping(document)}
    _reject_unknown_keys(changes, fields)

    for key, value in changes.items():
        target: Any = document
        for part in fields[key].path[:-1]:
            target = target[part]
        target[fields[key].path[-1]] = int(value)

    buffer = io.StringIO()
    yaml_rt.dump(document, buffer)
    _atomic_write(path, buffer.getvalue())

    try:
        return load_config(path, project_root=project_root, check_filesystem=False)
    except ConfigError as exc:
        _atomic_write(path, original)
        raise ConfigError(
            "Ayarlar kaydedilmedi: yeni değerler geçerli bir tasarım vermiyor, "
            f"dosya eski hâline geri alındı ({path}).\n{exc}"
        ) from exc


# ------------------------------------------------------- speaker (Adım 12c-ii)

#: The keys a speaker change writes.  ``speaker_selection.fixed_id`` is what a
#: real session reads; the four ``modules.*.speaker_id`` are the defaults the
#: dev tools and the design summary use, and leaving them behind would make
#: ``python -m mcgurk.config`` describe a different speaker than the one that
#: gets presented.
_SPEAKER_MODULE_KEYS = ("mcgurk", "avsr", "tbw", "dichotic")


@dataclass(frozen=True)
class SpeakerOption:
    """One row of the panel's "Konuşmacı" tab."""

    speaker_id: int
    label: str
    #: The still prepared in Adım 12c-ii, or None if the set has none.
    image: Path | None
    #: How many sessions have used this speaker so far (the panel fills it in).
    n_sessions: int = 0
    selected: bool = False


def read_speaker(config: ExperimentConfig) -> int | None:
    """The speaker a session would use today, or None if it is not pinned.

    None means ``speaker_selection.strategy`` is ``balanced`` or ``random``: the
    speaker is then decided per session and there is nothing for the tab to tick.
    """
    if config.speaker_selection.strategy != "fixed":
        return None
    return config.speaker_selection.fixed_id


def speaker_options(
    config: ExperimentConfig,
    stimuli_root: Path | str | None = None,
    *,
    session_counts: Mapping[int, int] | None = None,
) -> list[SpeakerOption]:
    """Every prepared speaker, with its still and whether it is the current one.

    The stills come from the prepared set's own folder rather than the manifest
    so this stays importable and testable without one; a missing file simply
    yields ``image=None`` and the tab shows the label alone.
    """
    current = read_speaker(config)
    counts = session_counts or {}
    root = Path(stimuli_root) if stimuli_root is not None else None
    options: list[SpeakerOption] = []
    for speaker in config.stimulus_prep.speakers:
        image = None
        if root is not None:
            candidate = root / "thumbnails" / f"speaker_{speaker.id}.png"
            image = candidate if candidate.is_file() else None
        options.append(
            SpeakerOption(
                speaker_id=speaker.id,
                label=speaker.label or f"Konuşmacı {speaker.id}",
                image=image,
                n_sessions=int(counts.get(speaker.id, 0)),
                selected=speaker.id == current,
            )
        )
    return options


def write_speaker(
    config_path: Path | str,
    project_root: Path | str,
    speaker_id: int,
) -> ExperimentConfig:
    """Pin *speaker_id* in *config_path* and re-validate.

    Writes ``speaker_selection`` (``fixed`` + the id) and the four
    ``modules.*.speaker_id`` in one go: a session reads the first, the dev tools
    and the design summary read the second, and letting them disagree is how a
    "check" ends up describing a speaker that is not the one presented.

    Comments survive and a config the schema refuses is rolled back — the same
    two rules as :func:`write_reps`, for the same reasons.
    """
    path = Path(config_path)
    try:
        original = path.read_bytes().decode("utf-8")
    except OSError as exc:
        raise ConfigError(f"Config dosyası okunamadı: {path} ({exc})") from exc

    yaml_rt = _round_trip_yaml()
    try:
        document = yaml_rt.load(original)
    except YAMLError as exc:
        raise ConfigError(f"Config geçerli YAML değil: {path}\n{exc}") from exc
    if not isinstance(document, Mapping):
        raise ConfigError(f"Config bir eşleme (mapping) olmalı: {path}")

    prepared = [
        _as_int(entry.get("id"))
        for entry in _sequence(_mapping(document.get("stimulus_prep")).get("speakers"))
    ]
    if speaker_id not in prepared:
        raise ConfigError(
            f"Hazır sette olmayan konuşmacı: {speaker_id}. "
            f"Hazır olanlar: {', '.join(str(i) for i in prepared if i is not None)}"
        )

    selection = document["speaker_selection"]
    selection["strategy"] = "fixed"
    selection["fixed_id"] = int(speaker_id)
    for name in _SPEAKER_MODULE_KEYS:
        document["modules"][name]["speaker_id"] = int(speaker_id)

    buffer = io.StringIO()
    yaml_rt.dump(document, buffer)
    _atomic_write(path, buffer.getvalue())

    try:
        return load_config(path, project_root=project_root, check_filesystem=False)
    except ConfigError as exc:
        _atomic_write(path, original)
        raise ConfigError(
            "Konuşmacı kaydedilmedi: seçim geçerli bir tasarım vermiyor, dosya "
            f"eski hâline geri alındı ({path}).\n{exc}"
        ) from exc


def default_reps(root: Path | str | None = None) -> dict[str, int]:
    """The factory repetition counts, keyed exactly like :class:`RepField`.

    Read from ``config/experiment.defaults.yaml`` under *root* — the read-only
    resource root, which frozen is the bundle and from a checkout is the
    repository.  It is a separate file rather than the bundled
    ``experiment.yaml`` because from source those are the same file: the
    "default" would be whatever was last saved, and "Varsayılana dön" would do
    nothing (§A11.4, PLAN_AYARLAR_SEKMESI §Açık nokta).
    """
    base = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    path = base / DEFAULTS_RELATIVE_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(
            f"Varsayılan tekrar sayıları okunamadı: {path} ({exc})"
        ) from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Varsayılan dosyası geçerli YAML değil: {path}\n{exc}") from exc

    reps = _mapping(_mapping(raw).get("reps"))
    if not reps:
        raise ConfigError(f"Varsayılan dosyasında 'reps' eşlemesi yok: {path}")

    defaults: dict[str, int] = {}
    for key, value in reps.items():
        number = _as_int(value)
        if number is None:
            raise ConfigError(
                f"Varsayılan dosyasında '{key}' tam sayı değil: {value!r} ({path})"
            )
        defaults[str(key)] = number
    return defaults
