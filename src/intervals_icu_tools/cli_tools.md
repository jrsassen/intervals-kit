# intervals-icu-tools CLI

Command-line interface for the Intervals.ICU fitness tracking API.

## Installation / Running

The MCP server `instructions` field contains the exact invocation for the current
installation. Use it as-is for all CLI calls. The general form is:

```bash
uv run --directory <project_dir> intervals-icu-tools <command>
```

Where `<project_dir>` is the absolute path to the cloned repository
(the directory containing `pyproject.toml`).

## Authentication

Set these environment variables before running:
```bash
export INTERVALS_API_KEY=your_api_key
export INTERVALS_ATHLETE_ID=your_athlete_id  # e.g. i123456
```

Or create `~/.config/intervals-icu-tools/config.toml`:
```toml
api_key = "your_api_key"
athlete_id = "your_athlete_id"
```

## Global Options

- `-o / --output-dir <dir>`: Directory to save output files (default: `.` = stdout)
- `-f / --format json|csv`: Output format for saved files (default: `json`)

## Available Commands

### list-activities
List activities for a date range. Prints JSON to stdout or saves with `-o`.

```
uv run intervals-icu-tools list-activities --oldest 2024-01-01 --newest 2024-12-31 [--limit 50] [-o ./data]
```

Output: Array of activity objects with id, name, type, start_date_local, distance, moving_time, icu_training_load, etc.
Use when: You need a summary of recent training for analysis or display.

### get-activity
Get all fields for a single activity.

```
uv run intervals-icu-tools get-activity <activity_id>
```

Output: Full activity JSON with all 173+ fields.

### search-activities
Search activities by name or tag.

```
uv run intervals-icu-tools search-activities "<query>" [--full] [--limit 20] [-o ./data]
```

Options:
- `--full`: Return full activity details (default: summary fields only)
Use when: The user references an activity by name or you need to find a specific workout.

### update-activity
Update editable fields on an activity.

```
uv run intervals-icu-tools update-activity <activity_id> [--name "New Name"] [--description "..."] [--type Run] [--perceived-exertion 7]
```

Output: Updated activity JSON.

### get-intervals
Get structured interval/lap data for an activity.

```
uv run intervals-icu-tools get-intervals <activity_id> [-o ./data]
```

Output: JSON with `icu_intervals` (each with avg/max power, HR, cadence, duration) and `icu_groups`.
Use when: You need lap-by-lap performance breakdown.

### get-streams
Get second-by-second time-series data for an activity.

```
uv run intervals-icu-tools get-streams <activity_id> [--types watts,heartrate,cadence] [-o ./data]
```

Available stream types: `time, watts, heartrate, cadence, distance, altitude, lat, lon, speed, temperature, smo2, thb`
Output: Array of stream objects, each with `type`, `name`, `data` array.
IMPORTANT: For activities >1 hour, output is large (>50KB). Always use `-o` to save to disk.

### get-power-curve
Get the mean-maximal power (MMP) curve for an activity.

```
uv run intervals-icu-tools get-power-curve <activity_id> [-o ./data]
```

Output: JSON with duration buckets (secs) and peak power values (watts).
Use when: Analyzing peak efforts at specific durations (5s, 1min, 5min, 20min, FTP).

### get-hr-curve
Get the heart rate curve for an activity.

```
uv run intervals-icu-tools get-hr-curve <activity_id> [-o ./data]
```

Output: JSON with duration buckets and peak HR values (bpm).

### get-pace-curve
Get the pace curve for running/swimming activities.

```
uv run intervals-icu-tools get-pace-curve <activity_id> [-o ./data]
```

Output: JSON with distance buckets and best pace values (m/s).

### get-best-efforts
Get best efforts detected in an activity (fastest 1km, 5km, 10km, etc.).

```
uv run intervals-icu-tools get-best-efforts <activity_id> [-o ./data]
```

Output: JSON with `efforts` list — each has distance/duration, elapsed time, avg power/HR/pace.

### get-segments
Get matched Strava/Intervals segments for an activity.

```
uv run intervals-icu-tools get-segments <activity_id> [-o ./data]
```

Output: Array of segment objects with name, distance, elapsed time, rank, PR status.

### download-activity-file
Download an activity file (original upload, FIT, or GPX) to disk.

```
uv run intervals-icu-tools download-activity-file <activity_id> --type original|fit|gpx -o ./data
```

Output: File saved to `<output-dir>/`. Prints path and size on success.
IMPORTANT: Streams directly to disk — safe for any file size. Binary files should always
be saved with `-o`, not printed to stdout.

### download-activities-csv
Download all activities in a date range as a CSV file.

```
uv run intervals-icu-tools download-activities-csv --oldest 2024-01-01 --newest 2024-12-31 -o ./data
```

Output: `activities.csv` saved to output directory. Prints path and size on success.
Use when: You need bulk activity data for analysis (spreadsheets, pandas, etc.).

### get-athlete-power-curves
Get best power curves across all activities in a date range.

```
uv run intervals-icu-tools get-athlete-power-curves --oldest 2024-01-01 --newest 2024-12-31 [-o ./data]
```

Output: Aggregated power curve data showing peak watts at each duration across all activities.
Use when: Tracking fitness progression or comparing training blocks.

### get-athlete-hr-curves
Get best HR curves across all activities in a date range.

```
uv run intervals-icu-tools get-athlete-hr-curves --oldest 2024-01-01 --newest 2024-12-31 [-o ./data]
```

### get-athlete-pace-curves
Get best pace curves across all activities in a date range.

```
uv run intervals-icu-tools get-athlete-pace-curves --oldest 2024-01-01 --newest 2024-12-31 [-o ./data]
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Auth error / general API error |
| 2 | Rate limit exceeded (retryable) |
| 3 | Download / network error (retryable) |
| 4 | Resource not found |

## Common Patterns

### MCP → CLI handoff for large streams
1. Use MCP tool `get_activity_streams` for short activities (<1 hour)
2. For longer activities, use CLI to save to disk:
   ```
   uv run intervals-icu-tools get-streams <id> --types watts,heartrate -o ./data
   ```
3. Read the saved JSON file for analysis

### Download then analyze
```bash
uv run intervals-icu-tools download-activities-csv --oldest 2024-01-01 --newest 2024-12-31 -o ./data
head -5 ./data/activities.csv
```

### Find activity by name then get its power curve
```bash
uv run intervals-icu-tools search-activities "long ride"
# → get the id from results
uv run intervals-icu-tools get-power-curve <id>
```

## Python Library Usage

For complex analysis, import the service layer directly:

```python
import asyncio
from intervals_icu_tools import IntervalsService, load_config

async def main():
    svc = IntervalsService(load_config())
    activities = await svc.list_activities("2024-01-01", "2024-12-31", limit=100)
    rides = [a for a in activities if a.type == "Ride"]
    print(f"Found {len(rides)} rides")

asyncio.run(main())
```
