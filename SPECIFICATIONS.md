# MCP + CLI Project Structure

> A Python package that provides **both** an MCP server and a CLI tool wrapping the same REST API,
> installable and runnable with zero setup via `uvx`.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          End Users                               │
│                                                                  │
│   Claude Code / claude.ai     Claude Code / LLM    LLM-generated │
│   (MCP client via stdio)      (CLI via terminal)    Python code   │
│         │                           │                    │        │
│         ▼                           ▼                    ▼        │
│   ┌───────────┐            ┌──────────────┐    ┌──────────────┐  │
│   │ MCP Server│            │  CLI (click)  │    │ Library API  │  │
│   │ (FastMCP) │            │              │    │ (import)     │  │
│   └─────┬─────┘            └──────┬───────┘    └──────┬───────┘  │
│         │                         │                    │          │
│         ▼                         ▼                    ▼          │
│   ┌────────────────────────────────────────────────────────┐     │
│   │                 Shared Service Layer                    │     │
│   │              (business logic, data models)              │     │
│   └───────────────────────┬────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│   ┌────────────────────────────────────────────────────────┐     │
│   │                  API Client Layer                       │     │
│   │           (httpx async, auth, retry, config)            │     │
│   └───────────────────────┬────────────────────────────────┘     │
│                           │                                      │
│                           ▼                                      │
│                    REST API (external)                            │
└──────────────────────────────────────────────────────────────────┘
```

The key insight: **MCP tools, CLI commands, and direct Python imports are thin wrappers**
around the same service functions. All business logic, data transformation, and API
interaction live in the shared layers. The three interfaces differ only in how they receive
arguments and format output:

| Interface | Input | Output | Consumer |
|-----------|-------|--------|----------|
| MCP tools | Tool call from LLM | JSON in LLM context | Claude Code, claude.ai |
| CLI commands | Terminal args | Files on disk + stdout | LLM agents, humans, scripts |
| Library API | Python function call | Pydantic models / dicts | LLM-generated code, notebooks |

---

## Directory Structure

```
myapi-tools/
├── pyproject.toml              # Single source of truth: metadata, deps, entry points
├── CLAUDE.md                   # Project instructions for Claude Code (dev-time)
├── README.md                   # User-facing docs (install, configure, use)
├── LICENSE
├── .python-version             # Pin Python version (e.g. "3.12")
│
├── src/
│   └── myapi_tools/
│       ├── __init__.py         # Package version (__version__ = "0.1.0")
│       │
│       ├── config.py           # Configuration: env vars, config file, defaults
│       ├── errors.py           # Exception hierarchy (MyAPIError and subclasses)
│       ├── client.py           # Low-level REST API client (httpx)
│       ├── models.py           # Pydantic models for API request/response shapes
│       ├── service.py          # Shared business logic (the core of everything)
│       ├── exporters.py        # Output formatting: JSON, CSV, markdown
│       │
│       ├── mcp_server.py       # MCP server: thin wrapper registering tools
│       │
│       ├── cli/
│       │   ├── __init__.py     # Imports commands to register them with Click
│       │   ├── main.py         # Click group + global options (--output-dir, --format)
│       │   └── commands.py     # CLI commands: thin wrappers calling service layer
│       │
│       └── cli_tools.md        # LLM-readable description of CLI capabilities
│
└── tests/
    ├── conftest.py             # Shared fixtures (mock API responses, temp dirs)
    ├── test_client.py
    ├── test_service.py
    ├── test_mcp.py
    └── test_cli.py
```

---

## Build Sequence (for Claude Code)

Follow this exact order. Each step depends on the previous one compiling/importing cleanly.

```
Phase 1: Project Skeleton
─────────────────────────
1.  mkdir -p myapi-tools/src/myapi_tools/cli myapi-tools/tests
2.  cd myapi-tools
3.  Create .python-version         → "3.12"
4.  Create pyproject.toml          → copy from spec below, adapt name/description
5.  uv sync                        → creates .venv, installs all deps
    (verify: uv run python -c "from fastmcp import FastMCP; print('ok')")

Phase 2: Core Layer (no MCP/CLI dependency)
───────────────────────────────────────────
6.  Create src/myapi_tools/__init__.py
7.  Create src/myapi_tools/errors.py
8.  Create src/myapi_tools/models.py
9.  Create src/myapi_tools/config.py
10. Create src/myapi_tools/client.py
11. Create src/myapi_tools/exporters.py
12. Create src/myapi_tools/service.py
    (verify: uv run python -c "from myapi_tools.service import MyAPIService; print('ok')")

Phase 3: MCP Server
────────────────────
13. Create src/myapi_tools/mcp_server.py
    (verify: uv run myapi-tools-mcp &   → should start and listen on stdio
     kill %1)

Phase 4: CLI
─────────────
14. Create src/myapi_tools/cli/__init__.py
15. Create src/myapi_tools/cli/main.py
16. Create src/myapi_tools/cli/commands.py
    (verify: uv run myapi-tools --help   → should show command list)

Phase 5: Documentation & Tests
──────────────────────────────
17. Create src/myapi_tools/cli_tools.md
18. Create CLAUDE.md
19. Create tests/conftest.py
20. Create tests/test_client.py, test_service.py, test_mcp.py, test_cli.py
    (verify: uv run pytest)

