"""Tests for the HTTP client layer."""

from __future__ import annotations

import respx
import httpx
import pytest

from intervals_icu_tools.client import IntervalsClient, _parse_content_disposition, _filename_from_path
from intervals_icu_tools.config import ApiConfig
from intervals_icu_tools.errors import AuthenticationError, NotFoundError, RateLimitError, DownloadError


@pytest.fixture
def config() -> ApiConfig:
    return ApiConfig(api_key="test-key", athlete_id="itest")


@pytest.fixture
def client(config: ApiConfig) -> IntervalsClient:
    return IntervalsClient(config)


class TestGet:
    @respx.mock
    async def test_get_returns_json(self, client: IntervalsClient) -> None:
        respx.get("https://intervals.icu/api/v1/activity/123").mock(
            return_value=httpx.Response(200, json={"id": "123", "name": "Test"})
        )
        result = await client.get("/api/v1/activity/123")
        assert result["id"] == "123"

    @respx.mock
    async def test_get_with_params(self, client: IntervalsClient) -> None:
        route = respx.get("https://intervals.icu/api/v1/athlete/itest/activities").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.get("/api/v1/athlete/itest/activities", params={"oldest": "2024-01-01"})
        assert route.called
        assert "oldest=2024-01-01" in str(route.calls[0].request.url)

    @respx.mock
    async def test_401_raises_auth_error(self, client: IntervalsClient) -> None:
        respx.get("https://intervals.icu/api/v1/activity/bad").mock(
            return_value=httpx.Response(401)
        )
        with pytest.raises(AuthenticationError):
            await client.get("/api/v1/activity/bad")

    @respx.mock
    async def test_403_raises_auth_error(self, client: IntervalsClient) -> None:
        respx.get("https://intervals.icu/api/v1/activity/forbidden").mock(
            return_value=httpx.Response(403)
        )
        with pytest.raises(AuthenticationError):
            await client.get("/api/v1/activity/forbidden")

    @respx.mock
    async def test_404_raises_not_found(self, client: IntervalsClient) -> None:
        respx.get("https://intervals.icu/api/v1/activity/missing").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(NotFoundError):
            await client.get("/api/v1/activity/missing")

    @respx.mock
    async def test_429_raises_rate_limit_with_retry_after(self, client: IntervalsClient) -> None:
        respx.get("https://intervals.icu/api/v1/activity/limited").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "30"})
        )
        with pytest.raises(RateLimitError) as exc_info:
            await client.get("/api/v1/activity/limited")
        assert exc_info.value.retry_after == 30.0

    @respx.mock
    async def test_uses_basic_auth(self, client: IntervalsClient) -> None:
        route = respx.get("https://intervals.icu/api/v1/activity/123").mock(
            return_value=httpx.Response(200, json={"id": "123"})
        )
        await client.get("/api/v1/activity/123")
        auth_header = route.calls[0].request.headers.get("authorization", "")
        assert auth_header.startswith("Basic ")


class TestDownloadFile:
    @respx.mock
    async def test_streams_to_disk(self, client: IntervalsClient, tmp_path) -> None:
        respx.get("https://intervals.icu/api/v1/activity/123/file").mock(
            return_value=httpx.Response(
                200,
                content=b"fake fit content",
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": 'attachment; filename="activity.fit"',
                },
            )
        )
        result = await client.download_file("/api/v1/activity/123/file", dest_dir=tmp_path)
        assert result.filename == "activity.fit"
        assert result.size_bytes == len(b"fake fit content")
        assert result.content_type == "application/octet-stream"
        assert (tmp_path / "activity.fit").exists()
        assert (tmp_path / "activity.fit").read_bytes() == b"fake fit content"

    @respx.mock
    async def test_fallback_filename_from_path(self, client: IntervalsClient, tmp_path) -> None:
        respx.get("https://intervals.icu/api/v1/activity/123/gpx-file").mock(
            return_value=httpx.Response(
                200,
                content=b"<gpx/>",
                headers={"Content-Type": "application/gpx+xml"},
            )
        )
        result = await client.download_file("/api/v1/activity/123/gpx-file", dest_dir=tmp_path)
        assert result.filename == "gpx-file"

    @respx.mock
    async def test_download_401_raises_auth_error(self, client: IntervalsClient, tmp_path) -> None:
        respx.get("https://intervals.icu/api/v1/activity/123/file").mock(
            return_value=httpx.Response(401)
        )
        with pytest.raises(AuthenticationError):
            await client.download_file("/api/v1/activity/123/file", dest_dir=tmp_path)


class TestHelpers:
    def test_parse_content_disposition_filename(self) -> None:
        headers = httpx.Headers({"content-disposition": 'attachment; filename="test.fit"'})
        assert _parse_content_disposition(headers) == "test.fit"

    def test_parse_content_disposition_missing(self) -> None:
        headers = httpx.Headers({})
        assert _parse_content_disposition(headers) is None

    def test_filename_from_path(self) -> None:
        assert _filename_from_path("/api/v1/activity/123/gpx-file") == "gpx-file"
        assert _filename_from_path("/api/v1/activity/123/file") == "file"
