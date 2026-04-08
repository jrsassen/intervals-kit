"""intervals-icu-tools — MCP server, CLI, and Python library for the Intervals.ICU API.

Library usage:
    from intervals_kit import IntervalsService, load_config

    config = load_config()  # reads INTERVALS_API_KEY and INTERVALS_ATHLETE_ID
    service = IntervalsService(config)
    activities = await service.list_activities("2024-01-01", "2024-12-31")
"""

__version__ = "0.1.1"

# Public library API — importable by scripts and notebooks.
# Do NOT import mcp_server or cli here: they have heavy deps (FastMCP, Click)
# and MCP startup side effects. Keep `import intervals_kit` fast.
from .config import ApiConfig, load_config
from .errors import (
    AuthenticationError,
    DownloadError,
    IntervalsError,
    NotFoundError,
    RateLimitError,
)
from .models import Activity, ActivitySearchResult, FileDownloadResult
from .service import IntervalsService

__all__ = [
    "IntervalsService",
    "ApiConfig",
    "load_config",
    "Activity",
    "ActivitySearchResult",
    "FileDownloadResult",
    "IntervalsError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "DownloadError",
]