Phase 6: Publish
────────────────
21. uv build
22. uv publish
```

**Why this order matters:** Steps 6–12 can be tested in isolation with just `python -c`.
The MCP server and CLI only import from the core layer, so if Phase 2 works, Phases 3–4
will not hit import errors. Building outward from the core also means you can iterate on
the API mapping (the hardest part) before dealing with MCP/CLI wiring.

---

## Mapping API Endpoints to Tools and Commands

**Rule: every feature gets a CLI command.** The CLI is the universal interface — it works
for LLM agents via terminal, for human users, and for shell scripts. MCP tools are an
additional fast path for LLM context, but never the *only* path.

When reading the API documentation, use this decision framework for each endpoint:

```
For each API endpoint, ask:
│
├─ Does it return a small, structured response (<100 items, <50KB)?
│  └─ YES → MCP tool (data goes into LLM context)
│          + CLI command (same data, saved to disk)
│          Example: GET /items?limit=20   → MCP `list_items` + CLI `list`
│                   GET /search?q=...     → MCP `search` + CLI `search`
│
├─ Does it return a large dataset (>100 items, paginated, bulk)?
│  └─ YES → CLI command (data goes to disk, no size cap)
│          + MCP tool with capped limit for preview (limit=20)
│          Example: GET /items?limit=10000 → CLI `download`
│                   GET /items?limit=20   → MCP `list_items`
│
├─ Does it return a binary file or large blob (PDF, ZIP, Parquet, image)?
│  └─ YES → CLI command for download (streams to disk)
│          + MCP tool for metadata only (HEAD or GET /files/{id}/info)
│          MCP docstring includes the exact CLI command for download
│          Example: GET /files/{id}/content → CLI `download-file`
│                   GET /files/{id}/info    → MCP `get_file_info`
│
├─ Does it trigger a server-side job (export generation, async processing)?
│  └─ YES → CLI command to request + poll + download (full lifecycle)
│          + MCP tool to start the job (returns job ID, lightweight)
│          Example: POST /exports              → MCP `request_export` + CLI `request-export`
│                   GET /exports/{id}/download  → CLI `download-export`
│
├─ Does it mutate state (POST/PUT/DELETE)?
│  └─ YES → MCP tool (LLM needs confirmation flow in context)
│          + CLI command (same operation, for scripting or batch use)
│          Example: POST /items → MCP `create_item` + CLI `create`
│
└─ Is it an auth/config/health endpoint?
   └─ SKIP — handle internally in client.py, don't expose to users
```

**Rules of thumb:**
- Every MCP tool should have a docstring that reads like instructions for an LLM.
  Include: what it does, when to use it vs alternatives, what the return shape looks like,
  and (for handoff scenarios) the exact CLI command to use next.
- Every CLI command should print structured, parseable output. The LLM will read stdout.
  Format: one summary line, then key=value pairs. No progress bars, no color codes.
- Every feature exposed via MCP or CLI must also be callable as a Python function via the
  service layer (see "Library Usage" below). The three interfaces are just different
  wrappers around the same `MyAPIService` methods.

---

## File-by-File Description

### `CLAUDE.md` — Project Instructions for Claude Code

This file lives at the project root and is automatically read by Claude Code when it
opens the project. It ties together the MCP server, CLI, and development workflow.

```markdown
# myapi-tools

## What this project is
A Python package providing an MCP server and CLI for the MyAPI REST API.
Published to PyPI, installed via `uvx`. See project-structure.md for architecture.

## Project layout
- `src/myapi_tools/` — all source code
- Core layer: config.py → errors.py → models.py → client.py → service.py → exporters.py
- MCP server: mcp_server.py (thin wrapper over service layer)
- CLI: cli/main.py + cli/commands.py (thin wrapper over service layer)
- Tests: tests/

## Key architectural rules
1. ALL business logic goes in service.py. MCP tools and CLI commands are thin wrappers.
2. ALL features are exposed via CLI, MCP, AND as importable Python functions.
3. MCP tools return small structured data (fits in LLM context, <100 items).
4. CLI commands handle all operations including large/binary data (streams to disk).
5. The service layer is the library API: `from myapi_tools import MyAPIService`.
6. MCP tool docstrings include exact `uvx` CLI commands for the handoff pattern.
7. The CLI prints structured, parseable output (no progress bars, no color codes).

## How to run
- MCP server: `uv run myapi-tools-mcp`
- CLI: `uv run myapi-tools --help`
- Tests: `uv run pytest`
- Single test: `uv run pytest tests/test_service.py -k test_name`

## How to test against the real API
Set MYAPI_KEY in your environment, then: `uv run myapi-tools list electronics`

## CLI tool documentation (for use by LLM agents)
See src/myapi_tools/cli_tools.md for the full CLI reference.
When operating as an agent, prefer MCP tools for quick lookups and the CLI for
bulk downloads or binary files.
```

### `src/myapi_tools/__init__.py` — Package Root & Public Library API

```python
"""MyAPI Tools — MCP server, CLI, and Python library for the MyAPI REST API.

Library usage:
    from myapi_tools import MyAPIService, ApiConfig

    config = ApiConfig(api_key="sk-...")
    service = MyAPIService(config)

    # Async usage
    items = await service.list_items("electronics", limit=50)

    # Or use the sync convenience wrapper
    from myapi_tools import sync_client
    items = sync_client.list_items("electronics", limit=50)
"""

__version__ = "0.1.0"

# Public API — importable by LLM-generated code and notebooks
from .config import ApiConfig, load_config
from .service import MyAPIService
from .models import Item, FileDownloadResult  # re-export key models
from .errors import MyAPIError, AuthenticationError, RateLimitError, NotFoundError

__all__ = [
    "MyAPIService",
    "ApiConfig",
    "load_config",
    "Item",
    "FileDownloadResult",
    "MyAPIError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
]
```

This exposes the service layer as a first-class Python library. An LLM generating a
script can write `from myapi_tools import MyAPIService, load_config` and call any
service method directly — no MCP, no CLI, no subprocess.

**Important:** Do NOT import `mcp_server` or `cli` here. Those are entry-point modules
with heavy imports (FastMCP, Click) that should only load when their entry points run.
The library API imports only the core layer (config, models, service, errors), keeping
`import myapi_tools` fast and lightweight.

### `src/myapi_tools/errors.py` — Exception Hierarchy

```python
"""Typed exceptions for API and application errors."""

class MyAPIError(Exception):
    """Base exception for all MyAPI errors."""
    pass

class AuthenticationError(MyAPIError):
    """API key is missing, invalid, or expired."""
    pass

class RateLimitError(MyAPIError):
    """API rate limit exceeded. Includes retry_after_seconds if available."""
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after

class NotFoundError(MyAPIError):
    """Requested resource does not exist."""
    pass

class ExportError(MyAPIError):
    """Server-side export job failed."""
    pass

class DownloadError(MyAPIError):
    """File download failed (network error, incomplete stream, etc.)."""
    pass
```

Both the MCP server and CLI must handle these, but differently (see Error Handling below).

### `pyproject.toml` — Package Configuration

This is the most critical file. It defines two entry points (MCP server + CLI), all
dependencies, and the build system. Using `hatchling` as the build backend because it's
lightweight, widely supported, and works perfectly with `uvx`.

```toml
[project]
name = "myapi-tools"
version = "0.1.0"
description = "MCP server and CLI for the MyAPI REST API"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"

