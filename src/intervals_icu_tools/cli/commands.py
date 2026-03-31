"""CLI commands for intervals-icu-tools.

Each command is a thin wrapper over IntervalsService. Exit codes:
  0 = success
  1 = auth error / general error
  2 = rate limit (retryable)
  3 = download / network error (retryable)
  4 = not found
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from ..errors import AuthenticationError, DownloadError, IntervalsError, NotFoundError, RateLimitError
from ..exporters import to_json_str, write_json
from ..service import IntervalsService
from .main import cli


def _exit(msg: str, code: int) -> None:
    click.echo(f"Error: {msg}", err=True)
    sys.exit(code)


def _handle(e: Exception) -> None:
    if isinstance(e, AuthenticationError):
        _exit(str(e), 1)
    if isinstance(e, RateLimitError):
        _exit(f"Rate limited. Retry after {e.retry_after}s.", 2)
    if isinstance(e, DownloadError):
        _exit(str(e), 3)
    if isinstance(e, NotFoundError):
        _exit(str(e), 4)
    if isinstance(e, IntervalsError):
        _exit(str(e), 1)
    _exit(str(e), 1)


def _output(data: object, ctx: click.Context, filename: str) -> None:
    """Print JSON to stdout or save to file depending on --output-dir."""
    output_dir = ctx.obj.get("output_dir", ".")
    if output_dir != ".":
        path = Path(output_dir) / filename
        write_json(data, path)
        click.echo(f"Saved to {path}")
    else:
        click.echo(to_json_str(data))


# ------------------------------------------------------------------
# Activity listing / searching / CRUD
# ------------------------------------------------------------------


@cli.command("list-activities")
@click.option("--oldest", required=True, help="Start date (ISO 8601, e.g. 2024-01-01)")
@click.option("--newest", required=True, help="End date (ISO 8601, e.g. 2024-12-31)")
@click.option("--limit", "-l", default=50, show_default=True, help="Max activities to return")
@click.pass_context
def list_activities(ctx: click.Context, oldest: str, newest: str, limit: int) -> None:
    """List activities for a date range."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        activities = asyncio.run(svc.list_activities(oldest, newest, limit=limit))
        data = [a.model_dump(exclude_none=True) for a in activities]
        _output(data, ctx, f"activities_{oldest}_{newest}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-activity")
@click.argument("activity_id")
@click.pass_context
def get_activity(ctx: click.Context, activity_id: str) -> None:
    """Get full details for a single activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        activity = asyncio.run(svc.get_activity(activity_id))
        click.echo(to_json_str(activity.model_dump(exclude_none=True)))
    except Exception as e:
        _handle(e)


@cli.command("search-activities")
@click.argument("query")
@click.option("--full", is_flag=True, default=False, help="Return full activity details")
@click.option("--limit", "-l", default=20, show_default=True, help="Max results")
@click.pass_context
def search_activities(ctx: click.Context, query: str, full: bool, limit: int) -> None:
    """Search activities by name or tag."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        results = asyncio.run(svc.search_activities(query, full=full, limit=limit))
        data = [r.model_dump(exclude_none=True) for r in results]
        _output(data, ctx, f"search_{query.replace(' ', '_')}.json")
    except Exception as e:
        _handle(e)


@cli.command("update-activity")
@click.argument("activity_id")
@click.option("--name", default=None, help="New activity name")
@click.option("--description", default=None, help="New description")
@click.option("--type", "activity_type", default=None, help="Activity type (e.g. Run, Ride)")
@click.option("--perceived-exertion", type=float, default=None, help="RPE 1–10")
@click.pass_context
def update_activity(
    ctx: click.Context,
    activity_id: str,
    name: str | None,
    description: str | None,
    activity_type: str | None,
    perceived_exertion: float | None,
) -> None:
    """Update editable fields on an activity."""
    fields = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "type": activity_type,
            "perceived_exertion": perceived_exertion,
        }.items()
        if v is not None
    }
    if not fields:
        click.echo("No fields to update. Use --name, --description, --type, or --perceived-exertion.", err=True)
        sys.exit(1)
    svc = IntervalsService(ctx.obj["config"])
    try:
        activity = asyncio.run(svc.update_activity(activity_id, **fields))
        click.echo(to_json_str(activity.model_dump(exclude_none=True)))
    except Exception as e:
        _handle(e)


# ------------------------------------------------------------------
# Activity sub-resources
# ------------------------------------------------------------------


@cli.command("get-intervals")
@click.argument("activity_id")
@click.pass_context
def get_intervals(ctx: click.Context, activity_id: str) -> None:
    """Get intervals (laps/splits) for an activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_activity_intervals(activity_id))
        _output(data, ctx, f"intervals_{activity_id}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-streams")
@click.argument("activity_id")
@click.option(
    "--types",
    default=None,
    help="Comma-separated stream types (e.g. watts,heartrate,cadence). Default: all.",
)
@click.pass_context
def get_streams(ctx: click.Context, activity_id: str, types: str | None) -> None:
    """Get time-series data streams for an activity. Saves to file by default (can be large)."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        type_list = [t.strip() for t in types.split(",")] if types else None
        data = asyncio.run(svc.get_activity_streams(activity_id, types=type_list))
        suffix = f"_{types.replace(',', '_')}" if types else ""
        _output(data, ctx, f"streams_{activity_id}{suffix}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-power-curve")
