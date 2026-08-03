"""Import the delivered raw recordings into ``assets/`` (ADIM 12a).

The delivery is one flat folder of ``Vis-<v>_Aud-<a>_Speaker-<n>.mp4`` files.
Only the **congruent** takes are imported — the pipeline builds every
incongruent presentation itself (§A.1) — and each speaker's takes land in the
folder ``stimulus_prep.speakers[].source`` names, under the pipeline's own
``Vis-<t>_Aud-<t>.mp4`` naming.

    python tools/import_speakers.py --dry-run       # what would happen
    python tools/import_speakers.py                 # copy
    python tools/import_speakers.py --speaker 5 --speaker 6
    python tools/import_speakers.py --source speakers

A destination that already holds the same bytes is skipped; one that holds
different bytes stops the import before anything is written.

Exit code 0 = the assets tree matches the config, 1 = nothing was copied.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.loader import ConfigError, load_config  # noqa: E402
from mcgurk.stimuli import StimulusError  # noqa: E402
from mcgurk.stimuli.import_sources import apply_import, plan_import  # noqa: E402

#: Where the recordings were delivered.  Not a config value: it is the folder
#: a corpus arrives in, not a property of the design.
DEFAULT_SOURCE = "speakers"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="import_speakers",
        description="Ham kayıtları assets/ altına aktar (yalnız uyumlu takeler)",
    )
    parser.add_argument("--config", type=Path, default=None, help="Config dosyası")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(DEFAULT_SOURCE),
        help=f"Ham kayıtların bulunduğu klasör (varsayılan: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--speaker",
        type=int,
        action="append",
        dest="speakers",
        help="Yalnız bu konuşmacı (birden fazla verilebilir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hiçbir şey kopyalama, ne yapılacağını yaz",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT)
    except ConfigError as exc:
        print(f"KIRMIZI  {exc}", file=sys.stderr)
        return 1

    source_dir = args.source
    if not source_dir.is_absolute():
        source_dir = _PROJECT_ROOT / source_dir

    try:
        items = plan_import(
            config, _PROJECT_ROOT, source_dir, speaker_ids=args.speakers
        )
        for item in items:
            print(f"  {item.describe()}")
        report = apply_import(items, dry_run=args.dry_run)
    except StimulusError as exc:
        print(f"\nKIRMIZI  {exc}", file=sys.stderr)
        return 1

    print()
    verb = "Kopyalanacak" if args.dry_run else "Kopyalandı"
    print(f"{verb:<14}: {len(report.copied)}")
    print(f"{'Atlandı':<14}: {len(report.skipped)}")
    if args.dry_run:
        print("\nSONUÇ: DENEME (hiçbir dosya yazılmadı)")
    else:
        print("\nSONUÇ: HAM KAYITLAR YERİNDE")
        print("Sırada: python tools/prepare_stimuli.py --force")
    return 0


if __name__ == "__main__":
    sys.exit(main())
