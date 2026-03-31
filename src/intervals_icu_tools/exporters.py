"""Output formatting utilities: serialize data to JSON files or strings."""

from __future__ import annotations

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