dependencies = [
    "fastmcp>=3.0,<4",         # MCP server framework (standalone, not the SDK-bundled one)
    "httpx>=0.27",              # Async HTTP client for REST API calls
    "pydantic>=2.0",            # Data validation and serialization
    "click>=8.0",               # CLI framework
]

[project.scripts]
# CLI entry point: `uvx myapi-tools <command>` or after install: `myapi-tools <command>`
# Points to cli/__init__.py which imports commands.py for registration
myapi-tools = "myapi_tools.cli:cli"

# MCP entry point: used in Claude Code / Claude Desktop config
myapi-tools-mcp = "myapi_tools.mcp_server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/myapi_tools"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "respx>=0.22",              # Mock httpx requests
]
```

**Why these choices:**

| Decision | Rationale |
|----------|-----------|
| `fastmcp` (standalone v3) | Actively maintained, 3.x has providers/transforms, better than SDK-bundled `mcp.server.fastmcp`. Import as `from fastmcp import FastMCP`. |
| `httpx` | Async-native, required by FastMCP anyway (transitive dep). Prefer over `requests` for async MCP tools. |
| `click` | Minimal, composable, no magic. Lighter than `typer` (which pulls in `rich` + `shellingham`). |
| `hatchling` | Fast, simple build backend. No `setup.py` needed. |
| `pydantic` | Already a transitive dep of FastMCP. Use it explicitly for your own models. |

### `src/myapi_tools/config.py` — Configuration Management

Handles auth and settings with a clear priority chain:
1. **Environment variables** (highest priority) — `MYAPI_KEY`, `MYAPI_BASE_URL`
2. **Config file** — `~/.config/myapi-tools/config.toml`
3. **Defaults** (lowest priority)

Both the MCP server and CLI read from the same config. The MCP server can also receive
the API key via the Claude config JSON (which sets it as an env var), so env vars taking
precedence is the correct behavior.

Uses `tomllib` (stdlib in Python 3.11+) for config file parsing, with a fallback to
`tomli` for 3.10 compatibility (add as optional dep if you need 3.10 support).

### `src/myapi_tools/client.py` — REST API Client

A thin async wrapper around `httpx.AsyncClient`:

- Constructs base URL, auth headers, common params
- Implements retry logic with exponential backoff
- Raises typed exceptions (subclasses of a base `MyAPIError`)
- Handles pagination (if the API supports it)
- **Streaming downloads** for large/binary files (reports, archives, media)
- **Does not contain business logic** — just HTTP mechanics

Both sync and async callers are supported: the service layer uses `async`, and the CLI
runs it via `asyncio.run()`. The MCP server is natively async.

The client exposes two HTTP patterns:

```python
async def get(self, path: str, params: dict = None) -> dict:
    """Standard JSON request/response for structured data."""
    ...

