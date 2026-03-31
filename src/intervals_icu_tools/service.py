"""Shared business logic for the Intervals.ICU API.

ALL business logic lives here. MCP tools and CLI commands are thin wrappers
that call these methods and format the output for their respective interfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import IntervalsClient
from .config import ApiConfig
from .models import Activity, ActivitySearchResult, FileDownloadResult


class IntervalsService:
    def __init__(self, config: ApiConfig) -> None:
        self._client = IntervalsClient(config)
        self._athlete_id = config.athlete_id

    # ------------------------------------------------------------------
    # Activity listing / searching / CRUD
    # ------------------------------------------------------------------

    async def list_activities(
        self,
        oldest: str,
        newest: str,
        athlete_id: str | None = None,
        limit: int = 50,
    ) -> list[Activity]:
        """List activities for a date range.

        Args:
            oldest: Start date ISO 8601 (e.g. "2024-01-01")
            newest: End date ISO 8601 (e.g. "2024-12-31")
            athlete_id: Override athlete ID (defaults to config)
            limit: Maximum number of activities to return
        """
        aid = athlete_id or self._athlete_id
        params: dict[str, Any] = {"oldest": oldest, "newest": newest}
        raw = await self._client.get(f"/api/v1/athlete/{aid}/activities", params=params)
        activities = [Activity.model_validate(r) for r in raw]
        return activities[:limit]

    async def get_activity(self, activity_id: str) -> Activity:
        """Get full details for a single activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}")
        return Activity.model_validate(raw)

    async def search_activities(
        self,
        query: str,
        full: bool = False,
        limit: int = 20,
    ) -> list[Activity] | list[ActivitySearchResult]:
        """Search activities by name or tag.

        Args:
            query: Free-text search query
            full: Return full activity details (True) or summary (False)
            limit: Maximum number of results
        """
        endpoint = "search-full" if full else "search"
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/activities/{endpoint}",
            params={"q": query},
        )
        results = raw[:limit]
        if full:
            return [Activity.model_validate(r) for r in results]
        return [ActivitySearchResult.model_validate(r) for r in results]

    async def update_activity(self, activity_id: str, **fields: Any) -> Activity:
        """Update editable fields on an activity. Pass only fields to change."""
        raw = await self._client.put(f"/api/v1/activity/{activity_id}", json=fields)
        return Activity.model_validate(raw)

    # ------------------------------------------------------------------
    # Activity sub-resources (structured data)
    # ------------------------------------------------------------------

    async def get_activity_intervals(self, activity_id: str) -> dict[str, Any]:
        """Get intervals (laps/splits) for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/intervals")
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_activity_streams(
        self,
        activity_id: str,
        types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get time-series data streams for an activity.

        Pass the path without extension to receive JSON.
        The {ext} path parameter is empty for JSON responses.
        """
        params: dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        raw = await self._client.get(
            f"/api/v1/activity/{activity_id}/streams",
            params=params,
        )
        return raw if isinstance(raw, list) else [raw]

    async def get_power_curve(self, activity_id: str) -> dict[str, Any]:
        """Get the mean-maximal power curve for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/power-curve")
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_power_curves(
        self,
        activity_id: str,
        types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get power curves for multiple stream types (watts, watts_kg, etc.)."""
        params: dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        raw = await self._client.get(
            f"/api/v1/activity/{activity_id}/power-curves",
            params=params,
        )
        return raw if isinstance(raw, list) else [raw]

    async def get_hr_curve(self, activity_id: str) -> dict[str, Any]:
        """Get the heart rate curve for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/hr-curve")
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_pace_curve(self, activity_id: str) -> dict[str, Any]:
        """Get the pace curve for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/pace-curve")
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_best_efforts(self, activity_id: str) -> dict[str, Any]:
        """Get best efforts (e.g. fastest 1km, 5km) found in an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/best-efforts")
        return raw if isinstance(raw, dict) else {"efforts": raw}

    async def get_activity_segments(self, activity_id: str) -> list[dict[str, Any]]:
        """Get matched segments for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/segments")
        return raw if isinstance(raw, list) else [raw]

    async def get_activity_map(self, activity_id: str) -> dict[str, Any]:
        """Get GPS map data (lat/lon track) for an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/map")
        return raw if isinstance(raw, dict) else {"data": raw}

    # ------------------------------------------------------------------
    # File downloads (streaming to disk)
    # ------------------------------------------------------------------

    async def download_activity_file(
        self,
        activity_id: str,
        file_type: str,
        output_dir: Path,
    ) -> FileDownloadResult:
        """Download an activity file (original, FIT, or GPX) to disk.

        Args:
            activity_id: The activity ID
            file_type: One of "original", "fit", "gpx"
            output_dir: Directory to save the file
        """
        endpoint_map = {
            "original": f"/api/v1/activity/{activity_id}/file",
            "fit": f"/api/v1/activity/{activity_id}/fit-file",
            "gpx": f"/api/v1/activity/{activity_id}/gpx-file",
        }
        if file_type not in endpoint_map:
            raise ValueError(
                f"file_type must be one of: {list(endpoint_map)}. Got: {file_type!r}"
            )
        return await self._client.download_file(
            endpoint_map[file_type], dest_dir=Path(output_dir)
        )

    async def download_activities_csv(
        self,
        oldest: str,
        newest: str,
        output_dir: Path,
    ) -> FileDownloadResult:
        """Download all activities in a date range as a CSV file."""
        return await self._client.download_file(
            f"/api/v1/athlete/{self._athlete_id}/activities.csv",
            dest_dir=Path(output_dir),
            params={"oldest": oldest, "newest": newest},
        )

    # ------------------------------------------------------------------
    # Athlete-level aggregate curves
    # ------------------------------------------------------------------

    async def get_athlete_power_curves(
        self,
        oldest: str,
        newest: str,
    ) -> dict[str, Any]:
        """Get best power curves across all activities in a date range."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/activity-power-curves",
            params={"oldest": oldest, "newest": newest},
        )
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_athlete_hr_curves(
        self,
        oldest: str,
        newest: str,
    ) -> dict[str, Any]:
        """Get best HR curves across all activities in a date range."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/activity-hr-curves",
            params={"oldest": oldest, "newest": newest},
        )
        return raw if isinstance(raw, dict) else {"data": raw}

    async def get_athlete_pace_curves(
        self,
        oldest: str,
        newest: str,
    ) -> dict[str, Any]:
        """Get best pace curves across all activities in a date range."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/activity-pace-curves",
            params={"oldest": oldest, "newest": newest},
        )
        return raw if isinstance(raw, dict) else {"data": raw}
