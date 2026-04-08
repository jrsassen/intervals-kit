"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import respx
import httpx
from click.testing import CliRunner

from intervals_kit.cli import cli
from intervals_kit.errors import AuthenticationError, RateLimitError, NotFoundError, DownloadError
from intervals_kit.models import Activity, ActivitySearchResult, FileDownloadResult


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner: CliRunner, args: list[str]) -> object:
    """Invoke CLI with INTERVALS_* env vars set."""
    return runner.invoke(
        cli,
        args,
        env={"INTERVALS_API_KEY": "test-key", "INTERVALS_ATHLETE_ID": "itest"},
        catch_exceptions=False,
    )


class TestListActivities:
    def test_success_prints_json(
        self, runner: CliRunner, sample_activities: list[dict]
    ) -> None:
        activities = [Activity.model_validate(a) for a in sample_activities]
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.list_activities = AsyncMock(return_value=activities)
            result = _invoke(runner, ["list-activities", "--oldest", "2024-01-01", "--newest", "2024-12-31"])
        assert result.exit_code == 0
        assert "Morning Ride" in result.output

    def test_auth_error_exits_1(self, runner: CliRunner) -> None:
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.list_activities = AsyncMock(
                side_effect=AuthenticationError("Bad key")
            )
            result = runner.invoke(
                cli,
                ["list-activities", "--oldest", "2024-01-01", "--newest", "2024-12-31"],
                env={"INTERVALS_API_KEY": "bad-key", "INTERVALS_ATHLETE_ID": "itest"},
            )
        assert result.exit_code == 1

    def test_rate_limit_exits_2(self, runner: CliRunner) -> None:
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.list_activities = AsyncMock(
                side_effect=RateLimitError("Limited", retry_after=10.0)
            )
            result = runner.invoke(
                cli,
                ["list-activities", "--oldest", "2024-01-01", "--newest", "2024-12-31"],
                env={"INTERVALS_API_KEY": "test", "INTERVALS_ATHLETE_ID": "itest"},
            )
        assert result.exit_code == 2

    def test_saves_to_file_with_output_dir(
        self, runner: CliRunner, sample_activities: list[dict], tmp_path: Path
    ) -> None:
        activities = [Activity.model_validate(a) for a in sample_activities]
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.list_activities = AsyncMock(return_value=activities)
            result = _invoke(runner, [
                "-o", str(tmp_path),
                "list-activities", "--oldest", "2024-01-01", "--newest", "2024-12-31",
            ])
        assert result.exit_code == 0
        saved_files = list(tmp_path.glob("activities_*.json"))
        assert len(saved_files) == 1


class TestGetActivity:
    def test_prints_activity_json(
        self, runner: CliRunner, sample_activity: dict
    ) -> None:
        activity = Activity.model_validate(sample_activity)
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.get_activity = AsyncMock(return_value=activity)
            result = _invoke(runner, ["get-activity", "99001"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "99001"

    def test_not_found_exits_4(self, runner: CliRunner) -> None:
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.get_activity = AsyncMock(
                side_effect=NotFoundError("Not found")
            )
            result = runner.invoke(
                cli,
                ["get-activity", "99999"],
                env={"INTERVALS_API_KEY": "test", "INTERVALS_ATHLETE_ID": "itest"},
            )
        assert result.exit_code == 4


class TestSearchActivities:
    def test_success(self, runner: CliRunner, sample_activities: list[dict]) -> None:
        results = [ActivitySearchResult.model_validate(a) for a in sample_activities]
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.search_activities = AsyncMock(return_value=results)
            result = _invoke(runner, ["search-activities", "ride"])
        assert result.exit_code == 0


class TestUpdateActivity:
    def test_success_with_name(
        self, runner: CliRunner, sample_activity: dict
    ) -> None:
        updated = Activity.model_validate({**sample_activity, "name": "Updated"})
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.update_activity = AsyncMock(return_value=updated)
            result = _invoke(runner, ["update-activity", "99001", "--name", "Updated"])
        assert result.exit_code == 0

    def test_no_fields_exits_1(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli,
            ["update-activity", "99001"],
            env={"INTERVALS_API_KEY": "test", "INTERVALS_ATHLETE_ID": "itest"},
        )
        assert result.exit_code == 1


class TestDownloadActivityFile:
    def test_download_success_prints_path_and_size(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        fake_file = tmp_path / "activity.fit"
        fake_file.write_bytes(b"fake content")
        mock_result = FileDownloadResult(
            path=fake_file,
            size_bytes=12,
            content_type="application/octet-stream",
            filename="activity.fit",
        )
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.download_activity_file = AsyncMock(return_value=mock_result)
            result = _invoke(runner, [
                "-o", str(tmp_path),
                "download-activity-file", "99001", "--type", "fit",
            ])
        assert result.exit_code == 0
        assert "Downloaded:" in result.output
        assert "12" in result.output

    def test_download_error_exits_3(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("intervals_kit.cli.commands.IntervalsService") as MockSvc:
            MockSvc.return_value.download_activity_file = AsyncMock(
                side_effect=DownloadError("Network failure")
            )
            result = runner.invoke(
                cli,
                ["-o", str(tmp_path), "download-activity-file", "99001"],
                env={"INTERVALS_API_KEY": "test", "INTERVALS_ATHLETE_ID": "itest"},
            )
        assert result.exit_code == 3


class TestMissingCredentials:
    def test_missing_api_key_exits_nonzero(self, runner: CliRunner) -> None:
        """Without credentials, config loading raises an error."""
        result = runner.invoke(
            cli,
            ["list-activities", "--oldest", "2024-01-01", "--newest", "2024-12-31"],
            env={"INTERVALS_API_KEY": "", "INTERVALS_ATHLETE_ID": ""},
        )
        # Config raises ValueError which Click propagates as exit code 1
        assert result.exit_code != 0