async def download_file(self, path: str, dest: Path, params: dict = None) -> FileDownloadResult:
    """Streaming download for large or binary responses.

    Streams directly to disk — never loads the full response into memory.
    Returns metadata (size, content_type, filename) without the file content.
    """
    async with self._client.stream("GET", path, params=params) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream")
        # Extract filename from Content-Disposition header if available
        filename = _parse_content_disposition(response.headers) or dest.name
        total = 0
        with open(dest / filename, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
    return FileDownloadResult(path=dest / filename, size=total, content_type=content_type)
```

This is critical for the file export scenario: the API may return PDFs, ZIPs, Parquet
files, or other binary formats that are multi-MB to multi-GB. Streaming avoids OOM errors
and lets the CLI report download progress.

### `src/myapi_tools/models.py` — Data Models

Pydantic models representing API entities. Shared across all layers:

- `ApiConfig` — validated configuration (base_url, api_key, timeout)
- `FileDownloadResult` — metadata from a streaming download (path, size, content_type)
- Request/response models for each API endpoint
- Export models (what gets written to JSON/CSV)

### `src/myapi_tools/service.py` — Shared Business Logic

**This is where all the real work lives.** A `MyAPIService` class (or module of functions)
that:

- Accepts an `ApiConfig` and creates a client
- Exposes high-level operations: `list_items()`, `get_item()`, `search()`, `download_all()`
- Exposes file operations: `download_file()` for large/binary API responses
- Handles data transformation and aggregation
- Returns Pydantic models or dicts — never raw HTTP responses

Both the MCP server and CLI call these same functions. Example:

```python
class MyAPIService:
    def __init__(self, config: ApiConfig):
        self.client = MyAPIClient(config)

    async def list_items(self, category: str, limit: int = 100) -> list[Item]:
        """Fetch items by category from the API."""
        raw = await self.client.get("/items", params={"cat": category, "limit": limit})
        return [Item.model_validate(r) for r in raw["results"]]

    async def download_all(self, category: str, output_dir: Path, fmt: str = "json") -> Path:
        """Download all items and save to files. Returns path to output."""
        items = await self.list_items(category, limit=10000)
        return export(items, output_dir, fmt)

    async def download_file(self, file_id: str, output_dir: Path) -> FileDownloadResult:
        """Download a file (report, export, binary asset) from the API.

        Streams the response directly to disk. The API may return any content
        type — PDF reports, ZIP archives, Parquet datasets, images, etc.
        The filename is extracted from the Content-Disposition header or
        derived from the file_id.
        """
        return await self.client.download_file(
            f"/files/{file_id}/content",
            dest=output_dir,
        )

    async def request_and_download_export(
        self, category: str, fmt: str, output_dir: Path
    ) -> FileDownloadResult:
        """Request a server-side export and download the resulting file.

        Some APIs generate exports asynchronously: you POST a request, poll
        for completion, then download the artifact. This method handles the
        full lifecycle.
        """
        # 1. Request the export
        job = await self.client.post(f"/exports", json={"category": category, "format": fmt})
        export_id = job["id"]

        # 2. Poll until ready
        while True:
            status = await self.client.get(f"/exports/{export_id}")
            if status["state"] == "completed":
                break
            if status["state"] == "failed":
                raise MyAPIError(f"Export {export_id} failed: {status.get('error')}")
            await asyncio.sleep(2)

        # 3. Stream download the resulting file
        return await self.client.download_file(
            f"/exports/{export_id}/download",
            dest=output_dir,
        )
```

### `src/myapi_tools/exporters.py` — Output Formatting

Functions that take Pydantic models and write them to files:

- `export_json(items, path)` — pretty-printed JSON
- `export_csv(items, path)` — flattened CSV with headers
- `export(items, output_dir, fmt)` — dispatcher

### `src/myapi_tools/mcp_server.py` — MCP Server

Thin wrapper that registers FastMCP tools. Each tool is a few lines that call the service
layer and format the response for the LLM context window.

```python
from fastmcp import FastMCP
from .config import load_config
from .service import MyAPIService

mcp = FastMCP("myapi-tools")

@mcp.tool
async def list_items(category: str, limit: int = 20) -> list[dict]:
    """List items from MyAPI by category.

    Args:
        category: The category to filter by (e.g. "electronics", "books")
        limit: Maximum number of items to return (default: 20, max: 100)

    Returns:
        List of items with id, name, description, and price fields.
    """
    config = load_config()
    service = MyAPIService(config)
    items = await service.list_items(category, limit=min(limit, 100))
    return [item.model_dump() for item in items]

@mcp.tool
async def search(query: str, max_results: int = 10) -> list[dict]:
    """Search for items across all categories.

    Args:
        query: Free-text search query
        max_results: Maximum results to return (default: 10)
    """
    config = load_config()
    service = MyAPIService(config)
    return [item.model_dump() for item in await service.search(query, max_results)]

@mcp.tool
async def get_file_info(file_id: str) -> dict:
    """Get metadata about a downloadable file (report, export, dataset) WITHOUT
    downloading it. Use this to check file size, type, and name before deciding
    whether to download.

    Args:
        file_id: The file identifier from the API

    Returns:
        Dict with name, size_bytes, content_type, created_at, and download_url.
        If the file is large or binary, use the CLI to download it:
        `uvx myapi-tools download-file <file_id> -o ./output`
    """
    config = load_config()
    service = MyAPIService(config)
    return (await service.get_file_metadata(file_id)).model_dump()

@mcp.tool
async def request_export(category: str, fmt: str = "csv") -> dict:
    """Request the API to generate an export file for a category.

    This starts an async server-side job. The response includes an export_id
    and status. Once the status is "completed", download the file using the CLI:
    `uvx myapi-tools download-export <export_id> -o ./output`

    DO NOT use this for small queries — use list_items or search instead.
    Use this only when the user needs a complete dataset as a file.

    Args:
        category: Category to export
        fmt: Export format — "csv", "json", or "parquet"

    Returns:
        Dict with export_id, status, estimated_size_bytes.
    """
    config = load_config()
    service = MyAPIService(config)
    job = await service.request_export(category, fmt)
    return job.model_dump()

def main():
    """Entry point for the MCP server."""
    mcp.run()
```

**The MCP ↔ CLI handoff for large/binary files:**

This is the most important architectural pattern in the project. MCP tools run inside the
LLM's context window — returning a 50 MB PDF or a 200 MB Parquet file as a tool result
would be catastrophic (context overflow, wasted tokens, binary garbage in chat). Instead:

1. The **MCP tool** provides metadata and initiates server-side jobs (lightweight, fits in context)
2. The **MCP tool's docstring** tells the LLM exactly which CLI command to run next
3. The **LLM shells out** to the CLI via the terminal: `uvx myapi-tools download-file abc123 -o ./data`
4. The **CLI** streams the file to disk and prints a summary (path, size, type)
5. The **LLM reads the CLI output** (a few lines of text) and reports back to the user

This is why the docstrings contain the exact `uvx` command — they serve as instructions
to the LLM agent, not just documentation for humans.

**Key design decisions for MCP tools:**

- **Cap results** (`limit: 100`): MCP tools return data into the LLM context window.
  Large results waste tokens and degrade performance.
- **Return dicts, not raw text**: FastMCP serializes them to JSON automatically.
- **Docstrings are the tool descriptions**: FastMCP extracts them for the LLM. Write
  them as if you're explaining to an LLM what the tool does and when to use it.
- **No file I/O in MCP tools**: If the user needs bulk data, point them to the CLI.

### Error Handling Patterns

Errors from the API client bubble up as typed exceptions (see `errors.py`). The MCP
server and CLI handle them differently:

**In MCP tools** — return error information as text the LLM can reason about. Never raise
exceptions through MCP (the client sees an opaque "internal error"). Instead, catch and
return a structured error dict:

```python
@mcp.tool
async def list_items(category: str, limit: int = 20) -> dict | list[dict]:
    """..."""
    try:
        config = load_config()
        service = MyAPIService(config)
        items = await service.list_items(category, limit=min(limit, 100))
        return [item.model_dump() for item in items]
    except AuthenticationError:
        return {"error": "Authentication failed. Check that MYAPI_KEY is set correctly."}
    except RateLimitError as e:
        return {"error": f"Rate limited. Retry after {e.retry_after} seconds."}
    except NotFoundError:
        return {"error": f"Category '{category}' not found."}
    except MyAPIError as e:
        return {"error": f"API error: {e}"}
```

**In CLI commands** — print to stderr and exit with a non-zero code. The LLM reads both
stdout and stderr, so the error message should be concise and actionable:

```python
@cli.command()
@click.pass_context
def download(ctx, category, limit):
    """..."""
    try:
        service = MyAPIService(ctx.obj["config"])
        result = asyncio.run(service.download_all(...))
        click.echo(f"Saved {result.count} items to {result.path}")
    except AuthenticationError:
        click.echo("Error: Authentication failed. Set MYAPI_KEY environment variable.", err=True)
        raise SystemExit(1)
    except RateLimitError as e:
        click.echo(f"Error: Rate limited. Retry after {e.retry_after}s.", err=True)
        raise SystemExit(2)
    except DownloadError as e:
        click.echo(f"Error: Download failed: {e}", err=True)
        raise SystemExit(3)
    except MyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

**Exit code convention** for the CLI (so the calling LLM can react programmatically):

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / auth error |
| 2 | Rate limit (retryable) |
| 3 | Download / network error (retryable) |
| 4 | Not found |

### `src/myapi_tools/cli/__init__.py` — Command Registration

This file is critical for Click's command discovery. It imports the commands module so
that the `@cli.command()` decorators run and register themselves with the Click group:

```python
"""CLI package. Import commands to register them with the Click group."""

from .main import cli
from . import commands  # noqa: F401 — import triggers @cli.command() registration
```

Without this import, `uvx myapi-tools --help` would show zero commands.

### `src/myapi_tools/cli/main.py` — CLI Entry Point

```python
import click
from ..config import load_config

@click.group()
@click.option("--output-dir", "-o", default=".", help="Directory for output files")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.pass_context
def cli(ctx, output_dir, fmt):
    """MyAPI Tools — download and process data from MyAPI."""
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = output_dir
    ctx.obj["format"] = fmt
    ctx.obj["config"] = load_config()
```

**Important:** The `[project.scripts]` entry point in pyproject.toml points to
`myapi_tools.cli:cli` — that's the `cli` object exported from `cli/__init__.py`.
The import chain is: entry point → `cli/__init__.py` (imports `cli` from `main.py`,
imports `commands.py` for side-effect registration) → `commands.py` (decorators attach
commands to the group). This is the standard Click pattern for multi-file CLIs.

### `src/myapi_tools/cli/commands.py` — CLI Commands

Each command calls the service layer and writes output to files:

```python
import asyncio
import click
from .main import cli
from ..service import MyAPIService

@cli.command()
@click.argument("category")
@click.option("--limit", "-l", default=10000, help="Max items to download")
@click.pass_context
def download(ctx, category, limit):
    """Download all items in CATEGORY and save to files."""
    service = MyAPIService(ctx.obj["config"])
    result = asyncio.run(
        service.download_all(category, ctx.obj["output_dir"], ctx.obj["format"])
    )
    click.echo(f"Saved {result.count} items to {result.path}")

@cli.command("download-file")
@click.argument("file_id")
@click.pass_context
def download_file(ctx, file_id):
    """Download a file (report, export, binary asset) by its ID.

    Streams the file directly to disk. Supports any content type
    (PDF, ZIP, Parquet, images, etc.). The filename is determined
    by the API's Content-Disposition header.
    """
    service = MyAPIService(ctx.obj["config"])
    result = asyncio.run(
        service.download_file(file_id, Path(ctx.obj["output_dir"]))
    )
    click.echo(f"Downloaded: {result.path}")
    click.echo(f"Size: {result.size:,} bytes ({result.content_type})")

@cli.command("download-export")
@click.argument("export_id")
@click.pass_context
def download_export(ctx, export_id):
    """Download a previously requested export by its export ID.

    If the export is still processing, waits until it completes.
    Use `request-export` or the MCP `request_export` tool to initiate.
    """
    service = MyAPIService(ctx.obj["config"])
    result = asyncio.run(
        service.download_export(export_id, Path(ctx.obj["output_dir"]))
    )
    click.echo(f"Downloaded: {result.path}")
    click.echo(f"Size: {result.size:,} bytes ({result.content_type})")

@cli.command("request-export")
@click.argument("category")
@click.option("--format", "-f", "fmt", type=click.Choice(["csv", "json", "parquet"]), default="csv")
@click.option("--wait/--no-wait", default=True, help="Wait for completion and download")
@click.pass_context
def request_export(ctx, category, fmt, wait):
    """Request a server-side export for CATEGORY, optionally wait and download.

    With --wait (default): blocks until the export is ready, then downloads.
    With --no-wait: prints the export_id immediately so you can download later.
    """
    service = MyAPIService(ctx.obj["config"])
    if wait:
        result = asyncio.run(
            service.request_and_download_export(category, fmt, Path(ctx.obj["output_dir"]))
        )
        click.echo(f"Downloaded: {result.path}")
        click.echo(f"Size: {result.size:,} bytes ({result.content_type})")
    else:
        job = asyncio.run(service.request_export(category, fmt))
        click.echo(f"Export requested: {job.id}")
        click.echo(f"Status: {job.status}")
        click.echo(f"Download later: uvx myapi-tools download-export {job.id}")

@cli.command("list")
@click.argument("category")
@click.option("--limit", "-l", default=100, help="Max items to return")
@click.pass_context
def list_items(ctx, category, limit):
    """List items in CATEGORY (prints to stdout or saves to file).

    With --format json (default): prints JSON to stdout (pipeable).
    With -o <dir>: saves to file instead of printing.
    """
    service = MyAPIService(ctx.obj["config"])
    items = asyncio.run(service.list_items(category, limit=limit))
    output_dir = ctx.obj.get("output_dir")
    if output_dir and output_dir != ".":
        result = export(items, Path(output_dir), ctx.obj["format"])
        click.echo(f"Saved {len(items)} items to {result.path}")
    else:
        for item in items:
            click.echo(json.dumps(item.model_dump(), indent=2))

@cli.command()
@click.argument("query")
@click.option("--max-results", "-n", default=50, help="Max results to return")
@click.pass_context
def search(ctx, query, max_results):
    """Search for items matching QUERY across all categories."""
    service = MyAPIService(ctx.obj["config"])
    items = asyncio.run(service.search(query, max_results))
    output_dir = ctx.obj.get("output_dir")
    if output_dir and output_dir != ".":
        result = export(items, Path(output_dir), ctx.obj["format"])
        click.echo(f"Saved {len(items)} results to {result.path}")
    else:
        for item in items:
            click.echo(json.dumps(item.model_dump(), indent=2))

@cli.command("file-info")
@click.argument("file_id")
@click.pass_context
def file_info(ctx, file_id):
    """Get metadata about a downloadable file (without downloading it)."""
    service = MyAPIService(ctx.obj["config"])
    meta = asyncio.run(service.get_file_metadata(file_id))
    click.echo(json.dumps(meta.model_dump(), indent=2))
```

### `src/myapi_tools/cli_tools.md` — LLM-Readable CLI Documentation

This is the file Claude Code (or any LLM agent) reads to understand how to use the CLI.
It's not code — it's a structured description designed for LLM consumption.

```markdown
# myapi-tools CLI

## Installation
Run any command without installing: `uvx myapi-tools <command>`

## Authentication
Set `MYAPI_KEY` environment variable before running commands.

## Available Commands

### list
List items in a category. Prints JSON to stdout by default (pipeable).
Usage: `uvx myapi-tools list <category> [--limit N] [--format json|csv] [-o output_dir]`
Output: JSON to stdout, or saves to file with -o.
Use when: You need structured data for a quick lookup or to pipe into another tool.

### search
Search for items matching a query across all categories.
Usage: `uvx myapi-tools search "<query>" [--max-results N] [--format json|csv] [-o dir]`
Output: JSON to stdout, or saves to file with -o.

### file-info
Get metadata about a downloadable file (without downloading it).
Usage: `uvx myapi-tools file-info <file_id>`
Output: JSON with name, size_bytes, content_type, created_at.
Use when: You want to check a file before deciding to download it.

### download
Download all items in a category and save to local files.
Usage: `uvx myapi-tools download <category> [--limit N] [--format json|csv] [-o output_dir]`
Output: Creates `<category>_items.{json|csv}` in the output directory.
Use when: You need to fetch large structured datasets that shouldn't go into the LLM context.

### download-file
Download a single file (report, binary asset, dataset) by its file ID.
Usage: `uvx myapi-tools download-file <file_id> [-o output_dir]`
Output: Saves the file to the output directory. Filename comes from the API.
The file may be any type: PDF, ZIP, Parquet, PNG, etc.
Use when: The MCP tool `get_file_info` returned metadata for a file and you need the actual content.
IMPORTANT: This streams directly to disk — safe for files of any size.

### download-export
Download a previously requested server-side export.
Usage: `uvx myapi-tools download-export <export_id> [-o output_dir]`
Output: Saves the export file. Waits for completion if the export is still processing.
Use when: The MCP tool `request_export` returned an export_id.

### request-export
Request a server-side data export and optionally wait for it.
Usage: `uvx myapi-tools request-export <category> [--format csv|json|parquet] [--wait|--no-wait] [-o dir]`
With --wait (default): blocks until ready, then downloads the file.
With --no-wait: prints the export_id immediately for later download.
Use when: You need a complete bulk export that the API generates server-side.

### search
Search across all categories and save results.
Usage: `uvx myapi-tools search "<query>" [--max-results N] [--format json|csv] [-o dir]`
Output: Creates `search_<query>.{json|csv}` in the output directory.

## Common Patterns

### Fetch a large file via MCP + CLI handoff
1. Use MCP tool `get_file_info` to check what the file is (size, type).
2. Run: `uvx myapi-tools download-file <file_id> -o ./data`
3. Read the CLI output to confirm path and size.
4. If the file is text-based (CSV, JSON), read it with `cat` or `head`.
5. If binary (PDF, ZIP), tell the user where it was saved.

### Bulk export workflow
1. Use MCP tool `request_export` to start a server-side export job.
2. Run: `uvx myapi-tools download-export <export_id> -o ./data`
3. Or combine: `uvx myapi-tools request-export electronics --format parquet -o ./data`

### Download then analyze
`uvx myapi-tools download electronics -o ./data && head -20 ./data/electronics_items.json`

### Search and save
`uvx myapi-tools search "wireless headphones" -f csv -o ./results`

### Quick pipe to stdout
`uvx myapi-tools list electronics --limit 5 | python -c "import sys,json; print(json.load(sys.stdin))"`

## Python Library Usage
For more complex processing, import the service layer directly in a script:
```python
import asyncio
from myapi_tools import MyAPIService, load_config

async def main():
    service = MyAPIService(load_config())
    items = await service.list_items("electronics", limit=50)
    expensive = [i for i in items if i.price > 100]
    print(f"Found {len(expensive)} expensive items")

asyncio.run(main())
```
Requires: `uv add myapi-tools` or `pip install myapi-tools` in the project environment.
Use when: You need to filter, transform, or combine API data in ways the CLI doesn't support.
```

---

## How Users Install & Configure

### MCP Server (Claude Code)

In `.claude/mcp.json` or the Claude Code MCP config:

```json
{
  "mcpServers": {
    "myapi-tools": {
      "command": "uvx",
      "args": ["myapi-tools-mcp"],
      "env": {
        "MYAPI_KEY": "your-api-key-here"
      }
    }
  }
}
```

That's it. No `pip install`, no venv, no Python version management. `uvx` handles
everything: it downloads the package, creates an isolated environment, and runs the
`myapi-tools-mcp` entry point.

### MCP Server (Claude Desktop)

Same pattern in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "myapi-tools": {
      "command": "uvx",
      "args": ["myapi-tools-mcp"],
      "env": {
        "MYAPI_KEY": "your-api-key-here"
      }
    }
  }
}
```

### CLI (terminal / Claude Code slash command)

```bash
# One-off usage (zero install):
uvx myapi-tools download electronics --format csv -o ./data

