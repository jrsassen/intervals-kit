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

- `-o / --output-dir <path>`: Directory **or full file path** to save output (default: `.` = stdout).
  - Directory: `uv run intervals-icu-tools -o ./data list-activities …` → saves to `./data/activities_<dates>.json`
  - File path: `uv run intervals-icu-tools -o ./data/my_activities.json list-activities …` → saves to exactly that path
- `-f / --format json|csv`: Output format for saved files (default: `json`)

**IMPORTANT**: Global options must come **before** the subcommand name:
```
uv run intervals-icu-tools -o ./data list-activities --oldest 2024-01-01 --newest 2024-12-31
#                          ^^^^^^^^^^^ before subcommand ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```
Placing `-o` after the subcommand causes: `Error: No such option: -o`

## Available Commands

### list-activities
List activities for a date range. Prints JSON to stdout or saves with `-o`.

```
uv run intervals-icu-tools [-o ./data] list-activities --oldest 2024-01-01 --newest 2024-12-31 [--limit 50]
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
uv run intervals-icu-tools [-o ./data] search-activities "<query>" [--full] [--limit 20]
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
uv run intervals-icu-tools [-o ./data] get-intervals <activity_id>
```

Output: JSON with `icu_intervals` (each with avg/max power, HR, cadence, duration) and `icu_groups`.
Use when: You need lap-by-lap performance breakdown.

### get-streams
Get second-by-second time-series data for an activity.

```
uv run intervals-icu-tools [-o ./data] get-streams <activity_id> [--types watts,heartrate,cadence]
```

Available stream types: `time, watts, heartrate, cadence, distance, altitude, lat, lon, speed, temperature, smo2, thb`
Output: Array of stream objects, each with `type`, `name`, `data` array.
IMPORTANT: For activities >1 hour, output is large (>50KB). Always use `-o ./data` (before the subcommand) to save to disk.

### get-power-curve
Get the mean-maximal power (MMP) curve for an activity.

```
uv run intervals-icu-tools [-o ./data] get-power-curve <activity_id>
```

Output: JSON with duration buckets (secs) and peak power values (watts).
Use when: Analyzing peak efforts at specific durations (5s, 1min, 5min, 20min, FTP).

### get-hr-curve
Get the heart rate curve for an activity.

```
uv run intervals-icu-tools [-o ./data] get-hr-curve <activity_id>
```

Output: JSON with duration buckets and peak HR values (bpm).

### get-pace-curve
Get the pace curve for running/swimming activities.

```
uv run intervals-icu-tools [-o ./data] get-pace-curve <activity_id>
```

Output: JSON with distance buckets and best pace values (m/s).

### get-best-efforts
Get best efforts detected in an activity (fastest 1km, 5km, 10km, etc.).

```
uv run intervals-icu-tools [-o ./data] get-best-efforts <activity_id>
```

Output: JSON with `efforts` list — each has distance/duration, elapsed time, avg power/HR/pace.

### get-segments
Get matched Strava/Intervals segments for an activity.

```
uv run intervals-icu-tools [-o ./data] get-segments <activity_id>
```

Output: Array of segment objects with name, distance, elapsed time, rank, PR status.

### download-activity-file
Download an activity file (original upload, FIT, or GPX) to disk.

```
uv run intervals-icu-tools -o ./data download-activity-file <activity_id> --type original|fit|gpx
```

Output: File saved to `<output-dir>/`. Prints path and size on success.
IMPORTANT: Streams directly to disk — safe for any file size. Binary files should always
be saved with `-o`, not printed to stdout.

### download-activities-csv
Download all activities in a date range as a CSV file.

```
uv run intervals-icu-tools -o ./data download-activities-csv --oldest 2024-01-01 --newest 2024-12-31
```

Output: `activities.csv` saved to output directory. Prints path and size on success.
Use when: You need bulk activity data for analysis (spreadsheets, pandas, etc.).

### get-athlete-power-curves
Get best power curves across all activities in a date range.

```
uv run intervals-icu-tools [-o ./data] get-athlete-power-curves --oldest 2024-01-01 --newest 2024-12-31
```

Output: Aggregated power curve data showing peak watts at each duration across all activities.
Use when: Tracking fitness progression or comparing training blocks.

### get-athlete-hr-curves
Get best HR curves across all activities in a date range.

```
uv run intervals-icu-tools [-o ./data] get-athlete-hr-curves --oldest 2024-01-01 --newest 2024-12-31
```

### get-athlete-pace-curves
Get best pace curves across all activities in a date range.

```
uv run intervals-icu-tools [-o ./data] get-athlete-pace-curves --oldest 2024-01-01 --newest 2024-12-31
```

### get-athlete
Get the athlete's profile (FTP, thresholds, sport settings, preferences).

