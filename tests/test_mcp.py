"""Tests for MCP server tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from intervals_icu_tools.mcp_server import mcp
from intervals_icu_tools.errors import AuthenticationError, RateLimitError, NotFoundError


@pytest.fixture
def mcp_client() -> Client:
    return Client(mcp)


class TestAllToolsHaveDocstrings:
    async def test_all_tools_have_docstrings(self, mcp_client: Client) -> None:
        """Every MCP tool must have a docstring — it becomes the LLM tool description."""
        async with mcp_client:
            tools = await mcp_client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool '{tool.name}' is missing a docstring"


class TestListActivities:
    async def test_returns_activity_list(
        self, mcp_client: Client, sample_activities: list[dict]
    ) -> None:
        from intervals_icu_tools.models import Activity
        activities = [Activity.model_validate(a) for a in sample_activities]
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.list_activities = AsyncMock(return_value=activities)
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "list_activities", {"oldest": "2024-01-01", "newest": "2024-12-31"}
                )
        assert result is not None
        text = str(result)
        assert "Morning Ride" in text

    async def test_auth_error_returns_error_dict(self, mcp_client: Client) -> None:
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.list_activities = AsyncMock(
                side_effect=AuthenticationError("Bad key")
            )
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "list_activities", {"oldest": "2024-01-01", "newest": "2024-12-31"}
                )
        assert "error" in str(result).lower()
        assert "authentication" in str(result).lower()

    async def test_rate_limit_returns_retry_info(self, mcp_client: Client) -> None:
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.list_activities = AsyncMock(
                side_effect=RateLimitError("Limited", retry_after=30.0)
            )
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "list_activities", {"oldest": "2024-01-01", "newest": "2024-12-31"}
                )
        assert "30" in str(result)

    async def test_not_found_returns_error_dict(self, mcp_client: Client) -> None:
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.list_activities = AsyncMock(
                side_effect=NotFoundError("Not found")
            )
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "list_activities", {"oldest": "2024-01-01", "newest": "2024-12-31"}
                )
        assert "error" in str(result).lower()


class TestGetActivity:
    async def test_returns_activity_fields(
        self, mcp_client: Client, sample_activity: dict
    ) -> None:
        from intervals_icu_tools.models import Activity
        activity = Activity.model_validate(sample_activity)
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.get_activity = AsyncMock(return_value=activity)
            async with mcp_client:
                result = await mcp_client.call_tool("get_activity", {"activity_id": "99001"})
        assert "Morning Ride" in str(result)
        assert "99001" in str(result)


class TestUpdateActivity:
    async def test_filters_none_fields(
        self, mcp_client: Client, sample_activity: dict
    ) -> None:
        from intervals_icu_tools.models import Activity
        updated = Activity.model_validate({**sample_activity, "name": "Updated Name"})
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.update_activity = AsyncMock(return_value=updated)
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "update_activity",
                    {"activity_id": "99001", "name": "Updated Name"},
                )
        assert "Updated Name" in str(result)
        # Verify only non-None fields were passed
        call_kwargs = mock_svc.return_value.update_activity.call_args[1]
        assert "name" in call_kwargs
        assert "description" not in call_kwargs


class TestGetStreams:
    async def test_parses_types_string(
        self, mcp_client: Client, sample_streams: list[dict]
    ) -> None:
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.get_activity_streams = AsyncMock(return_value=sample_streams)
            async with mcp_client:
                await mcp_client.call_tool(
                    "get_activity_streams",
                    {"activity_id": "99001", "types": "watts,heartrate"},
                )
        call_kwargs = mock_svc.return_value.get_activity_streams.call_args[1]
        assert call_kwargs["types"] == ["watts", "heartrate"]

    async def test_none_types_passes_none(
        self, mcp_client: Client, sample_streams: list[dict]
    ) -> None:
        with patch("intervals_icu_tools.mcp_server._make_service") as mock_svc:
            mock_svc.return_value.get_activity_streams = AsyncMock(return_value=sample_streams)
            async with mcp_client:
                await mcp_client.call_tool(
                    "get_activity_streams", {"activity_id": "99001"}
                )
        call_kwargs = mock_svc.return_value.get_activity_streams.call_args[1]
        assert call_kwargs["types"] is None