# Or install permanently:
uv tool install myapi-tools
myapi-tools download electronics --format csv -o ./data
```

### Python Library (in scripts / notebooks / LLM-generated code)

```bash
# Add to a project:
uv add myapi-tools

# Or pip install:
pip install myapi-tools
```

Then in Python:

```python
import asyncio
from myapi_tools import MyAPIService, load_config

async def main():
    service = MyAPIService(load_config())  # reads MYAPI_KEY from env
    items = await service.list_items("electronics", limit=50)
    for item in items:
        print(f"{item.name}: ${item.price}")

asyncio.run(main())
```

This is the preferred path when an LLM generates a Python script that needs API data —
it imports the service directly instead of shelling out to the CLI or going through MCP.

### Configuration File (optional)

For users who don't want to pass env vars every time:

```toml
# ~/.config/myapi-tools/config.toml
api_key = "sk-..."
base_url = "https://api.example.com/v1"    # optional override
timeout = 30                                # optional, seconds
```

---

## Dependency Summary

### Runtime Dependencies (4 packages + their transitive deps)

| Package | Purpose | Why not alternatives |
|---------|---------|---------------------|
| `fastmcp>=3.0,<4` | MCP server framework | De-facto standard. v3 is the actively maintained standalone version with providers, transforms, and hot reload. Do NOT use `mcp.server.fastmcp` from the SDK — it's the old v1 fork. |
| `httpx>=0.27` | Async HTTP client | Async-native, already a transitive dep of FastMCP. Using it directly avoids pulling in `requests` too. |
| `pydantic>=2.0` | Data validation | Already transitive dep of FastMCP. Use explicitly for your own models. |
| `click>=8.0` | CLI framework | Minimal, no heavy deps. `typer` would add `rich` + `shellingham`. `argparse` is too verbose for grouped commands. |

**Total unique transitive dependencies** (approximate): ~15-20 packages. The `uvx`
ephemeral environment makes this irrelevant to the user — they never see or manage these.

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest>=8.0` | Test runner |
| `pytest-asyncio>=0.24` | Async test support |
| `respx>=0.22` | Mock httpx requests in tests |

