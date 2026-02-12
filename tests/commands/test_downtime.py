"""Tests for downtime management commands."""

import json
import time
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.downtime import downtime, parse_downtime_time

# ============================================================================
# parse_downtime_time Tests
# ============================================================================


class TestParseDowntimeTime:
    """Tests for the parse_downtime_time helper."""

    def test_now(self):
        """'now' returns current Unix timestamp."""
        before = int(time.time())
        result = parse_downtime_time("now")
        after = int(time.time())
        assert before <= result <= after

    def test_relative_hours(self):
        """Relative hours like '2h' returns current time + offset."""
        before = int(time.time()) + 2 * 3600
        result = parse_downtime_time("2h")
        after = int(time.time()) + 2 * 3600
        assert before <= result <= after

    def test_relative_minutes(self):
        """Relative minutes like '30m' returns current time + offset."""
        before = int(time.time()) + 30 * 60
        result = parse_downtime_time("30m")
        after = int(time.time()) + 30 * 60
        assert before <= result <= after

    def test_relative_days(self):
        """Relative days like '1d' returns current time + offset."""
        before = int(time.time()) + 86400
        result = parse_downtime_time("1d")
        after = int(time.time()) + 86400
        assert before <= result <= after

    def test_iso_datetime(self):
        """ISO datetime string is parsed to Unix timestamp."""
        result = parse_downtime_time("2025-06-15T10:00:00")
        from datetime import datetime

        expected = int(datetime.fromisoformat("2025-06-15T10:00:00").timestamp())
        assert result == expected

    def test_invalid_format_raises(self):
        """Invalid time format raises ValueError."""
        with pytest.raises(ValueError):
            parse_downtime_time("invalid")


# ============================================================================
# Downtime List Command Tests
# ============================================================================


