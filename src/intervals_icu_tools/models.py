"""Pydantic models for Intervals.ICU API entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class Activity(BaseModel):
    """Core activity fields. extra='allow' passes through all 173+ API fields."""

    model_config = ConfigDict(extra="allow")

    id: str
    start_date_local: str | None = None
    type: str | None = None
    name: str | None = None
    description: str | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    average_cadence: float | None = None
    calories: int | None = None
    trainer: bool | None = None
    perceived_exertion: float | None = None
    icu_training_load: float | None = None
    icu_atl: float | None = None
    icu_ctl: float | None = None
    icu_ftp: int | None = None
    icu_weighted_avg_watts: int | None = None
    icu_joules: int | None = None
    trimp: float | None = None
    file_type: str | None = None
    icu_athlete_id: str | None = None
    tags: list[str] | None = None


class ActivitySearchResult(BaseModel):
    """Lightweight search result. extra='allow' for any additional fields."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str | None = None
    start_date_local: str | None = None
    type: str | None = None
    race: bool | None = None
    distance: float | None = None
    moving_time: int | None = None
    tags: list[str] | None = None
    description: str | None = None


class FileDownloadResult(BaseModel):
    """Metadata returned after a streaming file download."""

    path: Path
    size_bytes: int
    content_type: str
    filename: str