---

## Key Design Principles

### 1. The Service Layer Is King
All business logic lives in `service.py`. The MCP server, CLI, and library API are dumb
wrappers. This means:
- Zero duplicated logic
- You can test the core independently of MCP, Click, or import mechanics
- The service layer IS the library API — `__init__.py` just re-exports it
- Adding a fourth interface (e.g., a web UI) requires only a new thin wrapper

### 2. Three Interfaces, One Service

All features are available through all three interfaces. They differ in how they receive
input and format output:

| Aspect | MCP Tools | CLI Commands | Library (import) |
|--------|-----------|--------------|------------------|
| **Consumer** | LLM (context window) | Terminal / file system | Python scripts, notebooks |
| **Input** | Tool call JSON | CLI args | Function arguments |
| **Output** | JSON in LLM context | Files on disk + stdout | Pydantic models / dicts |
| **Volume** | Capped (~100 items) | Uncapped (streams to disk) | Uncapped (in memory) |
| **Binary files** | Metadata only | Streaming download to disk | Streaming download to disk |
| **Error handling** | Returns error dict | Stderr + exit code | Raises typed exceptions |
| **Use case** | Quick lookups in chat | Bulk ops, scripting | Custom processing logic |

**The CLI exposes every feature**, not just bulk operations. This ensures users always
have a fallback that works without MCP, and that shell scripts can automate everything.

