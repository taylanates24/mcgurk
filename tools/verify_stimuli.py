"""Audit the prepared stimulus set (steps.md §C Adım 2).

Re-measures every prepared file from disk and checks it against the manifest
and against what the enabled modules will ask for.  Run it after preparing,
after copying the set to another machine, and before a data-collection
session — the session checklist (Adım 8) calls the same code.

    python tools/verify_stimuli.py
    python tools/verify_stimuli.py --quick     # presence and checksums only

Exit code 0 = the set is usable, 1 = do not collect data with it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.loader import ConfigError, load_config, resolve_path  # noqa: E402
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.paths import detect_runtime, ensure_writable_config  # noqa: E402
from mcgurk.stimuli.verify import verify  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_stimuli", description="Hazırlanmış uyaran setini denetle"
    )
    parser.add_argument("--config", type=Path, default=None, help="Config dosyası")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Yalnızca dosya varlığı ve sağlama toplamı (ölçüm yapma)",
    )
    parser.add_argument(
        "--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args(argv)

    # Shared path layer (§A10.6): repo root from source, the writable location
    # beside the .exe when frozen (where the operator places stimuli/).
    runtime = detect_runtime()
    config_path = args.config or ensure_writable_config(runtime)
    try:
        config = load_config(config_path, project_root=runtime.writable_root)
    except ConfigError as exc:
        print(f"KIRMIZI  {exc}", file=sys.stderr)
        return 1

    setup_logging(
        resolve_path(runtime.writable_root, config.paths.logs),
        console_level=args.log_level,
        file_level=config.logging.file_level,
    )

    report = verify(config, runtime.writable_root, deep=not args.quick)
    print(report.text())
    print()
    if report.failures:
        print(f"SONUÇ: UYARAN SETİ KULLANILAMAZ ({report.failures} sorun)")
        return 1
    print("SONUÇ: UYARAN SETİ KULLANILABİLİR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
