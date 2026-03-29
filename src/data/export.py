"""CSV/Excel export for experiment data."""

import csv
from pathlib import Path

from .database import Database


def export_trials_csv(db: Database, output_path: str | Path):
    """Export all trials to a CSV file."""
    trials = db.get_all_trials()
    if not trials:
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(trials[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trials)


def export_participants_csv(db: Database, output_path: str | Path):
    """Export all participants to a CSV file."""
    participants = db.get_all_participants()
    if not participants:
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(participants[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(participants)