### 3. The MCP → CLI Handoff Pattern for Large/Binary Files

This is the central pattern that makes MCP and CLI complementary rather than redundant:

```
User: "Download the Q3 revenue report"
                │
                ▼
   LLM calls MCP tool: get_file_info("report-q3-2025")
                │
                ▼
   MCP returns: { name: "Q3_Revenue.pdf", size: 12_400_000, content_type: "application/pdf" }
                │
                ▼
   LLM sees: "12 MB PDF — too large for context, docstring says to use CLI"
                │
                ▼
   LLM runs in terminal: uvx myapi-tools download-file report-q3-2025 -o ./reports
                │
                ▼
   CLI streams 12 MB to disk, prints: "Downloaded: ./reports/Q3_Revenue.pdf (12,400,000 bytes)"
                │
                ▼
   LLM tells user: "Downloaded the Q3 revenue report to ./reports/Q3_Revenue.pdf (12.4 MB PDF)"
```

The MCP tool docstrings contain the exact `uvx` command the LLM should run. This is by
design — the docstrings serve as instructions to the LLM agent, not just human
documentation. The LLM never needs to guess the CLI syntax.

### 4. LLM-Friendly CLI Descriptions
The `cli_tools.md` file is the bridge that lets Claude Code (or any LLM agent) know the
CLI exists and how to use it. Without it, the LLM would only know about MCP tools. With
it, the LLM can decide: "This query needs bulk data → use the CLI" vs "This query needs
a quick lookup → use the MCP tool."

Place this file in the project README, or provide it as an MCP resource, or instruct
Claude Code to read it (e.g., via a CLAUDE.md project instruction file).

### 5. `uvx` as the Only Install Path
By targeting `uvx` exclusively:
- Users need only `uv` installed (one binary, installs in seconds)
- No Python version conflicts — `uvx` creates isolated environments
- No `pip install` into system Python
- Package updates: `uvx myapi-tools@latest <command>` or `uv tool upgrade myapi-tools`

---

## Publishing to PyPI

```bash
# Build
uv build

# Publish (requires PyPI token)
uv publish
```

After publishing, any user with `uv` installed can immediately run:

```bash
uvx myapi-tools download electronics
# or
uvx myapi-tools-mcp  # starts the MCP server
```

No other setup required.

---

## Testing Strategy

### `tests/conftest.py` — Shared Fixtures

```python
"""Shared test fixtures for all test modules."""

import pytest
from pathlib import Path
from myapi_tools.config import ApiConfig
from myapi_tools.service import MyAPIService

@pytest.fixture
def api_config():
    """A valid test configuration (does NOT hit real API)."""
    return ApiConfig(
        api_key="test-key-123",
        base_url="https://api.example.com/v1",
        timeout=5,
    )

@pytest.fixture
def service(api_config):
    """Service instance with test config."""
    return MyAPIService(api_config)

@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for file downloads."""
    return tmp_path / "output"

# --- Mock API response data ---

@pytest.fixture
def mock_items():
    """Sample item list as the API would return it."""
    return {
        "results": [
            {"id": "item-1", "name": "Widget", "category": "electronics", "price": 9.99},
            {"id": "item-2", "name": "Gadget", "category": "electronics", "price": 19.99},
        ],
        "total": 2,
    }

@pytest.fixture
def mock_file_metadata():
    """Sample file metadata response."""
    return {
        "id": "file-abc",
        "name": "Q3_Report.pdf",
        "size_bytes": 12_400_000,
        "content_type": "application/pdf",
        "created_at": "2025-09-15T10:00:00Z",
    }
```

### `tests/test_client.py` — API Client Tests

Use `respx` to mock httpx requests. Test both JSON responses and streaming downloads:

```python
"""Tests for the low-level API client."""

import pytest
import respx
import httpx
from pathlib import Path
from myapi_tools.client import MyAPIClient
from myapi_tools.errors import AuthenticationError, RateLimitError, NotFoundError

@pytest.fixture
def client(api_config):
    return MyAPIClient(api_config)

@respx.mock
@pytest.mark.asyncio
async def test_get_success(client, mock_items):
    """Standard JSON GET returns parsed response."""
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(200, json=mock_items)
    )
    result = await client.get("/items", params={"cat": "electronics"})
    assert result["total"] == 2

@respx.mock
@pytest.mark.asyncio
async def test_get_auth_error(client):
    """401 raises AuthenticationError."""
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )
    with pytest.raises(AuthenticationError):
        await client.get("/items")

@respx.mock
@pytest.mark.asyncio
async def test_get_rate_limit(client):
    """429 raises RateLimitError with retry_after."""
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )
    with pytest.raises(RateLimitError) as exc_info:
        await client.get("/items")
    assert exc_info.value.retry_after == 30.0

@respx.mock
@pytest.mark.asyncio
async def test_download_file_streams_to_disk(client, tmp_output):
    """Streaming download writes file to disk without loading into memory."""
    tmp_output.mkdir()
    file_content = b"fake PDF content " * 10000  # ~170KB
    respx.get("https://api.example.com/v1/files/abc/content").mock(
        return_value=httpx.Response(
            200,
            content=file_content,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="report.pdf"',
            },
        )
    )
    result = await client.download_file("/files/abc/content", dest=tmp_output)
    assert result.path.exists()
    assert result.path.name == "report.pdf"
    assert result.size == len(file_content)
    assert result.content_type == "application/pdf"
```

