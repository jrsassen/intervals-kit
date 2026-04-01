"""Tests for the service layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from intervals_icu_tools.config import ApiConfig
from intervals_icu_tools.models import Activity, ActivitySearchResult, FileDownloadResult
from intervals_icu_tools.service import IntervalsService


@pytest.fixture
def config() -> ApiConfig:
    return ApiConfig(api_key="test-key", athlete_id="itest")


@pytest.fixture
def svc(config: ApiConfig) -> IntervalsService:
    return IntervalsService(config)


class TestListActivities:
    async def test_returns_activity_list(
        self, svc: IntervalsService, sample_activities: list[dict]
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activities)):
            result = await svc.list_activities("2024-01-01", "2024-12-31")
        assert len(result) == 2
        assert all(isinstance(a, Activity) for a in result)
        assert result[0].id == "99001"
        assert result[1].type == "Run"

    async def test_respects_limit(
        self, svc: IntervalsService, sample_activities: list[dict]
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activities)):
            result = await svc.list_activities("2024-01-01", "2024-12-31", limit=1)
        assert len(result) == 1

    async def test_uses_correct_endpoint(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.list_activities("2024-01-01", "2024-12-31")
        called_path = mock.call_args[0][0]
        assert "/api/v1/athlete/itest/activities" in called_path


class TestGetActivity:
    async def test_returns_activity(
        self, svc: IntervalsService, sample_activity: dict
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activity)):
            result = await svc.get_activity("99001")
        assert isinstance(result, Activity)
        assert result.id == "99001"
        assert result.name == "Morning Ride"

    async def test_uses_correct_endpoint(self, svc: IntervalsService, sample_activity: dict) -> None:
        mock = AsyncMock(return_value=sample_activity)
        with patch.object(svc._client, "get", new=mock):
            await svc.get_activity("99001")
        assert mock.call_args[0][0] == "/api/v1/activity/99001"


class TestSearchActivities:
    async def test_summary_returns_search_results(
        self, svc: IntervalsService, sample_activities: list[dict]
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activities)):
            result = await svc.search_activities("ride", full=False)
        assert all(isinstance(r, ActivitySearchResult) for r in result)

    async def test_full_returns_activities(
        self, svc: IntervalsService, sample_activities: list[dict]
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activities)):
            result = await svc.search_activities("ride", full=True)
        assert all(isinstance(r, Activity) for r in result)

    async def test_full_uses_search_full_endpoint(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.search_activities("ride", full=True)
        assert "search-full" in mock.call_args[0][0]

    async def test_summary_uses_search_endpoint(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.search_activities("ride", full=False)
        path = mock.call_args[0][0]
        assert path.endswith("/activities/search")

    async def test_uses_q_param(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.search_activities("ride")
        params = mock.call_args[1]["params"]
        assert params.get("q") == "ride"
        assert "query" not in params


class TestUpdateActivity:
    async def test_passes_only_provided_fields(
        self, svc: IntervalsService, sample_activity: dict
    ) -> None:
        mock = AsyncMock(return_value=sample_activity)
        with patch.object(svc._client, "put", new=mock):
            await svc.update_activity("99001", name="New Name")
        assert mock.call_args[1]["json"] == {"name": "New Name"}

    async def test_returns_activity(
        self, svc: IntervalsService, sample_activity: dict
    ) -> None:
        with patch.object(svc._client, "put", new=AsyncMock(return_value=sample_activity)):
            result = await svc.update_activity("99001", name="New Name")
        assert isinstance(result, Activity)


class TestGetStreams:
    async def test_returns_list(
        self, svc: IntervalsService, sample_streams: list[dict]
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_streams)):
            result = await svc.get_activity_streams("99001")
        assert isinstance(result, list)
        assert len(result) == 3

    async def test_passes_types_param(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.get_activity_streams("99001", types=["watts", "heartrate"])
        params = mock.call_args[1]["params"]
        assert params["types"] == "watts,heartrate"

    async def test_uses_no_extension_for_json(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value=[])
        with patch.object(svc._client, "get", new=mock):
            await svc.get_activity_streams("99001")
        path = mock.call_args[0][0]
        assert path == "/api/v1/activity/99001/streams"
        assert ".csv" not in path


class TestDownloadActivityFile:
    async def test_original_uses_correct_endpoint(self, svc: IntervalsService, tmp_path: Path) -> None:
        mock_result = FileDownloadResult(
            path=tmp_path / "activity.fit",
            size_bytes=1024,
            content_type="application/octet-stream",
            filename="activity.fit",
        )
        mock = AsyncMock(return_value=mock_result)
        with patch.object(svc._client, "download_file", new=mock):
            await svc.download_activity_file("99001", "original", tmp_path)
        assert mock.call_args[0][0] == "/api/v1/activity/99001/file"

    async def test_fit_uses_correct_endpoint(self, svc: IntervalsService, tmp_path: Path) -> None:
        mock_result = FileDownloadResult(
            path=tmp_path / "activity.fit",
            size_bytes=1024,
            content_type="application/octet-stream",
            filename="activity.fit",
        )
        mock = AsyncMock(return_value=mock_result)
        with patch.object(svc._client, "download_file", new=mock):
            await svc.download_activity_file("99001", "fit", tmp_path)
        assert mock.call_args[0][0] == "/api/v1/activity/99001/fit-file"

    async def test_invalid_type_raises_value_error(
        self, svc: IntervalsService, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="file_type must be one of"):
            await svc.download_activity_file("99001", "invalid", tmp_path)


class TestAthleteCurves:
    async def test_power_curves_passes_date_params(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value={"data": []})
        with patch.object(svc._client, "get", new=mock):
            await svc.get_athlete_power_curves("2024-01-01", "2024-12-31")
        params = mock.call_args[1]["params"]
        assert params["oldest"] == "2024-01-01"
        assert params["newest"] == "2024-12-31"

    async def test_power_curves_uses_correct_endpoint(self, svc: IntervalsService) -> None:
        mock = AsyncMock(return_value={})
        with patch.object(svc._client, "get", new=mock):
            await svc.get_athlete_power_curves("2024-01-01", "2024-12-31")
        assert "activity-power-curves" in mock.call_args[0][0]


class TestDownloadActivitiesCsv:
    async def test_uses_json_endpoint_not_csv_endpoint(
        self, svc: IntervalsService, sample_activities: list[dict], tmp_path: Path
    ) -> None:
        """Must use /activities (supports date filtering), NOT /activities.csv (no params)."""
        mock = AsyncMock(return_value=sample_activities)
        with patch.object(svc._client, "get", new=mock):
            await svc.download_activities_csv("2024-01-01", "2024-12-31", tmp_path)
        called_path = mock.call_args[0][0]
        assert called_path.endswith("/activities")
        assert ".csv" not in called_path

    async def test_passes_date_params(
        self, svc: IntervalsService, sample_activities: list[dict], tmp_path: Path
    ) -> None:
        mock = AsyncMock(return_value=sample_activities)
        with patch.object(svc._client, "get", new=mock):
            await svc.download_activities_csv("2024-01-01", "2024-12-31", tmp_path)
        params = mock.call_args[1]["params"]
        assert params["oldest"] == "2024-01-01"
        assert params["newest"] == "2024-12-31"

    async def test_writes_csv_file(
        self, svc: IntervalsService, sample_activities: list[dict], tmp_path: Path
    ) -> None:
        with patch.object(svc._client, "get", new=AsyncMock(return_value=sample_activities)):
            result = await svc.download_activities_csv("2024-01-01", "2024-12-31", tmp_path)
        assert result.path.exists()
        assert result.path.suffix == ".csv"
        content = result.path.read_text()
        assert "Morning Ride" in content
        assert "Easy Run" in content
        # Header row must be present
        first_line = content.splitlines()[0]
        assert "id" in first_line
        assert "name" in first_line