```
uv run intervals-icu-tools [-o ./data] get-athlete
```

Output: Full athlete JSON with id, name, weight, icu_ftp, icu_resting_hr, timezone, measurement_preference, and all other profile fields.

### update-athlete
Update athlete profile fields.

```
uv run intervals-icu-tools update-athlete --fields '{"weight": 70.5, "timezone": "Europe/Berlin"}'
```

Options:
- `--fields / -j`: JSON object of fields to update. Common fields: name, weight (kg), sex ("M"/"F"), measurement_preference ("metric"/"imperial"), fahrenheit (bool), timezone.

### list-wellness
List wellness records for a date range.

```
uv run intervals-icu-tools [-o ./data] list-wellness --oldest 2024-01-01 --newest 2024-12-31
```

Output: Array of wellness records with id (date), ctl, atl, weight, restingHR, hrv, sleepSecs, sleepScore, fatigue, stress, mood, motivation.

### get-wellness
Get the wellness record for a specific date.

```
uv run intervals-icu-tools get-wellness 2024-01-15
```

Output: Single wellness record JSON.

### update-wellness
Update (or create) the wellness record for a specific date.

```
uv run intervals-icu-tools update-wellness 2024-01-15 --fields '{"weight": 70.2, "sleepSecs": 28800, "fatigue": 3}'
```

Options:
- `--fields / -j` (required): JSON object of wellness fields. Common: weight (kg), restingHR (bpm), hrv (ms), sleepSecs (seconds), sleepScore (0–100), sleepQuality (1–5), fatigue (1–7), stress (1–7), mood (1–7), motivation (1–7), soreness (1–7).

### list-events
List calendar events (planned workouts, races, notes) for a date range.

```
uv run intervals-icu-tools [-o ./data] list-events --oldest 2024-01-01 --newest 2024-12-31 [--category WORKOUT,RACE_A]
```

Options:
- `--category`: Filter by comma-separated categories: WORKOUT, RACE_A, RACE_B, RACE_C, NOTE
- `--limit / -l`: Max events to return

Output: Array of event objects with id, name, category, start_date_local, type, moving_time, icu_training_load, description.

### get-event
Get a single calendar event by ID.

```
uv run intervals-icu-tools get-event <event_id>
```

### create-event
Create a calendar event (planned workout, note, race, etc.).

```
uv run intervals-icu-tools create-event --fields '{"name": "Long Run", "category": "WORKOUT", "start_date_local": "2024-03-15T09:00:00", "type": "Run", "moving_time": 5400}'
```

Options:
- `--fields / -j` (required): JSON object. Common fields: name, category (WORKOUT/NOTE/RACE_A/RACE_B/RACE_C), start_date_local (ISO 8601 datetime), type (Run/Ride/Swim/etc.), description, moving_time (seconds), indoor (bool).

### update-event
Update a calendar event. Only provided fields are changed.

```
uv run intervals-icu-tools update-event <event_id> --fields '{"name": "Recovery Ride", "moving_time": 3600}'
```

### delete-event
Delete a calendar event.

```
uv run intervals-icu-tools delete-event <event_id>
```

### list-workouts
List all workouts in the athlete's library.

```
uv run intervals-icu-tools [-o ./data] list-workouts
```

Output: Array of workout objects with id, name, type, moving_time, icu_training_load, folder_id, tags.

### get-workout
Get a single workout from the library.

```
uv run intervals-icu-tools get-workout <workout_id>
```

Output: Full workout JSON including workout_doc (structured steps).

### create-workout
Create a new workout in the athlete's library.

```
uv run intervals-icu-tools create-workout --fields '{"name": "Tempo Run", "type": "Run", "moving_time": 3600}'
```

Options:
- `--fields / -j` (required): JSON object. Common fields: name (required), type (Run/Ride/Swim/etc.), description, moving_time (seconds), indoor (bool), folder_id (int), tags (list of strings), workout_doc (structured steps).

### update-workout
Update a workout in the library.

```
uv run intervals-icu-tools update-workout <workout_id> --fields '{"name": "Updated Name"}'
```

### delete-workout
Delete a workout from the library.

```
uv run intervals-icu-tools delete-workout <workout_id>
```

### list-messages
List all comments on an activity.

```
uv run intervals-icu-tools [-o ./data] list-messages <activity_id>
```

Output: Array of message objects with id, content, athlete_id, athlete_name, updated.

### create-message
Post a comment on an activity.

```
uv run intervals-icu-tools create-message <activity_id> "Great workout!"
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
   uv run intervals-icu-tools -o ./data get-streams <id> --types watts,heartrate
   ```
3. Read the saved JSON file for analysis

### Download then analyze
```bash
uv run intervals-icu-tools -o ./data download-activities-csv --oldest 2024-01-01 --newest 2024-12-31
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
