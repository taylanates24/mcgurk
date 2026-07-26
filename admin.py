"""McGurk Experiment — Admin Panel entry point.

Usage:
    python admin.py
    python admin.py --config path/to/config.yaml
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.admin.panel import AdminPanel
from src.config import load_config
from src.data.database import Database


def main():
    config_path = None
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        config_path = sys.argv[2]
    config = load_config(config_path)

    project_root = Path(__file__).resolve().parent
    db_path = project_root / config.get("database_path", "data/mcgurk.db")
    db = Database(db_path)

    app = QApplication(sys.argv)
    window = AdminPanel(db)
    window.show()
    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
