"""Shared test fixtures for intervals-icu-tools."""

from __future__ import annotations

import pytest


ATHLETE_ID = "itest"
API_KEY = "test-api-key"
BASE_URL = "https://intervals.icu"


@pytest.fixture(autouse=True)
def env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for all tests."""
    monkeypatch.setenv("INTERVALS_API_KEY", API_KEY)
    monkeypatch.setenv("INTERVALS_ATHLETE_ID", ATHLETE_ID)


@pytest.fixture
def sample_activity() -> dict:
    return {
        "id": "99001",
        "name": "Morning Ride",
        "type": "Ride",
        "start_date_local": "2024-06-15T07:00:00",
        "distance": 45000.0,
        "moving_time": 5400,
        "elapsed_time": 5600,
        "total_elevation_gain": 350.0,
        "average_speed": 8.33,
        "average_heartrate": 145.0,
        "icu_training_load": 85,
        "icu_ftp": 250,
        "icu_weighted_avg_watts": 210,
        "tags": ["outdoor", "base"],
    }


@pytest.fixture
def sample_activities(sample_activity: dict) -> list[dict]:
    return [
        sample_activity,
        {
            "id": "99002",
            "name": "Easy Run",
            "type": "Run",
            "start_date_local": "2024-06-16T06:30:00",
            "distance": 8000.0,
            "moving_time": 2700,
            "elapsed_time": 2750,
            "total_elevation_gain": 50.0,
            "average_speed": 2.96,
            "average_heartrate": 135.0,
            "icu_training_load": 42,
        },
    ]


@pytest.fixture
def sample_streams() -> list[dict]:
    return [
        {"type": "time", "name": "Time", "data": [0, 1, 2, 3, 4]},
        {"type": "watts", "name": "Power", "data": [200, 220, 210, 215, 205]},
        {"type": "heartrate", "name": "Heart Rate", "data": [140, 142, 143, 141, 140]},
    ]


@pytest.fixture
def sample_power_curve() -> dict:
    return {
        "secs": [1, 5, 10, 30, 60, 120, 300, 600, 1200],
        "watts": [850, 720, 620, 480, 380, 310, 260, 230, 210],
        "activity_id": "99001",
    }


@pytest.fixture
def sample_intervals() -> dict:
    return {
        "icu_intervals": [
            {
                "id": "1",
                "label": "1",
                "start_index": 0,
                "end_index": 500,
                "moving_time": 500,
                "average_watts": 200,
                "average_heartrate": 140,
            },
            {
                "id": "2",
                "label": "2",
                "start_index": 501,
                "end_index": 1200,
                "moving_time": 700,
                "average_watts": 250,
                "average_heartrate": 155,
            },
        ],
        "icu_groups": [],
    }
