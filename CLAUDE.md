# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Python package providing an MCP server and CLI for the Intervals.ICU REST API. See `docs/SPECIFICATIONS.md` for the architecture spec (used to guide adding new endpoints) and `src/intervals_kit/cli_tools.md` for the full CLI reference.

## Commands

```bash
# Setup (first time)
uv sync

# Run MCP server
uv run intervals-icu-mcp

# Run CLI
uv run intervals-icu-tools --help

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_service.py -k test_name

# Run integration tests (real API, requires API key set)
uv run pytest -m integration

# Build for publishing
uv build
```

## Build sequence

Follow this exact order — each phase depends on the previous one importing cleanly:

1. **Phase 1 (Skeleton):** Create dirs, `.python-version`, `pyproject.toml`, run `uv sync`
2. **Phase 2 (Core):** `errors.py` → `models.py` → `config.py` → `client.py` → `exporters.py` → `service.py`
   - Verify: `uv run python -c "from myapi_tools.service import MyAPIService; print('ok')"`
3. **Phase 3 (MCP):** `mcp_server.py`
   - Verify: `uv run intervals-icu-tools-mcp &; kill %1`
4. **Phase 4 (CLI):** `cli/__init__.py` → `cli/main.py` → `cli/commands.py`
   - Verify: `uv run intervals-icu-tools --help`
5. **Phase 5 (Docs & Tests):** `cli_tools.md`, `tests/`
6. **Phase 6 (Publish):** `uv build && uv publish`

## Architecture

Three interfaces, one service layer:

```
MCP Tools (FastMCP)  ──┐
CLI Commands (Click)  ──┼──▶  service.py  ──▶  client.py  ──▶  Intervals.ICU REST API
Library API (import) ──┘
```

- **`service.py`** — all business logic lives here. MCP tools and CLI commands are thin wrappers.
- **`client.py`** — low-level `httpx` async client (auth, retry, config).
- **`models.py`** — Pydantic models for API request/response shapes.
- **`config.py`** — priority chain: env vars > `~/.config/.../config.toml` > defaults.
- **`exporters.py`** — output formatting (JSON, CSV, markdown).
- **`mcp_server.py`** — FastMCP wrapper; registers tools calling service methods.
- **`cli/`** — Click group + commands; thin wrappers calling service methods.
- **`__init__.py`** — exports only the core layer (`MyAPIService`, `ApiConfig`, models, errors). Never import `mcp_server` or `cli` here.

## Key design rules

1. ALL business logic goes in `service.py`. MCP tools and CLI are thin wrappers.
2. ALL features are exposed via CLI, MCP, AND as importable Python functions.
3. MCP tools return small structured data (<100 items, <50KB) — fits in LLM context.
4. CLI commands handle large/binary data (streams to disk, no size cap).
5. MCP tool docstrings must include: what it does, when to use it, return shape, and the exact `uvx` CLI command for handoff to bulk/binary operations.
6. CLI prints structured, parseable output — no progress bars, no ANSI color codes.
7. MCP tools return error dicts on failure (never raise). CLI prints to stderr and exits with structured codes: 0=success, 1=auth/general, 2=rate limit, 3=download, 4=not found.

## Deciding what gets an MCP tool vs CLI command

| Endpoint type | MCP tool | CLI command |
|---|---|---|
| Small structured response (<100 items) | Yes (full data) | Yes |
| Large dataset (paginated, bulk) | Yes (capped preview, limit=20) | Yes (full download) |
| Binary/large blob (PDF, ZIP) | Yes (metadata only) | Yes (streaming download) |
| Async server-side job | Yes (start job, return job ID) | Yes (start + poll + download) |
| Mutating (POST/PUT/DELETE) | Yes | Yes |
| Auth/config/health | No — handle in `client.py` | No |

## Testing

- Mock at the HTTP boundary with `respx`, not at the service layer — tests cover the full stack.
- Test error paths explicitly (LLM relies on structured error output).
- Test that all MCP tools have docstrings (missing docstring = silent LLM discoverability failure).
- Test CLI exit codes (they are part of the contract with calling LLM agents).
- No real API calls in CI — use `respx` mocks. Real API tests use `@pytest.mark.integration`.

## Technology choices

| Package | Role | Notes |
|---|---|---|
| `fastmcp>=3.0,<4` | MCP server | Import as `from fastmcp import FastMCP`, not the SDK-bundled version |
| `httpx>=0.27` | HTTP client | Async-native; use `respx` to mock in tests |
| `pydantic>=2.0` | Data models | Already a transitive dep of FastMCP |
| `click>=8.0` | CLI | Lighter than `typer` (no `rich`/`shellingham` pull) |
| `hatchling` | Build backend | Used via `uv build` |
| `pytest-asyncio` | Async tests | Use `@pytest.mark.asyncio` on async test functions |
