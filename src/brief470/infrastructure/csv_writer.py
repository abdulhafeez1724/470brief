from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path


class CsvTableWriter:
    """Writes CSV files under a base directory (data/private, which git ignores)."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def write(self, name: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
        path = self._base_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)
        return str(path)
