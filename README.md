# intervals-kit

MCP server, CLI, and Python library for the [Intervals.ICU](https://intervals.icu) fitness tracking API. Exposes activity data (power curves, HR curves, streams, intervals, segments, file downloads) to AI assistants via the Model Context Protocol, and as a command-line tool for scripting and bulk data access.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — recommended for running the package

## Installation

```bash
pip install intervals-kit
```

Or with uv:

```bash
uv pip install intervals-kit
```

## Configuration

The package reads credentials from environment variables or a config file.

**Environment variables (recommended):**

```bash
export INTERVALS_API_KEY=your_api_key      # From intervals.icu → Settings → API Key
export INTERVALS_ATHLETE_ID=iXXXXXX       # Your athlete ID (visible in the URL when logged in)
```

**Config file** (`~/.config/intervals-kit/config.toml`):

```toml
api_key = "your_api_key"
athlete_id = "iXXXXXX"
base_url = "https://intervals.icu"   # optional
```

Environment variables take precedence over the config file.

## Usage as MCP Server (Claude Code / Claude Desktop)

The easiest way — no installation needed:

```json
{
  "mcpServers": {
    "intervals-icu": {
      "command": "uvx",
      "args": ["intervals-kit"],
      "env": {
        "INTERVALS_API_KEY": "your_api_key",
        "INTERVALS_ATHLETE_ID": "iXXXXXX"
      }
    }
  }
}
```

Once configured, Claude can directly query your training data:

> "How many rides did I do last month?"
> "What was my best 5-minute power in March?"
> "Download my activities as a CSV for Q1 2025."

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_activities` | List activities for a date range |
| `get_activity` | Get full details for a single activity |
| `search_activities` | Search by name or tag |
| `update_activity` | Update name, description, type, or RPE |
| `get_activity_intervals` | Get lap/split data |
| `get_activity_streams` | Get second-by-second time-series (power, HR, cadence, …) |
| `get_power_curve` | Mean-maximal power curve for an activity |
| `get_hr_curve` | Heart rate curve for an activity |
| `get_pace_curve` | Pace curve for running/swimming |
| `get_best_efforts` | Best efforts detected in an activity |
| `get_activity_segments` | Matched Strava/Intervals segments |
| `get_activity_map` | GPS track (lat/lon) |
| `get_athlete_power_curves` | Best power curves across a date range |
| `get_athlete_hr_curves` | Best HR curves across a date range |

For large data (streams >1 hour, CSV exports, binary files) the MCP tools return metadata and tell Claude to use the CLI for the actual download.

## Usage as CLI

```bash
uvx --from intervals-kit intervals-icu-tools --help
```

### Activity commands

```bash
# List activities for a date range (JSON to stdout)
uvx --from intervals-kit intervals-icu-tools list-activities --oldest 2025-01-01 --newest 2025-03-31

# Save to a file instead of stdout
uvx --from intervals-kit intervals-icu-tools -o ./data list-activities --oldest 2025-01-01 --newest 2025-03-31

# Get a single activity
uvx --from intervals-kit intervals-icu-tools get-activity i136292802

# Search by name or tag (# prefix for exact tag match)
uvx --from intervals-kit intervals-icu-tools search-activities "long ride"
uvx --from intervals-kit intervals-icu-tools search-activities "#race" --full

# Update fields
uvx --from intervals-kit intervals-icu-tools update-activity i136292802 --perceived-exertion 7 --description "Felt strong"
```

### Sub-resource commands

```bash
# Lap/interval data
uvx --from intervals-kit intervals-icu-tools get-intervals i136292802

# Time-series streams (specify types to limit size)
uvx --from intervals-kit intervals-icu-tools -o ./data get-streams i136292802 --types watts,heartrate,cadence

# Power / HR / pace curves
uvx --from intervals-kit intervals-icu-tools get-power-curve i136292802
uvx --from intervals-kit intervals-icu-tools get-hr-curve i136292802
uvx --from intervals-kit intervals-icu-tools get-pace-curve i136292816  # running activity

# Best efforts, segments, GPS map
uvx --from intervals-kit intervals-icu-tools get-best-efforts i136292802
uvx --from intervals-kit intervals-icu-tools get-segments i136292802
uvx --from intervals-kit intervals-icu-tools -o ./data get-activity-map i136292802
```

### File download commands

```bash
# Download original upload / FIT / GPX file
uvx --from intervals-kit intervals-icu-tools -o ./data download-activity-file i136292802 --type fit
uvx --from intervals-kit intervals-icu-tools -o ./data download-activity-file i136292802 --type gpx

# Bulk CSV export for a date range
uvx --from intervals-kit intervals-icu-tools -o ./data download-activities-csv --oldest 2025-01-01 --newest 2025-03-31
```

### Aggregate curves

```bash
# Best power/HR/pace curves across all activities in a date range
uvx --from intervals-kit intervals-icu-tools get-athlete-power-curves --oldest 2025-01-01 --newest 2025-03-31
uvx --from intervals-kit intervals-icu-tools get-athlete-hr-curves --oldest 2025-01-01 --newest 2025-03-31
uvx --from intervals-kit intervals-icu-tools get-athlete-pace-curves --oldest 2025-01-01 --newest 2025-03-31
```

### Global options

| Option | Default | Description |
|--------|---------|-------------|
| `-o / --output-dir` | `.` (stdout) | Directory to save output files |
| `-f / --format` | `json` | Output format: `json` or `csv` |

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Auth error or general API error |
| 2 | Rate limit exceeded (retryable) |
| 3 | Download / network error (retryable) |
| 4 | Resource not found |

## Usage as Python Library

```python
import asyncio
from intervals_kit import IntervalsService, load_config

async def main():
    svc = IntervalsService(load_config())

    # List March 2025 activities
    activities = await svc.list_activities("2025-03-01", "2025-03-31")
    rides = [a for a in activities if a.type == "Ride"]
    print(f"Rides: {len(rides)}, Runs: {len(activities) - len(rides)}")

    # Get power curve for first ride
    if rides:
        curve = await svc.get_power_curve(rides[0].id)
        print(f"Power curve keys: {list(curve.keys())}")

asyncio.run(main())
```

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/jrsassen/intervals-kit
cd intervals-kit
uv sync

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_service.py -k test_name

# Run integration tests against the real API (requires credentials)
uv run pytest -m integration
```

## Architecture

Three interfaces share one service layer — see `SPECIFICATIONS.md` for the full architecture and `src/intervals_kit/cli_tools.md` for the complete CLI reference intended for LLM agents.

```
MCP Tools (FastMCP)  ──┐
CLI Commands (Click)  ──┼──▶  service.py  ──▶  client.py  ──▶  Intervals.ICU API
Python import        ──┘
```

Source layout:

```
src/intervals_kit/
├── errors.py        # Exception types
├── models.py        # Pydantic models
├── config.py        # Configuration loading
├── client.py        # HTTP client (auth, error mapping, streaming)
├── exporters.py     # JSON serialization
├── service.py       # All business logic
├── mcp_server.py    # FastMCP tool definitions
└── cli/             # Click command definitions
```
