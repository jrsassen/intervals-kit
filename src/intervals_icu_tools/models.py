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


class Athlete(BaseModel):
    """Athlete profile. extra='allow' passes through all 154+ API fields."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    sex: str | None = None
    weight: float | None = None
    icu_resting_hr: int | None = None
    icu_weight: float | None = None
    icu_ftp: int | None = None
    timezone: str | None = None
    measurement_preference: str | None = None


class WellnessRecord(BaseModel):
    """A single day's wellness data. extra='allow' passes through all 46 fields."""

    model_config = ConfigDict(extra="allow")

    id: str  # ISO-8601 date, e.g. "2024-01-15"
    ctl: float | None = None
    atl: float | None = None
    weight: float | None = None
    restingHR: int | None = None
    hrv: float | None = None
    hrvSDNN: float | None = None
    sleepSecs: int | None = None
    sleepScore: float | None = None
    sleepQuality: int | None = None
    soreness: int | None = None
    fatigue: int | None = None
    stress: int | None = None
    mood: int | None = None
    motivation: int | None = None
    injury: int | None = None
    updated: str | None = None


class Event(BaseModel):
    """A calendar event (planned workout, race, note, etc.). extra='allow' for all 60+ fields."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    athlete_id: str | None = None
    name: str | None = None
    description: str | None = None
    start_date_local: str | None = None
    end_date_local: str | None = None
    category: str | None = None  # WORKOUT, RACE_A/B/C, NOTE, PLAN, etc.
    type: str | None = None
    indoor: bool | None = None
    color: str | None = None
    moving_time: int | None = None
    icu_training_load: int | None = None
    icu_atl: float | None = None
    icu_ctl: float | None = None


class Workout(BaseModel):
    """A workout in the athlete's library. extra='allow' for all 28 fields."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    athlete_id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    indoor: bool | None = None
    color: str | None = None
    moving_time: int | None = None
    icu_training_load: int | None = None
    folder_id: int | None = None
    tags: list[str] | None = None
    updated: str | None = None


class ActivityMessage(BaseModel):
    """A comment on an activity."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    content: str | None = None
    athlete_id: str | None = None
    athlete_name: str | None = None
    updated: str | None = None
