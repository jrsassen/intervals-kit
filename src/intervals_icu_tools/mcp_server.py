"""MCP server for intervals-icu-tools.

Thin FastMCP wrappers over the IntervalsService. All business logic lives in service.py.
Each tool catches exceptions and returns a structured error dict instead of raising,
so the LLM can reason about failures and recover gracefully.
"""

from __future__ import annotations

from fastmcp import FastMCP

from .config import load_config
from .errors import AuthenticationError, IntervalsError, NotFoundError, RateLimitError
from .service import IntervalsService

mcp = FastMCP("intervals-icu-tools")


def _make_service() -> IntervalsService:
    return IntervalsService(load_config())


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
        intervals-icu-tools download-activities-csv --oldest 2024-01-01 --newest 2024-12-31 -o ./data
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
        return await svc.get_activity_intervals(activity_id)
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
        intervals-icu-tools get-streams <activity_id> --types watts,heartrate -o ./data
    """
    try:
        svc = _make_service()
        type_list = [t.strip() for t in types.split(",")] if types else None
        return await svc.get_activity_streams(activity_id, types=type_list)
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
        return await svc.get_power_curve(activity_id)
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
        return await svc.get_hr_curve(activity_id)
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
        return await svc.get_pace_curve(activity_id)
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
        return await svc.get_best_efforts(activity_id)
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
        return await svc.get_activity_segments(activity_id)
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
        return await svc.get_activity_map(activity_id)
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
        return await svc.get_athlete_power_curves(oldest, newest)
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
        return await svc.get_athlete_hr_curves(oldest, newest)
    except Exception as e:
        return _err(e)


def main() -> None:
    """Entry point for the MCP server (intervals-icu-mcp)."""
    mcp.run()
