"""MCP server for intervals-icu-tools.

Thin FastMCP wrappers over the IntervalsService. All business logic lives in service.py.
Each tool catches exceptions and returns a structured error dict instead of raising,
so the LLM can reason about failures and recover gracefully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.resources import FileResource

from .config import load_config
from .errors import AuthenticationError, IntervalsError, NotFoundError, RateLimitError
from .service import IntervalsService

# Detect whether running from a source tree (editable/local install) or a PyPI/uvx install.
# pyproject.toml exists at the project root only in a source tree.
_project_root = Path(__file__).parent.parent.parent
_CLI_INVOCATION = (
    f"uv run --directory {_project_root} intervals-icu-tools"
    if (_project_root / "pyproject.toml").exists()
    else "uvx intervals-icu-tools"
)

mcp = FastMCP(
    "intervals-icu-tools",
    instructions=f"""This MCP server provides tools to query Intervals.ICU training data.

## CLI companion

For large data (streams from activities longer than ~1 hour, bulk CSV exports, binary
file downloads) the tools will tell you to use the CLI instead of returning the data
directly. Invoke the CLI with:

    {_CLI_INVOCATION} <command> [options]

Full CLI reference is available as an MCP resource — read it with:
    Resource URI: docs://cli-tools

## Key patterns
- Use `list_activities` / `get_activity` for structured training data in context.
- Use `get_activity_streams` for short activities; fall back to the CLI for long ones.
- Use `get_power_curve` / `get_hr_curve` for performance analysis.
- Use `get_athlete_power_curves` to compare fitness across a training block.
- Use `list_wellness` / `update_wellness` for daily biometric and subjective load tracking.
- Use `list_events` / `create_event` to read and plan the training calendar.
- Use `list_workouts` / `create_workout` to manage the workout library.
- Always pass dates as ISO 8601 strings: "YYYY-MM-DD".
- For tools that accept a `fields` parameter, pass a JSON string, e.g. '{{"weight": 70.5}}'.
""",
)

# Expose the CLI reference documentation as an MCP resource so the LLM can read it
# through the same MCP connection — no separate configuration needed.
mcp.add_resource(
    FileResource(
        uri="docs://cli-tools",
        path=Path(__file__).parent / "cli_tools.md",
        name="CLI Tool Reference",
        description="Full reference for the intervals-icu-tools CLI: commands, options, exit codes, and usage patterns.",
        mime_type="text/markdown",
    )
)


def _make_service() -> IntervalsService:
    return IntervalsService(load_config())


def _strip_nulls(obj: Any) -> Any:
    """Recursively remove keys with None values from dicts (and nested structures)."""
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_nulls(item) for item in obj]
    return obj


def _err(e: Exception) -> dict:
    """Map exceptions to structured error dicts the LLM can act on."""
    if isinstance(e, AuthenticationError):
        return {
            "error": f"Authentication failed. Ensure INTERVALS_API_KEY is set correctly. Details: {e}"
        }
    if isinstance(e, RateLimitError):
        return {"error": f"Rate limit exceeded. Retry after {e.retry_after} seconds."}
    if isinstance(e, NotFoundError):
        return {"error": f"Resource not found: {e}"}
    if isinstance(e, IntervalsError):
        return {"error": f"API error: {e}"}
    return {"error": f"Unexpected error: {type(e).__name__}: {e}"}


# ------------------------------------------------------------------
# Activity listing / searching / CRUD
# ------------------------------------------------------------------


@mcp.tool
async def list_activities(oldest: str, newest: str, limit: int = 50) -> list[dict] | dict:
    """List activities for a date range.

    Args:
        oldest: Start date in ISO 8601 format (e.g. "2024-01-01")
        newest: End date in ISO 8601 format (e.g. "2024-12-31")
        limit: Maximum number of activities to return (default: 50)

    Returns:
        List of activity dicts containing id, name, type, start_date_local,
        distance, moving_time, icu_training_load, icu_ftp, and all other activity fields.

    For a bulk CSV export of all activities, use the CLI instead:
        intervals-icu-tools -o ./data download-activities-csv --oldest 2024-01-01 --newest 2024-12-31
    """
    try:
        svc = _make_service()
        activities = await svc.list_activities(oldest, newest, limit=limit)
        return [a.model_dump(exclude_none=True) for a in activities]
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_activity(activity_id: str) -> dict:
    """Get complete details for a single activity by its ID.

    Args:
        activity_id: The activity ID (e.g. "12345678")

    Returns:
        Full activity dict with all available fields including training load,
        power metrics (icu_weighted_avg_watts, icu_ftp), HR zones, and more.
    """
    try:
        svc = _make_service()
        activity = await svc.get_activity(activity_id)
        return activity.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def search_activities(query: str, full: bool = False, limit: int = 20) -> list[dict] | dict:
    """Search activities by name or tag.

    Args:
        query: Search query (activity name, tag, or description text)
        full: If True, return full activity details; if False (default), return summary fields
        limit: Maximum number of results to return (default: 20)

    Returns:
        List of activity dicts. Summary includes id, name, type, start_date_local,
        distance, moving_time. Full includes all activity fields.
    """
    try:
        svc = _make_service()
        results = await svc.search_activities(query, full=full, limit=limit)
        return [r.model_dump(exclude_none=True) for r in results]
    except Exception as e:
        return _err(e)


@mcp.tool
async def update_activity(
    activity_id: str,
    name: str | None = None,
    description: str | None = None,
    type: str | None = None,
    perceived_exertion: float | None = None,
) -> dict:
    """Update editable fields on an activity. Only provided fields are changed.

    Args:
        activity_id: The activity ID to update
        name: New activity name (optional)
        description: New description or notes (optional)
        type: Activity type override, e.g. "Run", "Ride", "Swim" (optional)
        perceived_exertion: RPE on a 1–10 scale (optional)

    Returns:
        Updated activity dict with all fields.
    """
    try:
        svc = _make_service()
        fields = {
            k: v
            for k, v in {
                "name": name,
                "description": description,
                "type": type,
                "perceived_exertion": perceived_exertion,
            }.items()
            if v is not None
        }
        activity = await svc.update_activity(activity_id, **fields)
        return activity.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Activity sub-resources
# ------------------------------------------------------------------


@mcp.tool
async def get_activity_intervals(activity_id: str) -> dict:
    """Get structured interval data (laps/splits) for an activity.

    Args:
        activity_id: The activity ID

    Returns:
        Dict with 'icu_intervals' (list of interval objects with avg/max power, HR,
        cadence, duration, distance) and 'icu_groups' (interval groupings).
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_activity_intervals(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_activity_streams(activity_id: str, types: str | None = None) -> list[dict] | dict:
    """Get time-series data streams for an activity (second-by-second data).

    Args:
        activity_id: The activity ID
        types: Comma-separated stream types to fetch. If omitted, returns all available streams.
               Common types: time, watts, heartrate, cadence, distance, altitude,
               lat, lon, speed, temperature, smo2, thb

    Returns:
        List of stream dicts, each with 'type', 'name', and 'data' (array of values).

    WARNING: For activities longer than 1 hour, streams can exceed 50KB.
    To save streams to disk for large activities, use the CLI:
        intervals-icu-tools -o ./data get-streams <activity_id> --types watts,heartrate
    """
    try:
        svc = _make_service()
        type_list = [t.strip() for t in types.split(",")] if types else None
        return _strip_nulls(await svc.get_activity_streams(activity_id, types=type_list))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_power_curve(activity_id: str) -> dict:
    """Get the mean-maximal power (MMP) curve for an activity.

    Args:
        activity_id: The activity ID

    Returns:
        Dict with duration buckets (secs) and corresponding peak power values (watts).
        Useful for identifying best efforts at specific durations (e.g. 1min, 5min, 20min, FTP).
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_power_curve(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_hr_curve(activity_id: str) -> dict:
    """Get the heart rate curve for an activity.

    Args:
        activity_id: The activity ID

    Returns:
        Dict with duration buckets and corresponding peak HR values (bpm).
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_hr_curve(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_pace_curve(activity_id: str) -> dict:
    """Get the pace curve for an activity (running/swimming).

    Args:
        activity_id: The activity ID

    Returns:
        Dict with distance buckets and corresponding best pace values (m/s).
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_pace_curve(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_best_efforts(activity_id: str) -> dict:
    """Get best efforts found within an activity (e.g. fastest 1km, 5km, 1-mile).

    Args:
        activity_id: The activity ID

    Returns:
        Dict with 'efforts' list. Each effort has distance/duration, elapsed time,
        average power/HR/pace, and a reference to the segment in the activity.
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_best_efforts(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_activity_segments(activity_id: str) -> list[dict] | dict:
    """Get matched Strava/Intervals segments for an activity.

    Args:
        activity_id: The activity ID

    Returns:
        List of segment dicts with name, distance, elapsed time, rank, and PR status.
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_activity_segments(activity_id))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_activity_map(activity_id: str) -> dict:
    """Get GPS track (lat/lon) and map metadata for an activity.

    Args:
        activity_id: The activity ID

    Returns:
        Dict with 'latlngs' (list of [lat, lon] pairs), 'bounds', and 'route' arrays.
        For large activities the lat/lon array may be downsampled for context efficiency.
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_activity_map(activity_id))
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Athlete-level aggregate curves
# ------------------------------------------------------------------


@mcp.tool
async def get_athlete_power_curves(oldest: str, newest: str) -> dict:
    """Get the best (peak) power curves across all activities in a date range.

    Useful for tracking fitness progression: compare best 5-min power this month
    vs last month, or identify where the athlete is on the power duration curve.

    Args:
        oldest: Start date ISO 8601 (e.g. "2024-01-01")
        newest: End date ISO 8601 (e.g. "2024-12-31")

    Returns:
        Dict with power curve data aggregated across all activities in the date range.
        Includes 'list' of per-duration best values and 'activities' linking to source activities.
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_athlete_power_curves(oldest, newest))
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_athlete_hr_curves(oldest: str, newest: str) -> dict:
    """Get the best heart rate curves across all activities in a date range.

    Args:
        oldest: Start date ISO 8601 (e.g. "2024-01-01")
        newest: End date ISO 8601 (e.g. "2024-12-31")

    Returns:
        Dict with HR curve data aggregated across all activities in the date range.
    """
    try:
        svc = _make_service()
        return _strip_nulls(await svc.get_athlete_hr_curves(oldest, newest))
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Athlete profile
# ------------------------------------------------------------------


@mcp.tool
async def get_athlete() -> dict:
    """Get the athlete's profile, including sport settings and thresholds.

    Returns:
        Dict with athlete fields: id, name, weight, icu_ftp, icu_resting_hr,
        timezone, measurement_preference, and all other profile fields.
    """
    try:
        svc = _make_service()
        athlete = await svc.get_athlete()
        return athlete.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def update_athlete(fields: str) -> dict:
    """Update athlete profile fields. Only provided fields are changed.

    Args:
        fields: JSON object of fields to update. Common fields:
            name (str), weight (float, kg), sex ("M"/"F"),
            measurement_preference ("metric"/"imperial"),
            fahrenheit (bool), timezone (e.g. "Europe/London").
            Example: '{"weight": 70.5, "timezone": "Europe/Berlin"}'

    Returns:
        Updated athlete dict with all profile fields.
    """
    import json as _json
    try:
        svc = _make_service()
        athlete = await svc.update_athlete(**_json.loads(fields))
        return athlete.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Wellness
# ------------------------------------------------------------------


@mcp.tool
async def list_wellness(oldest: str, newest: str) -> list[dict] | dict:
    """List wellness records for a date range.

    Args:
        oldest: Start date ISO 8601 (e.g. "2024-01-01")
        newest: End date ISO 8601 (e.g. "2024-12-31")

    Returns:
        List of wellness dicts. Each has date (id), ctl, atl, weight, restingHR,
        hrv, sleepSecs, sleepScore, fatigue, stress, mood, motivation, and more.
    """
    try:
        svc = _make_service()
        records = await svc.list_wellness(oldest, newest)
        return [r.model_dump(exclude_none=True) for r in records]
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_wellness(date: str) -> dict:
    """Get the wellness record for a specific date.

    Args:
        date: ISO 8601 date string (e.g. "2024-01-15")

    Returns:
        Wellness dict with all tracked metrics for that day.
    """
    try:
        svc = _make_service()
        record = await svc.get_wellness(date)
        return record.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def update_wellness(date: str, fields: str) -> dict:
    """Update (or create) the wellness record for a specific date.

    Args:
        date: ISO 8601 date string (e.g. "2024-01-15")
        fields: JSON object of wellness metrics to set. Common fields:
            weight (float, kg), restingHR (int, bpm), hrv (float, ms),
            sleepSecs (int, seconds), sleepScore (float, 0-100),
            sleepQuality (int, 1-5), fatigue (int, 1-7), stress (int, 1-7),
            mood (int, 1-7), motivation (int, 1-7), soreness (int, 1-7).
            Example: '{"weight": 70.2, "sleepSecs": 28800, "fatigue": 3}'

    Returns:
        Updated wellness dict for that date.
    """
    import json as _json
    try:
        svc = _make_service()
        record = await svc.update_wellness(date, **_json.loads(fields))
        return record.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Events / Calendar
# ------------------------------------------------------------------


@mcp.tool
async def list_events(
    oldest: str,
    newest: str,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict] | dict:
    """List calendar events (planned workouts, races, notes) for a date range.

    Args:
        oldest: Start date ISO 8601 (e.g. "2024-01-01")
        newest: End date ISO 8601 (e.g. "2024-12-31")
        category: Comma-separated categories to filter. Options: WORKOUT, RACE_A,
                  RACE_B, RACE_C, NOTE. Default: all categories.
        limit: Maximum number of events to return.

    Returns:
        List of event dicts with id, name, category, start_date_local, type,
        moving_time, icu_training_load, description, and more.
    """
    try:
        svc = _make_service()
        events = await svc.list_events(oldest, newest, category=category, limit=limit)
        return [e.model_dump(exclude_none=True) for e in events]
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_event(event_id: int) -> dict:
    """Get a single calendar event by its ID.

    Args:
        event_id: The event ID (integer)

    Returns:
        Full event dict with all fields.
    """
    try:
        svc = _make_service()
        event = await svc.get_event(event_id)
        return event.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def create_event(fields: str) -> dict:
    """Create a calendar event (planned workout, note, race, etc.).

    Args:
        fields: JSON object of event fields. Common fields:
            name (str), category (WORKOUT/NOTE/RACE_A/RACE_B/RACE_C),
            start_date_local (ISO 8601, e.g. "2024-03-15T09:00:00"),
            type (Run/Ride/Swim/etc.), description (str),
            moving_time (int, seconds), indoor (bool).
            Example: '{"name": "Long Run", "category": "WORKOUT",
                       "start_date_local": "2024-03-15T09:00:00",
                       "type": "Run", "moving_time": 5400}'

    Returns:
        Created event dict with all fields including the assigned id.
    """
    import json as _json
    try:
        svc = _make_service()
        event = await svc.create_event(**_json.loads(fields))
        return event.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def update_event(event_id: int, fields: str) -> dict:
    """Update a calendar event. Only provided fields are changed.

    Args:
        event_id: The event ID to update
        fields: JSON object of fields to update. Common fields:
            name, description, start_date_local, category, type,
            moving_time (seconds), indoor (bool), color (hex string).
            Example: '{"name": "Recovery Ride", "moving_time": 3600}'

    Returns:
        Updated event dict with all fields.
    """
    import json as _json
    try:
        svc = _make_service()
        event = await svc.update_event(event_id, **_json.loads(fields))
        return event.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def delete_event(event_id: int) -> dict:
    """Delete a calendar event.

    Args:
        event_id: The event ID to delete

    Returns:
        Empty dict on success, or error dict on failure.
    """
    try:
        svc = _make_service()
        return await svc.delete_event(event_id)
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Workouts library
# ------------------------------------------------------------------


@mcp.tool
async def list_workouts() -> list[dict] | dict:
    """List all workouts in the athlete's workout library.

    Returns:
        List of workout dicts with id, name, type, moving_time,
        icu_training_load, folder_id, tags, and more.
    """
    try:
        svc = _make_service()
        workouts = await svc.list_workouts()
        return [w.model_dump(exclude_none=True) for w in workouts]
    except Exception as e:
        return _err(e)


@mcp.tool
async def get_workout(workout_id: int) -> dict:
    """Get a single workout from the library by its ID.

    Args:
        workout_id: The workout ID (integer)

    Returns:
        Full workout dict including workout_doc (structured workout steps).
    """
    try:
        svc = _make_service()
        workout = await svc.get_workout(workout_id)
        return workout.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def create_workout(fields: str) -> dict:
    """Create a new workout in the athlete's library.

    Args:
        fields: JSON object of workout fields. Common fields:
            name (str, required), type (Run/Ride/Swim/etc.),
            description (str), moving_time (int, seconds), indoor (bool),
            folder_id (int), tags (list of strings),
            workout_doc (structured steps object).
            Example: '{"name": "Tempo Run", "type": "Run", "moving_time": 3600}'

    Returns:
        Created workout dict with assigned id and all fields.
    """
    import json as _json
    try:
        svc = _make_service()
        workout = await svc.create_workout(**_json.loads(fields))
        return workout.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def update_workout(workout_id: int, fields: str) -> dict:
    """Update a workout in the library. Only provided fields are changed.

    Args:
        workout_id: The workout ID to update
        fields: JSON object of fields to update (name, description, type,
                moving_time, indoor, tags, workout_doc, etc.).
                Example: '{"name": "Updated Tempo Run", "moving_time": 4500}'

    Returns:
        Updated workout dict with all fields.
    """
    import json as _json
    try:
        svc = _make_service()
        workout = await svc.update_workout(workout_id, **_json.loads(fields))
        return workout.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


@mcp.tool
async def delete_workout(workout_id: int) -> dict:
    """Delete a workout from the library.

    Args:
        workout_id: The workout ID to delete

    Returns:
        Empty dict on success, or error dict on failure.
    """
    try:
        svc = _make_service()
        return await svc.delete_workout(workout_id)
    except Exception as e:
        return _err(e)


# ------------------------------------------------------------------
# Activity messages (comments)
# ------------------------------------------------------------------


@mcp.tool
async def list_activity_messages(activity_id: str) -> list[dict] | dict:
    """List all comments on an activity.

    Args:
        activity_id: The activity ID

    Returns:
        List of message dicts with id, content, athlete_id, athlete_name, updated.
    """
    try:
        svc = _make_service()
        messages = await svc.list_activity_messages(activity_id)
        return [m.model_dump(exclude_none=True) for m in messages]
    except Exception as e:
        return _err(e)


@mcp.tool
async def create_activity_message(activity_id: str, content: str) -> dict:
    """Post a comment on an activity.

    Args:
        activity_id: The activity ID to comment on
        content: The message text

    Returns:
        Created message dict with id, content, athlete_id, athlete_name, updated.
    """
    try:
        svc = _make_service()
        message = await svc.create_activity_message(activity_id, content)
        return message.model_dump(exclude_none=True)
    except Exception as e:
        return _err(e)


def main() -> None:
    """Entry point for the MCP server (intervals-icu-mcp)."""
    mcp.run()
