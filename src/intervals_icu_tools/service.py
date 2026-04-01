"""Shared business logic for the Intervals.ICU API.

ALL business logic lives here. MCP tools and CLI commands are thin wrappers
that call these methods and format the output for their respective interfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import IntervalsClient
from .config import ApiConfig
from .exporters import write_csv
from .models import (
    Activity,
    ActivityMessage,
    ActivitySearchResult,
    Athlete,
    Event,
    FileDownloadResult,
    WellnessRecord,
    Workout,
)


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
        """Download activities for a date range as a CSV file.

        Uses the JSON activities endpoint (which supports date filtering) and
        writes the result to CSV locally. The /activities.csv API endpoint does
        not accept date range parameters and would return all activities.
        """
        output_dir = Path(output_dir)
        activities = await self.list_activities(oldest, newest, limit=10000)
        rows = [a.model_dump(exclude_none=True) for a in activities]
        path = output_dir / f"{self._athlete_id}_activities.csv"
        write_csv(rows, path)
        size = path.stat().st_size
        return FileDownloadResult(
            path=path,
            size_bytes=size,
            content_type="text/csv",
            filename=path.name,
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

    # ------------------------------------------------------------------
    # Athlete profile
    # ------------------------------------------------------------------

    async def get_athlete(self) -> Athlete:
        """Get the athlete's profile (includes sport settings and custom items)."""
        raw = await self._client.get(f"/api/v1/athlete/{self._athlete_id}")
        return Athlete.model_validate(raw)

    async def update_athlete(self, **fields: Any) -> Athlete:
        """Update athlete profile fields. Pass only fields to change."""
        raw = await self._client.put(f"/api/v1/athlete/{self._athlete_id}", json=fields)
        return Athlete.model_validate(raw)

    # ------------------------------------------------------------------
    # Wellness
    # ------------------------------------------------------------------

    async def list_wellness(
        self,
        oldest: str,
        newest: str,
    ) -> list[WellnessRecord]:
        """List wellness records for a date range."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/wellness",
            params={"oldest": oldest, "newest": newest},
        )
        records = raw if isinstance(raw, list) else [raw]
        return [WellnessRecord.model_validate(r) for r in records]

    async def get_wellness(self, date: str) -> WellnessRecord:
        """Get wellness record for a specific date (ISO-8601, e.g. '2024-01-15')."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/wellness/{date}"
        )
        return WellnessRecord.model_validate(raw)

    async def update_wellness(self, date: str, **fields: Any) -> WellnessRecord:
        """Update (or create) the wellness record for a specific date."""
        raw = await self._client.put(
            f"/api/v1/athlete/{self._athlete_id}/wellness/{date}", json=fields
        )
        return WellnessRecord.model_validate(raw)

    # ------------------------------------------------------------------
    # Events / Calendar
    # ------------------------------------------------------------------

    async def list_events(
        self,
        oldest: str,
        newest: str,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """List calendar events (planned workouts, races, notes) for a date range.

        Args:
            oldest: Start date ISO 8601 (e.g. "2024-01-01")
            newest: End date ISO 8601 (e.g. "2024-12-31")
            category: Comma-separated categories to filter (WORKOUT, RACE_A, RACE_B, RACE_C, NOTE)
            limit: Maximum number of events to return
        """
        params: dict[str, Any] = {"oldest": oldest, "newest": newest}
        if category:
            params["category"] = category
        if limit is not None:
            params["limit"] = limit
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/events",
            params=params,
        )
        records = raw if isinstance(raw, list) else [raw]
        return [Event.model_validate(r) for r in records]

    async def get_event(self, event_id: int) -> Event:
        """Get a single calendar event by ID."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/events/{event_id}"
        )
        return Event.model_validate(raw)

    async def create_event(self, **fields: Any) -> Event:
        """Create a calendar event (planned workout, note, race, etc.)."""
        raw = await self._client.post(
            f"/api/v1/athlete/{self._athlete_id}/events", json=fields
        )
        return Event.model_validate(raw)

    async def update_event(self, event_id: int, **fields: Any) -> Event:
        """Update a calendar event. Pass only fields to change."""
        raw = await self._client.put(
            f"/api/v1/athlete/{self._athlete_id}/events/{event_id}", json=fields
        )
        return Event.model_validate(raw)

    async def delete_event(self, event_id: int) -> dict[str, Any]:
        """Delete a calendar event."""
        return await self._client.delete(
            f"/api/v1/athlete/{self._athlete_id}/events/{event_id}"
        )

    # ------------------------------------------------------------------
    # Workouts library
    # ------------------------------------------------------------------

    async def list_workouts(self) -> list[Workout]:
        """List all workouts in the athlete's library."""
        raw = await self._client.get(f"/api/v1/athlete/{self._athlete_id}/workouts")
        records = raw if isinstance(raw, list) else [raw]
        return [Workout.model_validate(r) for r in records]

    async def get_workout(self, workout_id: int) -> Workout:
        """Get a single workout from the library."""
        raw = await self._client.get(
            f"/api/v1/athlete/{self._athlete_id}/workouts/{workout_id}"
        )
        return Workout.model_validate(raw)

    async def create_workout(self, **fields: Any) -> Workout:
        """Create a new workout in the athlete's library."""
        raw = await self._client.post(
            f"/api/v1/athlete/{self._athlete_id}/workouts", json=fields
        )
        return Workout.model_validate(raw)

    async def update_workout(self, workout_id: int, **fields: Any) -> Workout:
        """Update a workout in the library. Pass only fields to change."""
        raw = await self._client.put(
            f"/api/v1/athlete/{self._athlete_id}/workouts/{workout_id}", json=fields
        )
        return Workout.model_validate(raw)

    async def delete_workout(self, workout_id: int) -> dict[str, Any]:
        """Delete a workout from the library."""
        return await self._client.delete(
            f"/api/v1/athlete/{self._athlete_id}/workouts/{workout_id}"
        )

    # ------------------------------------------------------------------
    # Activity messages (comments)
    # ------------------------------------------------------------------

    async def list_activity_messages(self, activity_id: str) -> list[ActivityMessage]:
        """List all comments on an activity."""
        raw = await self._client.get(f"/api/v1/activity/{activity_id}/messages")
        records = raw if isinstance(raw, list) else [raw]
        return [ActivityMessage.model_validate(r) for r in records]

    async def create_activity_message(
        self, activity_id: str, content: str
    ) -> ActivityMessage:
        """Post a comment on an activity."""
        raw = await self._client.post(
            f"/api/v1/activity/{activity_id}/messages", json={"content": content}
        )
        return ActivityMessage.model_validate(raw)
