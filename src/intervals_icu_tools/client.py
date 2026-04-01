"""Low-level async HTTP client for the Intervals.ICU REST API.

Handles auth, error mapping, and streaming downloads.
Does not contain business logic — just HTTP mechanics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .config import ApiConfig
from .errors import AuthenticationError, DownloadError, NotFoundError, RateLimitError
from .models import FileDownloadResult


class IntervalsClient:
    def __init__(self, config: ApiConfig) -> None:
        self._base_url = config.base_url
        self._auth = httpx.BasicAuth(username="API_KEY", password=config.api_key)
        self._timeout = config.timeout

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request and return the parsed JSON response."""
        async with self._make_client() as client:
            response = await client.get(path, params=params)
            self._raise_for_status(response)
            return response.json()

    async def put(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Perform a PUT request and return the parsed JSON response."""
        async with self._make_client() as client:
            response = await client.put(path, json=json)
            self._raise_for_status(response)
            return response.json()

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Perform a POST request and return the parsed JSON response."""
        async with self._make_client() as client:
            response = await client.post(path, json=json)
            self._raise_for_status(response)
            return response.json()

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a DELETE request and return the parsed JSON response (if any)."""
        async with self._make_client() as client:
            response = await client.delete(path, params=params)
            self._raise_for_status(response)
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    async def download_file(
        self,
        path: str,
        dest_dir: Path,
        params: dict[str, Any] | None = None,
    ) -> FileDownloadResult:
        """Stream a file download directly to disk.

        Never loads the full response into memory.
        Returns metadata (path, size, content_type, filename).
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        async with self._make_client() as client:
            async with client.stream("GET", path, params=params) as response:
                self._raise_for_status(response)
                content_type = response.headers.get(
                    "content-type", "application/octet-stream"
                )
                filename = (
                    _parse_content_disposition(response.headers)
                    or _filename_from_path(path)
                )
                dest_path = dest_dir / filename
                total = 0
                try:
                    with open(dest_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            total += len(chunk)
                except OSError as e:
                    raise DownloadError(f"Failed to write {dest_path}: {e}") from e
        return FileDownloadResult(
            path=dest_path,
            size_bytes=total,
            content_type=content_type,
            filename=filename,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed (HTTP {response.status_code}). "
                "Check that INTERVALS_API_KEY is set correctly."
            )
        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {response.url}")
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 60))
            raise RateLimitError("Rate limit exceeded", retry_after=retry_after)
        response.raise_for_status()


def _parse_content_disposition(headers: httpx.Headers) -> str | None:
    """Extract filename from Content-Disposition header, if present."""
    cd = headers.get("content-disposition", "")
    if "filename=" in cd:
        filename = cd.split("filename=")[-1].strip().strip('"').strip("'")
        return filename or None
    return None


def _filename_from_path(path: str) -> str:
    """Derive a fallback filename from the URL path."""
    return path.rstrip("/").split("/")[-1] or "download"