class TestDowntimeList:
    """Tests for downtime list command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _make_downtime(
        self, id, scope, message="", start=None, end=None, disabled=False, monitor_id=None
    ):
        """Create a mock downtime object."""
        dt = Mock()
        dt.id = id
        dt.scope = scope
        dt.message = message
        dt.start = start or int(time.time())
        dt.end = end
        dt.disabled = disabled
        dt.monitor_id = monitor_id
        dt.to_dict = Mock(
            return_value={
                "id": id,
                "scope": scope,
                "message": message,
                "start": dt.start,
                "end": end,
                "disabled": disabled,
                "monitor_id": monitor_id,
            }
        )
        return dt

    def test_list_table_format(self, mock_client, runner):
        """Test listing downtimes in table format."""
        downtimes = [
            self._make_downtime(1, ["env:prod"], "Deploy v2.5"),
            self._make_downtime(2, ["env:staging"], "Testing"),
        ]
        mock_client.downtimes.list_downtimes.return_value = downtimes

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtimes" in result.output
        assert "env:prod" in result.output
        assert "env:staging" in result.output

    def test_list_json_format(self, mock_client, runner):
        """Test listing downtimes in JSON format."""
        downtimes = [
            self._make_downtime(1, ["env:prod"], "Deploy v2.5"),
        ]
        mock_client.downtimes.list_downtimes.return_value = downtimes

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["list", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["id"] == 1

    def test_list_current_only(self, mock_client, runner):
        """Test listing only currently active downtimes."""
        downtimes = [
            self._make_downtime(1, ["env:prod"]),
        ]
        mock_client.downtimes.list_downtimes.return_value = downtimes

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["list", "--current-only"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_client.downtimes.list_downtimes.assert_called_once_with(current_only=True)

    def test_list_without_current_only(self, mock_client, runner):
        """Test listing all downtimes (no current_only flag)."""
        mock_client.downtimes.list_downtimes.return_value = []

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["list"])

        assert result.exit_code == 0
        mock_client.downtimes.list_downtimes.assert_called_once_with()

    def test_list_empty(self, mock_client, runner):
        """Test listing when no downtimes exist."""
        mock_client.downtimes.list_downtimes.return_value = []

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["list"])

        assert result.exit_code == 0
        assert "Total downtimes: 0" in result.output


# ============================================================================
# Downtime Get Command Tests
# ============================================================================


class TestDowntimeGet:
    """Tests for downtime get command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_get_table_format(self, mock_client, runner):
        """Test getting a downtime in table format."""
        dt = Mock()
        dt.id = 123
        dt.scope = ["env:prod"]
        dt.message = "Deploying v2.5"
        dt.start = 1700000000
        dt.end = 1700007200
        dt.disabled = False
        dt.monitor_id = 456

        mock_client.downtimes.get_downtime.return_value = dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["get", "123"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime #123" in result.output
        assert "env:prod" in result.output
        assert "Deploying v2.5" in result.output
        mock_client.downtimes.get_downtime.assert_called_once_with(123)

    def test_get_json_format(self, mock_client, runner):
        """Test getting a downtime in JSON format."""
        dt = Mock()
        dt.id = 456
        dt.scope = ["env:staging"]
        dt.message = "Testing"
        dt.start = 1700000000
        dt.end = None
        dt.disabled = False
        dt.monitor_id = None
        dt.to_dict = Mock(
            return_value={
                "id": 456,
                "scope": ["env:staging"],
                "message": "Testing",
                "start": 1700000000,
                "end": None,
                "disabled": False,
                "monitor_id": None,
            }
        )

        mock_client.downtimes.get_downtime.return_value = dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["get", "456", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 456
        assert output["scope"] == ["env:staging"]


# ============================================================================
# Downtime Create Command Tests
# ============================================================================


class TestDowntimeCreate:
    """Tests for downtime create command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_create_with_inline_flags(self, mock_client, runner):
        """Test creating a downtime with inline flags."""
        created_dt = Mock()
        created_dt.id = 100
        created_dt.scope = ["env:prod"]
        created_dt.message = "Deploying v2.5"
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "--scope",
                    "env:prod",
                    "--start",
                    "now",
                    "--end",
                    "2h",
                    "--message",
                    "Deploying v2.5",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 100 created" in result.output
        mock_client.downtimes.create_downtime.assert_called_once()

    def test_create_with_monitor_id(self, mock_client, runner):
        """Test creating a downtime scoped to a specific monitor."""
        created_dt = Mock()
        created_dt.id = 101
        created_dt.scope = ["env:prod"]
        created_dt.message = "Monitor-specific downtime"
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "--scope",
                    "env:prod",
                    "--start",
                    "now",
                    "--end",
                    "1h",
                    "--message",
                    "Monitor-specific downtime",
                    "--monitor-id",
                    "789",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 101 created" in result.output

        # Verify monitor_id was passed
        call_kwargs = mock_client.downtimes.create_downtime.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.monitor_id == 789

    def test_create_missing_scope(self, mock_client, runner):
        """Test that create fails when --scope is missing and no file provided."""
        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "--start",
                    "now",
                    "--end",
                    "2h",
                ],
            )

        assert result.exit_code != 0

    def test_create_from_file(self, mock_client, runner, tmp_path):
        """Test creating a downtime from a JSON file."""
        downtime_def = {
            "scope": ["env:prod"],
            "start": 1700000000,
            "end": 1700007200,
            "message": "From file",
        }
        json_file = tmp_path / "downtime.json"
        json_file.write_text(json.dumps(downtime_def))

        created_dt = Mock()
        created_dt.id = 102
        created_dt.scope = ["env:prod"]
        created_dt.message = "From file"
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["create", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 102 created" in result.output
        mock_client.downtimes.create_downtime.assert_called_once()

    def test_create_from_file_overrides_flags(self, mock_client, runner, tmp_path):
        """Test that -f flag takes precedence over inline flags."""
        downtime_def = {
            "scope": ["env:staging"],
            "start": 1700000000,
            "end": 1700007200,
            "message": "File wins",
        }
        json_file = tmp_path / "downtime.json"
        json_file.write_text(json.dumps(downtime_def))

        created_dt = Mock()
        created_dt.id = 103
        created_dt.scope = ["env:staging"]
        created_dt.message = "File wins"
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "-f",
                    str(json_file),
                    "--scope",
                    "env:prod",
                    "--message",
                    "Ignored",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        call_kwargs = mock_client.downtimes.create_downtime.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.scope == ["env:staging"]

    def test_create_json_output(self, mock_client, runner):
        """Test creating a downtime with JSON output format."""
        created_dt = Mock()
        created_dt.id = 104
        created_dt.scope = ["env:prod"]
        created_dt.message = "Deploy"
        created_dt.to_dict = Mock(
            return_value={
                "id": 104,
                "scope": ["env:prod"],
                "message": "Deploy",
            }
        )
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "--scope",
                    "env:prod",
                    "--start",
                    "now",
                    "--end",
                    "2h",
                    "--message",
                    "Deploy",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 104

    def test_create_scope_is_list(self, mock_client, runner):
        """Test that scope is passed as a list to the API."""
        created_dt = Mock()
        created_dt.id = 105
        created_dt.scope = ["env:prod"]
        created_dt.message = ""
        mock_client.downtimes.create_downtime.return_value = created_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "create",
                    "--scope",
                    "env:prod",
                    "--start",
                    "now",
                    "--end",
                    "1h",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        call_kwargs = mock_client.downtimes.create_downtime.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.scope == ["env:prod"]


# ============================================================================
# Downtime Update Command Tests
# ============================================================================


class TestDowntimeUpdate:
    """Tests for downtime update command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_update_end_time(self, mock_client, runner):
        """Test updating the end time of a downtime."""
        updated_dt = Mock()
        updated_dt.id = 200
        updated_dt.scope = ["env:prod"]
        updated_dt.message = "Extended maintenance"
        mock_client.downtimes.update_downtime.return_value = updated_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "update",
                    "200",
                    "--end",
                    "4h",
                    "--message",
                    "Extended maintenance",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 200 updated" in result.output
        mock_client.downtimes.update_downtime.assert_called_once()

        # Verify downtime_id was passed correctly
        call_args = mock_client.downtimes.update_downtime.call_args
        assert call_args[0][0] == 200

    def test_update_message_only(self, mock_client, runner):
        """Test updating only the message of a downtime."""
        updated_dt = Mock()
        updated_dt.id = 201
        updated_dt.scope = ["env:prod"]
        updated_dt.message = "New message"
        mock_client.downtimes.update_downtime.return_value = updated_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "update",
                    "201",
                    "--message",
                    "New message",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 201 updated" in result.output

    def test_update_no_fields_errors(self, mock_client, runner):
        """Test that update without any fields gives an error."""
        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["update", "202"])

        assert result.exit_code != 0

    def test_update_json_output(self, mock_client, runner):
        """Test updating a downtime with JSON output format."""
        updated_dt = Mock()
        updated_dt.id = 203
        updated_dt.to_dict = Mock(
            return_value={
                "id": 203,
                "scope": ["env:prod"],
                "message": "Updated",
            }
        )
        mock_client.downtimes.update_downtime.return_value = updated_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "update",
                    "203",
                    "--message",
                    "Updated",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 203

    def test_update_scope(self, mock_client, runner):
        """Test updating the scope of a downtime."""
        updated_dt = Mock()
        updated_dt.id = 204
        updated_dt.scope = ["env:staging"]
        updated_dt.message = ""
        mock_client.downtimes.update_downtime.return_value = updated_dt

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "update",
                    "204",
                    "--scope",
                    "env:staging",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 204 updated" in result.output


# ============================================================================
# Downtime Delete Command Tests
# ============================================================================


class TestDowntimeDelete:
    """Tests for downtime delete command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_delete_with_confirm_flag(self, mock_client, runner):
        """Test deleting a downtime with --confirm flag (no prompt)."""
        mock_client.downtimes.cancel_downtime.return_value = None

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["delete", "300", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 300 cancelled" in result.output
        mock_client.downtimes.cancel_downtime.assert_called_once_with(300)

    def test_delete_interactive_confirm_yes(self, mock_client, runner):
        """Test deleting a downtime with interactive confirmation (user says yes)."""
        mock_client.downtimes.cancel_downtime.return_value = None

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["delete", "301"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Downtime 301 cancelled" in result.output
        mock_client.downtimes.cancel_downtime.assert_called_once_with(301)

    def test_delete_interactive_confirm_no(self, mock_client, runner):
        """Test deleting a downtime with interactive confirmation (user says no)."""
        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["delete", "302"], input="n\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Aborted" in result.output
        mock_client.downtimes.cancel_downtime.assert_not_called()


# ============================================================================
# Downtime Cancel-by-Scope Command Tests
# ============================================================================


class TestDowntimeCancelByScope:
    """Tests for downtime cancel-by-scope command."""

    @pytest.fixture
    def mock_client(self):
        client = Mock()
        client.downtimes = Mock()
        return client

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cancel_by_scope(self, mock_client, runner):
        """Test cancelling downtimes by scope."""
        cancel_result = Mock()
        cancel_result.cancelled_ids = [1, 2, 3]
        mock_client.downtimes.cancel_downtimes_by_scope.return_value = cancel_result

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["cancel-by-scope", "env:prod", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "cancelled" in result.output.lower()
        mock_client.downtimes.cancel_downtimes_by_scope.assert_called_once()

    def test_cancel_by_scope_interactive_confirm_yes(self, mock_client, runner):
        """Test cancel-by-scope with interactive confirmation (user says yes)."""
        cancel_result = Mock()
        cancel_result.cancelled_ids = [10]
        mock_client.downtimes.cancel_downtimes_by_scope.return_value = cancel_result

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["cancel-by-scope", "env:staging"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "cancelled" in result.output.lower()

    def test_cancel_by_scope_interactive_confirm_no(self, mock_client, runner):
        """Test cancel-by-scope with interactive confirmation (user says no)."""
        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(downtime, ["cancel-by-scope", "env:prod"], input="n\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Aborted" in result.output
        mock_client.downtimes.cancel_downtimes_by_scope.assert_not_called()

    def test_cancel_by_scope_json_output(self, mock_client, runner):
        """Test cancel-by-scope with JSON output."""
        cancel_result = Mock()
        cancel_result.cancelled_ids = [5, 6]
        mock_client.downtimes.cancel_downtimes_by_scope.return_value = cancel_result

        with patch("ddogctl.commands.downtime.get_datadog_client", return_value=mock_client):
            result = runner.invoke(
                downtime,
                [
                    "cancel-by-scope",
                    "env:prod",
                    "--confirm",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["cancelled_ids"] == [5, 6]