@click.argument("activity_id")
@click.pass_context
def get_power_curve(ctx: click.Context, activity_id: str) -> None:
    """Get the mean-maximal power (MMP) curve for an activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_power_curve(activity_id))
        _output(data, ctx, f"power_curve_{activity_id}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-hr-curve")
@click.argument("activity_id")
@click.pass_context
def get_hr_curve(ctx: click.Context, activity_id: str) -> None:
    """Get the heart rate curve for an activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_hr_curve(activity_id))
        _output(data, ctx, f"hr_curve_{activity_id}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-pace-curve")
@click.argument("activity_id")
@click.pass_context
def get_pace_curve(ctx: click.Context, activity_id: str) -> None:
    """Get the pace curve for an activity (running/swimming)."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_pace_curve(activity_id))
        _output(data, ctx, f"pace_curve_{activity_id}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-best-efforts")
@click.argument("activity_id")
@click.pass_context
def get_best_efforts(ctx: click.Context, activity_id: str) -> None:
    """Get best efforts found within an activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_best_efforts(activity_id))
        _output(data, ctx, f"best_efforts_{activity_id}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-segments")
@click.argument("activity_id")
@click.pass_context
def get_segments(ctx: click.Context, activity_id: str) -> None:
    """Get matched segments for an activity."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_activity_segments(activity_id))
        _output(data, ctx, f"segments_{activity_id}.json")
    except Exception as e:
        _handle(e)


# ------------------------------------------------------------------
# File downloads (streaming to disk)
# ------------------------------------------------------------------


@cli.command("download-activity-file")
@click.argument("activity_id")
@click.option(
    "--type",
    "file_type",
    type=click.Choice(["original", "fit", "gpx"]),
    default="original",
    show_default=True,
    help="File type to download.",
)
@click.pass_context
def download_activity_file(ctx: click.Context, activity_id: str, file_type: str) -> None:
    """Download an activity file (original, FIT, or GPX) to disk.

    Streams directly to disk — safe for files of any size.
    Output directory is set with the global -o / --output-dir option.
    """
    svc = IntervalsService(ctx.obj["config"])
    try:
        result = asyncio.run(
            svc.download_activity_file(
                activity_id, file_type, Path(ctx.obj["output_dir"])
            )
        )
        click.echo(f"Downloaded: {result.path}")
        click.echo(f"Size: {result.size_bytes:,} bytes ({result.content_type})")
    except Exception as e:
        _handle(e)


@cli.command("download-activities-csv")
@click.option("--oldest", required=True, help="Start date (ISO 8601, e.g. 2024-01-01)")
@click.option("--newest", required=True, help="End date (ISO 8601, e.g. 2024-12-31)")
@click.pass_context
def download_activities_csv(ctx: click.Context, oldest: str, newest: str) -> None:
    """Download all activities in a date range as a CSV file.

    Streams directly to disk. Use -o / --output-dir to set the destination directory.
    """
    svc = IntervalsService(ctx.obj["config"])
    try:
        result = asyncio.run(
            svc.download_activities_csv(oldest, newest, Path(ctx.obj["output_dir"]))
        )
        click.echo(f"Downloaded: {result.path}")
        click.echo(f"Size: {result.size_bytes:,} bytes ({result.content_type})")
    except Exception as e:
        _handle(e)


# ------------------------------------------------------------------
# Athlete-level aggregate curves
# ------------------------------------------------------------------


@cli.command("get-athlete-power-curves")
@click.option("--oldest", required=True, help="Start date (ISO 8601)")
@click.option("--newest", required=True, help="End date (ISO 8601)")
@click.pass_context
def get_athlete_power_curves(ctx: click.Context, oldest: str, newest: str) -> None:
    """Get best power curves across all activities in a date range."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_athlete_power_curves(oldest, newest))
        _output(data, ctx, f"power_curves_{oldest}_{newest}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-athlete-hr-curves")
@click.option("--oldest", required=True, help="Start date (ISO 8601)")
@click.option("--newest", required=True, help="End date (ISO 8601)")
@click.pass_context
def get_athlete_hr_curves(ctx: click.Context, oldest: str, newest: str) -> None:
    """Get best HR curves across all activities in a date range."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_athlete_hr_curves(oldest, newest))
        _output(data, ctx, f"hr_curves_{oldest}_{newest}.json")
    except Exception as e:
        _handle(e)


@cli.command("get-athlete-pace-curves")
@click.option("--oldest", required=True, help="Start date (ISO 8601)")
@click.option("--newest", required=True, help="End date (ISO 8601)")
@click.pass_context
def get_athlete_pace_curves(ctx: click.Context, oldest: str, newest: str) -> None:
    """Get best pace curves across all activities in a date range."""
    svc = IntervalsService(ctx.obj["config"])
    try:
        data = asyncio.run(svc.get_athlete_pace_curves(oldest, newest))
        _output(data, ctx, f"pace_curves_{oldest}_{newest}.json")
    except Exception as e:
        _handle(e)
