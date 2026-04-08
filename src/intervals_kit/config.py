"""Configuration management for intervals-icu-tools.

Priority chain: environment variables > config file > error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, field_validator

CONFIG_FILE = Path.home() / ".config" / "intervals-icu-tools" / "config.toml"


class ApiConfig(BaseModel):
    api_key: str
    athlete_id: str
    base_url: str = "https://intervals.icu"
    timeout: float = 30.0

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


def load_config() -> ApiConfig:
    """Load config from env vars > config file > error.

    Called lazily (inside each MCP tool / CLI command), never at module import.
    """
    data: dict = {}

    # Config file — lowest priority
    if CONFIG_FILE.exists():
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomllib  # type: ignore[no-redef]
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

    # Env vars override config file
    if api_key := os.getenv("INTERVALS_API_KEY"):
        data["api_key"] = api_key
    if athlete_id := os.getenv("INTERVALS_ATHLETE_ID"):
        data["athlete_id"] = athlete_id
    if base_url := os.getenv("INTERVALS_BASE_URL"):
        data["base_url"] = base_url

    try:
        return ApiConfig(**data)
    except Exception as e:
        raise ValueError(
            f"Configuration error: {e}. "
            "Set INTERVALS_API_KEY and INTERVALS_ATHLETE_ID environment variables, "
            "or create ~/.config/intervals-icu-tools/config.toml with api_key and athlete_id."
        ) from e
