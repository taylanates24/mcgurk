"""AVSR word lists — the schema, and reading one from disk.

The word set is the part of Modül 2 that has no content yet: the recording
session has not happened (§F.2, ``04_kod_disi_isler.md`` §2).  What exists here
is the shape it will have, so that the day the recordings arrive nothing but a
file and a flag has to change (steps.md §C Adım 5: "Uyaran seti veri odaklı
olmalı … kod değişmez").

A list lives in its own file rather than inline in ``experiment.yaml`` because
it is a corpus: fifty phonetically balanced words with a provenance worth
recording, not five lines of experimental design.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class WordListError(RuntimeError):
    """A word list is missing, unparseable or invalid."""


class WordList(BaseModel):
    """One stimulus list: the items, and where they came from."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    language: str = Field(default="tr", min_length=2)
    #: Free text: which list this is, who compiled it, which publication.
    description: str = ""
    #: The words themselves, exactly as they must be answered and exactly as
    #: the prepared stimulus files are named.  Empty in the shipped template
    #: (§F.2) — checked below rather than with ``min_length`` so the message
    #: says what to do about it.
    items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _items_are_usable(self) -> WordList:
        if not self.items:
            raise ValueError(
                "items boş — kelime listesi doldurulmadan bu stimulus_set "
                "etkinleştirilemez. Kayıt yapılmadı (§F.2); ayrıntı: "
                "config/word_lists/README.md"
            )
        stripped = [item.strip() for item in self.items]
        if any(not item for item in stripped):
            raise ValueError("items boş bir girdi içeriyor")
        lowered = [item.casefold() for item in stripped]
        duplicates = sorted({item for item in lowered if lowered.count(item) > 1})
        if duplicates:
            raise ValueError(
                f"items tekrarlı kelime içeriyor: {duplicates}. Tekrar sayısı "
                "'reps' ile verilir; listede iki kez geçen bir kelime o kelimeyi "
                "sessizce iki katı sunar"
            )
        if any(item != item.strip() for item in self.items):
            raise ValueError("items baştaki/sondaki boşlukları içeriyor")
        return self


def load_word_list(path: Path) -> WordList:
    """Read and validate the word list at *path*.

    Raises:
        WordListError: for every failure mode, naming the file.
    """
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WordListError(f"Kelime listesi okunamadı: {path} ({exc})") from exc

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise WordListError(f"Kelime listesi geçerli YAML değil: {path}\n{exc}") from exc

    if not isinstance(raw, dict):
        raise WordListError(f"Kelime listesi bir eşleme (mapping) olmalı: {path}")

    try:
        return WordList.model_validate(raw)
    except ValueError as exc:
        raise WordListError(f"Kelime listesi geçersiz: {path}\n{exc}") from exc
