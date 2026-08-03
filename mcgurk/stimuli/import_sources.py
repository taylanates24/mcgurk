"""Import delivered raw recordings into the ``assets/`` layout (ADIM 12a).

The corpus arrives as one flat folder of ``Vis-<v>_Aud-<a>_Speaker-<n>.mp4``
files — every visual x auditory combination of every speaker.  Only the
**congruent** takes (``Vis-<t>_Aud-<t>``) are imported: those are the natural
recordings, and every incongruent presentation is built at run time by mounting
one token's audio on another take's silent video (§A.1).  The incongruent files
in the delivery are an older re-mux of the same tokens and are ignored here
exactly as they already are for the two speakers in the project.

Where a speaker's takes go is ``stimulus_prep.speakers[].source`` — the config
is the id->folder mapping (§A.9), so nothing here invents a folder name.

Two rules keep an import from quietly changing what gets presented:

* **A destination that already holds the same bytes is skipped**, not rewritten.
  Speakers 1 and 2 were already in the project and their files must stay the
  file the earlier sessions were run with.
* **A destination that holds *different* bytes stops the import.**  Overwriting
  it would leave no record of which recording the existing prepared set — and
  the sessions run from it — actually came from.

The whole plan is checked before anything is copied, for the same reason
preparation refuses to write a partial set (§A.12): a half-imported corpus
looks complete from the outside.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from . import StimulusError

logger = logging.getLogger(__name__)

#: The delivered file name.  Both tokens are in it; only the congruent takes
#: (visual == audio) are read.
SOURCE_TEMPLATE = "Vis-{visual}_Aud-{audio}_Speaker-{speaker}.mp4"

#: The name the preparation pipeline looks for under a speaker's folder.
DESTINATION_TEMPLATE = "Vis-{visual}_Aud-{audio}.mp4"

#: Read size for hashing.  The takes are ~500 kB, but the delivery folder is
#: not the only caller a corpus ever gets.
_CHUNK_BYTES = 1 << 20


class Verdict(Enum):
    """What the importer intends to do with one congruent take."""

    COPY = "kopyalanacak"
    IDENTICAL = "zaten var (aynı içerik)"
    KEPT = "zaten var (kaynak elde değil, dokunulmadı)"
    CONFLICT = "zaten var (FARKLI içerik)"
    MISSING = "kaynak dosya yok"


@dataclass(frozen=True)
class ImportItem:
    """One congruent take, its destination, and the decision made about it."""

    speaker_id: int
    token: str
    source: Path
    destination: Path
    verdict: Verdict

    def describe(self) -> str:
        return (
            f"Konuşmacı {self.speaker_id} /{self.token}/: "
            f"{self.verdict.value} -> {self.destination}"
        )


@dataclass(frozen=True)
class ImportReport:
    """What an import actually did."""

    copied: tuple[ImportItem, ...]
    skipped: tuple[ImportItem, ...]

    @property
    def total(self) -> int:
        return len(self.copied) + len(self.skipped)


def file_digest(path: Path) -> str:
    """sha256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _same_bytes(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    return file_digest(left) == file_digest(right)


def plan_import(
    config: ExperimentConfig,
    project_root: Path,
    source_dir: Path,
    *,
    speaker_ids: list[int] | None = None,
) -> list[ImportItem]:
    """Decide what would be copied where, without touching anything.

    ``speaker_ids`` restricts the plan to some of the declared speakers; the
    default is every speaker in ``stimulus_prep.speakers``.
    """
    prep = config.stimulus_prep
    wanted = prep.speaker_ids() if speaker_ids is None else list(speaker_ids)
    unknown = sorted(set(wanted) - set(prep.speaker_ids()))
    if unknown:
        raise StimulusError(
            f"stimulus_prep.speakers içinde olmayan konuşmacı: {unknown}"
        )

    items: list[ImportItem] = []
    for speaker_id in wanted:
        destination_dir = resolve_path(project_root, prep.source_for(speaker_id))
        for token in prep.tokens:
            source = source_dir / SOURCE_TEMPLATE.format(
                visual=token, audio=token, speaker=speaker_id
            )
            destination = destination_dir / DESTINATION_TEMPLATE.format(
                visual=token, audio=token
            )
            items.append(
                ImportItem(
                    speaker_id=speaker_id,
                    token=token,
                    source=source,
                    destination=destination,
                    verdict=_decide(source, destination),
                )
            )
    return items


def _decide(source: Path, destination: Path) -> Verdict:
    if not source.is_file():
        # A destination that is already in place makes a missing source
        # harmless: the import can be re-run after the delivery folder is gone.
        # It is a separate verdict from IDENTICAL because nothing was compared
        # — saying the two match would be a claim this branch cannot make.
        return Verdict.KEPT if destination.is_file() else Verdict.MISSING
    if not destination.is_file():
        return Verdict.COPY
    return Verdict.IDENTICAL if _same_bytes(source, destination) else Verdict.CONFLICT


def apply_import(items: list[ImportItem], *, dry_run: bool = False) -> ImportReport:
    """Copy everything the plan marks ``COPY``, or refuse the whole plan.

    Nothing is copied until every item has been checked, and a conflict or a
    missing source aborts before the first write.
    """
    blocked = [item for item in items if item.verdict is Verdict.CONFLICT]
    if blocked:
        lines = "\n".join(
            f"  {item.destination} (kaynak: {item.source})" for item in blocked
        )
        raise StimulusError(
            "Hedef dosya var ve içeriği kaynaktan FARKLI; içe aktarma durdu.\n"
            "Üzerine yazmak, hazırlanmış setin hangi kayıttan geldiğini\n"
            "belirsizleştirirdi. Önce elle inceleyin:\n" + lines
        )

    missing = [item for item in items if item.verdict is Verdict.MISSING]
    if missing:
        lines = "\n".join(f"  {item.source}" for item in missing)
        raise StimulusError("Kaynak kayıt bulunamadı; içe aktarma durdu:\n" + lines)

    to_copy = [item for item in items if item.verdict is Verdict.COPY]
    skipped = [
        item
        for item in items
        if item.verdict in (Verdict.IDENTICAL, Verdict.KEPT)
    ]

    if not dry_run:
        for item in to_copy:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, item.destination)
            logger.info("Kopyalandı: %s -> %s", item.source, item.destination)

    return ImportReport(copied=tuple(to_copy), skipped=tuple(skipped))