### `tests/test_service.py` — Service Layer Tests

Test business logic in isolation from HTTP. Mock the client, verify the service transforms
data correctly:

```python
"""Tests for the shared service layer."""

import pytest
from unittest.mock import AsyncMock, patch
from myapi_tools.service import MyAPIService

@pytest.mark.asyncio
async def test_list_items_transforms_response(service, mock_items):
    """Service returns validated Pydantic models from raw API response."""
    with patch.object(service.client, "get", new=AsyncMock(return_value=mock_items)):
        items = await service.list_items("electronics", limit=10)
    assert len(items) == 2
    assert items[0].name == "Widget"
    assert items[0].price == 9.99

@pytest.mark.asyncio
async def test_download_all_writes_json(service, mock_items, tmp_output):
    """download_all creates a JSON file on disk."""
    tmp_output.mkdir()
    with patch.object(service.client, "get", new=AsyncMock(return_value=mock_items)):
        result = await service.download_all("electronics", tmp_output, fmt="json")
    assert result.path.suffix == ".json"
    assert result.path.exists()
```

### `tests/test_mcp.py` — MCP Server Tests

FastMCP provides a test client for in-process testing without starting a real server:

```python
"""Tests for MCP tools."""

import pytest
import respx
import httpx
from fastmcp import Client
from myapi_tools.mcp_server import mcp

@pytest.fixture
def mcp_client():
    """In-process MCP test client."""
    return Client(mcp)

@respx.mock
@pytest.mark.asyncio
async def test_list_items_tool(mcp_client, mock_items, monkeypatch):
    """MCP list_items tool returns capped, serialized items."""
    monkeypatch.setenv("MYAPI_KEY", "test-key")
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(200, json=mock_items)
    )
    async with mcp_client:
        result = await mcp_client.call_tool("list_items", {"category": "electronics"})
    # result is a list of TextContent; parse the JSON from it
    assert "Widget" in str(result)

@respx.mock
@pytest.mark.asyncio
async def test_list_items_auth_error_returns_error_dict(mcp_client, monkeypatch):
    """MCP tool returns error dict instead of raising on auth failure."""
    monkeypatch.setenv("MYAPI_KEY", "bad-key")
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(401)
    )
    async with mcp_client:
        result = await mcp_client.call_tool("list_items", {"category": "electronics"})
    assert "error" in str(result).lower()
    assert "authentication" in str(result).lower()

@pytest.mark.asyncio
async def test_all_tools_have_docstrings(mcp_client):
    """Every MCP tool must have a docstring (it becomes the LLM description)."""
    async with mcp_client:
        tools = await mcp_client.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' is missing a docstring"
```

### `tests/test_cli.py` — CLI Tests

Use Click's `CliRunner` for isolated CLI testing (no real subprocess, no real API):

```python
"""Tests for CLI commands."""

import pytest
import respx
import httpx
from click.testing import CliRunner
from myapi_tools.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

@respx.mock
def test_download_writes_file(runner, mock_items, tmp_path, monkeypatch):
    """download command creates output file and prints summary."""
    monkeypatch.setenv("MYAPI_KEY", "test-key")
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(200, json=mock_items)
    )
    result = runner.invoke(cli, ["--output-dir", str(tmp_path), "download", "electronics"])
    assert result.exit_code == 0
    assert "Saved" in result.output

@respx.mock
def test_download_file_streams_binary(runner, tmp_path, monkeypatch):
    """download-file command streams to disk and prints path + size."""
    monkeypatch.setenv("MYAPI_KEY", "test-key")
    respx.get("https://api.example.com/v1/files/abc/content").mock(
        return_value=httpx.Response(
            200,
            content=b"fake binary content",
            headers={"Content-Type": "application/pdf",
                     "Content-Disposition": 'attachment; filename="report.pdf"'},
        )
    )
    result = runner.invoke(cli, ["--output-dir", str(tmp_path), "download-file", "abc"])
    assert result.exit_code == 0
    assert "report.pdf" in result.output
    assert (tmp_path / "report.pdf").exists()

def test_missing_api_key_exits_with_error(runner, monkeypatch):
    """CLI exits with code 1 and helpful message when MYAPI_KEY is not set."""
    monkeypatch.delenv("MYAPI_KEY", raising=False)
    result = runner.invoke(cli, ["download", "electronics"])
    assert result.exit_code == 1
    assert "MYAPI_KEY" in result.output or "authentication" in result.output.lower()

@respx.mock
def test_rate_limit_exits_with_code_2(runner, monkeypatch):
    """CLI exits with code 2 on rate limit so LLM knows to retry."""
    monkeypatch.setenv("MYAPI_KEY", "test-key")
    respx.get("https://api.example.com/v1/items").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "10"})
    )
    result = runner.invoke(cli, ["download", "electronics"])
    assert result.exit_code == 2
```

### Testing Principles

- **Mock at the HTTP boundary** (`respx`), not at the service layer — this tests the full
  stack from tool/command → service → client → (mocked) HTTP.
- **Test error paths explicitly** — the LLM relies on structured error output to decide
  what to do next (retry, change params, report to user).
- **Test MCP docstrings exist** — a missing docstring means the LLM gets no tool
  description, which silently breaks discoverability.
- **Test CLI exit codes** — they're part of the contract with the calling LLM agent.
- **No real API calls in CI** — all tests use `respx` mocks. For integration tests
  against the real API, use a separate `pytest.ini` marker:
  `pytest -m integration` (and mark those tests with `@pytest.mark.integration`).
