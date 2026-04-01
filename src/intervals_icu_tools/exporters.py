"""Output formatting utilities: serialize data to JSON files or strings."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_json(data: Any, path: Path) -> None:
    """Write data to a JSON file with pretty printing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def to_json_str(data: Any) -> str:
    """Serialize data to a pretty-printed JSON string."""
    return json.dumps(data, indent=2, default=str)


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Write a list of dicts to a CSV file.

    Column order is derived from the union of all keys, with keys from the
    first row appearing first (preserves field order for uniform result sets).
    """
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        return
    # Collect all keys, preserving insertion order, first-row keys first.
    fieldnames: list[str] = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
