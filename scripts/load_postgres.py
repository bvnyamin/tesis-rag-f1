"""Wrapper para cargar las tablas principales del dataset en PostgreSQL."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from f1_rag.database.cli import main


if __name__ == "__main__":
    main()
