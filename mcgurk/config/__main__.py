"""``python -m mcgurk.config`` — validate a config and print the design summary.

steps.md §G: the trial-count decision (§F.1) is meant to be made against this
output, so it has to be reachable without starting an experiment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .loader import ConfigError, load_config, summarise_design


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcgurk.config",
        description="Config'i doğrula ve tasarım özetini yazdır",
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Config dosyası yolu"
    )
    parser.add_argument(
        "--no-filesystem-check",
        action="store_true",
        help="data_collection dosya kontrollerini atla (yalnızca şema doğrula)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(
            args.config, check_filesystem=not args.no_filesystem_check
        )
    except ConfigError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    print(summarise_design(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
