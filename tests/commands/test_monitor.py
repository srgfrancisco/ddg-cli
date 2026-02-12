"""Tests for monitor commands."""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from datadog_api_client.v1.model.monitor_overall_states import MonitorOverallStates
from ddogctl.commands.monitor import monitor


class MockMonitor:
    """Mock Datadog monitor object."""

    def __init__(self, id, name, overall_state, tags=None):
        self.id = id
        self.name = name
        self.overall_state = overall_state
        self.tags = tags or []
        self.type = "metric alert"
        self.query = "avg:system.cpu.user{*}"
        self.message = "Test monitor"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "overall_state": str(self.overall_state),
            "type": self.type,
            "query": self.query,
            "message": self.message,
            "tags": self.tags,
        }


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.monitors = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def test_monitor_list_state_filter(mock_client, runner):
    """Test that monitor list correctly filters by state.

    This test verifies the fix for the bug where state filtering always returned 0 monitors
    because m.overall_state (enum) was compared directly to strings instead of str(m.overall_state).
    """
    # Create monitors with different states
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
        MockMonitor(2, "Warn Monitor", MonitorOverallStates.WARN, tags=["env:staging"]),
        MockMonitor(3, "OK Monitor", MonitorOverallStates.OK, tags=["env:dev"]),
        MockMonitor(4, "Another Alert", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]

    # Mock the API response
    mock_client.monitors.list_monitors.return_value = mock_monitors

    # Patch get_datadog_client to return our mock
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # Test filtering by Alert state only
        result = runner.invoke(monitor, ["list", "--state", "Alert", "--format", "json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Parse JSON output
        import json

        output = json.loads(result.output)

        # Should only return Alert monitors (IDs 1 and 4)
        assert len(output) == 2, f"Expected 2 Alert monitors, got {len(output)}"
        assert output[0]["id"] == 1
        assert output[1]["id"] == 4

        # Test filtering by multiple states (Alert and Warn)
        result = runner.invoke(
            monitor, ["list", "--state", "Alert", "--state", "Warn", "--format", "json"]
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)

        # Should return Alert and Warn monitors (IDs 1, 2, 4)
        assert len(output) == 3, f"Expected 3 Alert/Warn monitors, got {len(output)}"
        monitor_ids = [m["id"] for m in output]
        assert sorted(monitor_ids) == [1, 2, 4]

        # Verify OK monitor (ID 3) was filtered out
        assert 3 not in monitor_ids, "OK monitor should be filtered out"


def test_monitor_list_no_state_filter(mock_client, runner):
    """Test that monitor list without state filter returns all monitors."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
        MockMonitor(2, "OK Monitor", MonitorOverallStates.OK),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        # Should return all monitors
        assert len(output) == 2


# ============================================================================
# Output Format Tests
# ============================================================================


def test_monitor_list_table_format(mock_client, runner):
    """Test monitor list with table format (default)."""
    mock_monitors = [
        MockMonitor(
            1, "Test Monitor", MonitorOverallStates.ALERT, tags=["env:prod", "service:web"]
        ),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "table"])

        assert result.exit_code == 0
        assert "Datadog Monitors" in result.output
        assert "Test Monitor" in result.output
        assert "Total monitors: 1" in result.output


def test_monitor_list_markdown_format(mock_client, runner):
    """Test monitor list with markdown format."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT),
        MockMonitor(2, "Another Monitor", MonitorOverallStates.OK),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "markdown"])

        assert result.exit_code == 0
        # Check markdown table structure
        assert "| ID | State | Name |" in result.output
        assert "|---|---|---|" in result.output
        assert "| 1 |" in result.output
        assert "| 2 |" in result.output
        assert "Test Monitor" in result.output


def test_monitor_list_json_format(mock_client, runner):
    """Test monitor list with JSON format."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]

    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["list", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        assert len(output) == 1
        assert output[0]["id"] == 1
        assert output[0]["name"] == "Test Monitor"
        assert output[0]["tags"] == ["env:prod"]


# ============================================================================
# Monitor Get Command Tests
# ============================================================================


def test_monitor_get_table_format(mock_client, runner):
    """Test getting a single monitor with table format."""
    mock_monitor = MockMonitor(
        123, "CPU Alert Monitor", MonitorOverallStates.ALERT, tags=["env:prod", "service:web"]
    )
    mock_monitor.created = "2024-01-01T00:00:00Z"
    mock_monitor.modified = "2024-01-02T00:00:00Z"

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "123", "--format", "table"])

        assert result.exit_code == 0
        assert "Monitor #123" in result.output
        assert "CPU Alert Monitor" in result.output
        assert "metric alert" in result.output
        assert "avg:system.cpu.user{*}" in result.output
        assert "env:prod" in result.output
        assert "service:web" in result.output


def test_monitor_get_json_format(mock_client, runner):
    """Test getting a single monitor with JSON format."""
    mock_monitor = MockMonitor(456, "Memory Monitor", MonitorOverallStates.OK, tags=["env:staging"])

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "456", "--format", "json"])

        assert result.exit_code == 0

        import json

        output = json.loads(result.output)

        assert output["id"] == 456
        assert output["name"] == "Memory Monitor"
        assert output["type"] == "metric alert"
        assert output["tags"] == ["env:staging"]


def test_monitor_get_without_optional_fields(mock_client, runner):
    """Test getting a monitor that has no created/modified timestamps."""
    mock_monitor = MockMonitor(789, "Simple Monitor", MonitorOverallStates.WARN)

    mock_client.monitors.get_monitor.return_value = mock_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["get", "789"])

        assert result.exit_code == 0
        assert "Simple Monitor" in result.output


# ============================================================================
# Monitor Mute Command Tests
# ============================================================================


def test_monitor_mute_basic(mock_client, runner):
    """Test muting a monitor without additional options."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "123"])

        assert result.exit_code == 0
        assert "Monitor 123 muted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_duration(mock_client, runner):
    """Test muting a monitor with a duration."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "123", "--duration", "3600"])

        assert result.exit_code == 0
        assert "Monitor 123 muted" in result.output
        assert "Muted for 3600 seconds" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_scope(mock_client, runner):
    """Test muting a monitor with a specific scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute", "456", "--scope", "host:myhost"])

        assert result.exit_code == 0
        assert "Monitor 456 muted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_mute_with_duration_and_scope(mock_client, runner):
    """Test muting a monitor with both duration and scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor, ["mute", "789", "--duration", "1800", "--scope", "env:prod"]
        )

        assert result.exit_code == 0
        assert "Monitor 789 muted" in result.output
        assert "Muted for 1800 seconds" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


# ============================================================================
# Monitor Unmute Command Tests
# ============================================================================


def test_monitor_unmute_basic(mock_client, runner):
    """Test unmuting a monitor without additional options."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute", "123"])

        assert result.exit_code == 0
        assert "Monitor 123 unmuted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_unmute_with_scope(mock_client, runner):
    """Test unmuting a monitor with a specific scope."""
    mock_client.monitors.update_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute", "456", "--scope", "host:myhost"])

        assert result.exit_code == 0
        assert "Monitor 456 unmuted" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


# ============================================================================
# Monitor Validate Command Tests
# ============================================================================


class MockValidationResult:
    """Mock validation result object."""

    def __init__(self, has_errors=False):
        if has_errors:
            self.errors = ["Invalid query syntax", "Missing required field"]
        else:
            self.errors = None


def test_monitor_validate_valid_definition(mock_client, runner):
    """Test validating a valid monitor definition."""
    mock_client.monitors.validate_monitor.return_value = MockValidationResult(has_errors=False)

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            ["validate", "--type", "metric alert", "--query", "avg:system.cpu.user{*} > 80"],
        )

        assert result.exit_code == 0
        assert "Monitor definition is valid" in result.output
        mock_client.monitors.validate_monitor.assert_called_once()


def test_monitor_validate_invalid_definition(mock_client, runner):
    """Test validating an invalid monitor definition."""
    mock_client.monitors.validate_monitor.return_value = MockValidationResult(has_errors=True)

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor, ["validate", "--type", "metric alert", "--query", "invalid query syntax"]
        )

        assert result.exit_code == 1  # Should exit with error code
        assert "Monitor definition is invalid" in result.output
        assert "Invalid query syntax" in result.output
        assert "Missing required field" in result.output


def test_monitor_validate_missing_required_args(mock_client, runner):
    """Test validate command without required arguments."""
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # Missing --query
        result = runner.invoke(monitor, ["validate", "--type", "metric alert"])
        assert result.exit_code != 0

        # Missing --type
        result = runner.invoke(monitor, ["validate", "--query", "avg:system.cpu{*}"])
        assert result.exit_code != 0


# ============================================================================
# Integration Tests (Multiple Commands)
# ============================================================================


def test_monitor_workflow_list_get(mock_client, runner):
    """Test workflow: list monitors, then get details of one."""
    # Setup for list
    mock_monitors = [
        MockMonitor(1, "Monitor A", MonitorOverallStates.ALERT),
        MockMonitor(2, "Monitor B", MonitorOverallStates.OK),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    # Setup for get
    mock_single = MockMonitor(1, "Monitor A", MonitorOverallStates.ALERT)
    mock_client.monitors.get_monitor.return_value = mock_single

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # First list all monitors
        result = runner.invoke(monitor, ["list", "--format", "json"])
        assert result.exit_code == 0

        import json

        monitors_list = json.loads(result.output)
        assert len(monitors_list) == 2

        # Then get details of the first one
        result = runner.invoke(monitor, ["get", "1", "--format", "json"])
        assert result.exit_code == 0

        monitor_details = json.loads(result.output)
        assert monitor_details["id"] == 1
        assert monitor_details["name"] == "Monitor A"


# ============================================================================
# Monitor Create Command Tests
# ============================================================================


def test_monitor_create_with_inline_flags(mock_client, runner):
    """Test creating a monitor with inline flags."""
    created_monitor = MockMonitor(100, "CPU Alert", MonitorOverallStates.OK)
    mock_client.monitors.create_monitor.return_value = created_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            [
                "create",
                "--type",
                "metric alert",
                "--query",
                "avg:system.cpu.user{*} > 80",
                "--name",
                "CPU Alert",
                "--message",
                "CPU is high",
                "--tags",
                "env:prod,service:web",
                "--priority",
                "3",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 100 created" in result.output
        mock_client.monitors.create_monitor.assert_called_once()

        # Verify the Monitor body was passed correctly
        call_kwargs = mock_client.monitors.create_monitor.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert str(body.type) == "metric alert"
        assert body.query == "avg:system.cpu.user{*} > 80"
        assert body.name == "CPU Alert"
        assert body.message == "CPU is high"
        assert body.tags == ["env:prod", "service:web"]
        assert body.priority == 3


def test_monitor_create_with_minimal_flags(mock_client, runner):
    """Test creating a monitor with only required flags."""
    created_monitor = MockMonitor(101, "Test", MonitorOverallStates.OK)
    mock_client.monitors.create_monitor.return_value = created_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            [
                "create",
                "--type",
                "metric alert",
                "--query",
                "avg:system.cpu.user{*} > 80",
                "--name",
                "Test",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 101 created" in result.output
        mock_client.monitors.create_monitor.assert_called_once()


def test_monitor_create_missing_required_flags(mock_client, runner):
    """Test that create fails when required flags are missing."""
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        # Missing --type
        result = runner.invoke(
            monitor,
            ["create", "--query", "avg:system.cpu.user{*} > 80", "--name", "Test"],
        )
        assert result.exit_code != 0

        # Missing --query
        result = runner.invoke(
            monitor,
            ["create", "--type", "metric alert", "--name", "Test"],
        )
        assert result.exit_code != 0

        # Missing --name
        result = runner.invoke(
            monitor,
            ["create", "--type", "metric alert", "--query", "avg:system.cpu.user{*} > 80"],
        )
        assert result.exit_code != 0


def test_monitor_create_from_file(mock_client, runner, tmp_path):
    """Test creating a monitor from a JSON file."""
    monitor_def = {
        "type": "metric alert",
        "query": "avg:system.cpu.user{*} > 90",
        "name": "High CPU from file",
        "message": "CPU is very high",
        "tags": ["env:prod"],
        "priority": 2,
    }
    json_file = tmp_path / "monitor.json"
    json_file.write_text(json.dumps(monitor_def))

    created_monitor = MockMonitor(102, "High CPU from file", MonitorOverallStates.OK)
    mock_client.monitors.create_monitor.return_value = created_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["create", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 102 created" in result.output
        mock_client.monitors.create_monitor.assert_called_once()


def test_monitor_create_from_file_overrides_flags(mock_client, runner, tmp_path):
    """Test that -f flag takes precedence over inline flags."""
    monitor_def = {
        "type": "metric alert",
        "query": "avg:system.mem.used{*} > 90",
        "name": "Memory from file",
    }
    json_file = tmp_path / "monitor.json"
    json_file.write_text(json.dumps(monitor_def))

    created_monitor = MockMonitor(103, "Memory from file", MonitorOverallStates.OK)
    mock_client.monitors.create_monitor.return_value = created_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            [
                "create",
                "-f",
                str(json_file),
                "--type",
                "log alert",
                "--query",
                "ignored",
                "--name",
                "ignored",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # The file data should be used, not the flags
        call_kwargs = mock_client.monitors.create_monitor.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.name == "Memory from file"


def test_monitor_create_from_invalid_file(mock_client, runner, tmp_path):
    """Test creating a monitor from an invalid JSON file."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("not valid json {{{")

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["create", "-f", str(json_file)])

        assert result.exit_code != 0


def test_monitor_create_from_nonexistent_file(mock_client, runner):
    """Test creating a monitor from a file that doesn't exist."""
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["create", "-f", "/nonexistent/path.json"])

        assert result.exit_code != 0


def test_monitor_create_json_output(mock_client, runner):
    """Test creating a monitor with JSON output format."""
    created_monitor = MockMonitor(104, "JSON Test", MonitorOverallStates.OK)
    mock_client.monitors.create_monitor.return_value = created_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            [
                "create",
                "--type",
                "metric alert",
                "--query",
                "avg:system.cpu.user{*} > 80",
                "--name",
                "JSON Test",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 104
        assert output["name"] == "JSON Test"


# ============================================================================
# Monitor Update Command Tests
# ============================================================================


def test_monitor_update_with_inline_flags(mock_client, runner):
    """Test updating a monitor with inline flags."""
    updated_monitor = MockMonitor(200, "Updated CPU Alert", MonitorOverallStates.OK)
    mock_client.monitors.update_monitor.return_value = updated_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            [
                "update",
                "200",
                "--name",
                "Updated CPU Alert",
                "--query",
                "avg:system.cpu.user{*} > 90",
                "--message",
                "Updated message",
                "--tags",
                "env:prod,team:sre",
                "--priority",
                "1",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 200 updated" in result.output
        mock_client.monitors.update_monitor.assert_called_once()

        # Verify monitor_id and body
        call_args = mock_client.monitors.update_monitor.call_args
        assert call_args[0][0] == 200  # monitor_id


def test_monitor_update_partial_flags(mock_client, runner):
    """Test updating a monitor with only some flags."""
    updated_monitor = MockMonitor(201, "Partially Updated", MonitorOverallStates.OK)
    mock_client.monitors.update_monitor.return_value = updated_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            ["update", "201", "--name", "Partially Updated"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 201 updated" in result.output


def test_monitor_update_from_file(mock_client, runner, tmp_path):
    """Test updating a monitor from a JSON file."""
    monitor_def = {
        "name": "Updated from file",
        "query": "avg:system.mem.used{*} > 95",
        "tags": ["env:staging"],
    }
    json_file = tmp_path / "update.json"
    json_file.write_text(json.dumps(monitor_def))

    updated_monitor = MockMonitor(202, "Updated from file", MonitorOverallStates.OK)
    mock_client.monitors.update_monitor.return_value = updated_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["update", "202", "-f", str(json_file)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 202 updated" in result.output
        mock_client.monitors.update_monitor.assert_called_once()


def test_monitor_update_json_output(mock_client, runner):
    """Test updating a monitor with JSON output format."""
    updated_monitor = MockMonitor(203, "JSON Update", MonitorOverallStates.OK)
    mock_client.monitors.update_monitor.return_value = updated_monitor

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            monitor,
            ["update", "203", "--name", "JSON Update", "--format", "json"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = json.loads(result.output)
        assert output["id"] == 203


# ============================================================================
# Monitor Delete Command Tests
# ============================================================================


def test_monitor_delete_with_confirm_flag(mock_client, runner):
    """Test deleting a monitor with --confirm flag (no prompt)."""
    mock_client.monitors.delete_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["delete", "300", "--confirm"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 300 deleted" in result.output
        mock_client.monitors.delete_monitor.assert_called_once_with(300)


def test_monitor_delete_interactive_confirm_yes(mock_client, runner):
    """Test deleting a monitor with interactive confirmation (user says yes)."""
    mock_client.monitors.delete_monitor.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["delete", "301"], input="y\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Monitor 301 deleted" in result.output
        mock_client.monitors.delete_monitor.assert_called_once_with(301)


def test_monitor_delete_interactive_confirm_no(mock_client, runner):
    """Test deleting a monitor with interactive confirmation (user says no)."""
    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["delete", "302"], input="n\n")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Aborted" in result.output
        mock_client.monitors.delete_monitor.assert_not_called()


# ============================================================================
# Monitor Mute-All Command Tests
# ============================================================================


def test_monitor_mute_all(mock_client, runner):
    """Test muting all monitors by creating a global downtime."""
    mock_downtime = Mock()
    mock_downtime.id = 5000
    mock_client.downtimes = Mock()
    mock_client.downtimes.create_downtime.return_value = mock_downtime

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute-all"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "All monitors muted" in result.output
        mock_client.downtimes.create_downtime.assert_called_once()

        # Verify the downtime scope is "*"
        call_kwargs = mock_client.downtimes.create_downtime.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.scope == ["*"]


def test_monitor_mute_all_with_message(mock_client, runner):
    """Test muting all monitors with a custom message."""
    mock_downtime = Mock()
    mock_downtime.id = 5001
    mock_client.downtimes = Mock()
    mock_client.downtimes.create_downtime.return_value = mock_downtime

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["mute-all", "--message", "Maintenance window"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "All monitors muted" in result.output

        call_kwargs = mock_client.downtimes.create_downtime.call_args
        body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
        assert body.message == "Maintenance window"


# ============================================================================
# Monitor Unmute-All Command Tests
# ============================================================================


def test_monitor_unmute_all(mock_client, runner):
    """Test unmuting all monitors by cancelling global downtimes."""
    mock_downtime_active = Mock()
    mock_downtime_active.id = 6000
    mock_downtime_active.scope = ["*"]
    mock_downtime_active.disabled = False

    mock_downtime_other = Mock()
    mock_downtime_other.id = 6001
    mock_downtime_other.scope = ["host:myhost"]
    mock_downtime_other.disabled = False

    mock_client.downtimes = Mock()
    mock_client.downtimes.list_downtimes.return_value = [
        mock_downtime_active,
        mock_downtime_other,
    ]
    mock_client.downtimes.cancel_downtime.return_value = Mock()

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute-all"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "All monitors unmuted" in result.output
        # Should only cancel the global downtime (scope ["*"]), not the host-specific one
        mock_client.downtimes.cancel_downtime.assert_called_once_with(6000)


def test_monitor_unmute_all_no_global_downtimes(mock_client, runner):
    """Test unmuting when there are no global downtimes."""
    mock_client.downtimes = Mock()
    mock_client.downtimes.list_downtimes.return_value = []

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        result = runner.invoke(monitor, ["unmute-all"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "No global downtimes found" in result.output
        mock_client.downtimes.cancel_downtime.assert_not_called()


# ============================================================================
# Monitor List --watch Tests
# ============================================================================


def test_monitor_list_watch_flag_accepted(mock_client, runner):
    """Test that --watch flag is accepted by the monitor list command."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop"):
            result = runner.invoke(monitor, ["list", "--watch"])

            # Should not fail with unrecognized option
            assert result.exit_code == 0


def test_monitor_list_watch_with_interval(mock_client, runner):
    """Test that --interval flag is accepted alongside --watch."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--watch", "--interval", "10"])

            assert result.exit_code == 0
            # watch_loop should be called with the specified interval
            mock_watch.assert_called_once()
            call_kwargs = mock_watch.call_args
            assert call_kwargs[1]["interval"] == 10


def test_monitor_list_watch_calls_watch_loop(mock_client, runner):
    """Test that --watch triggers watch_loop with a render function."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--watch"])

            assert result.exit_code == 0
            mock_watch.assert_called_once()
            # First arg should be a callable (render function)
            render_func = mock_watch.call_args[0][0]
            assert callable(render_func)


def test_monitor_list_watch_default_interval(mock_client, runner):
    """Test that --watch defaults to 30 second interval."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--watch"])

            assert result.exit_code == 0
            call_kwargs = mock_watch.call_args
            assert call_kwargs[1]["interval"] == 30


def test_monitor_list_without_watch_runs_normally(mock_client, runner):
    """Test that without --watch, the command runs once and exits."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT, tags=["env:prod"]),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--format", "table"])

            assert result.exit_code == 0
            # watch_loop should NOT be called
            mock_watch.assert_not_called()
            assert "Datadog Monitors" in result.output


def test_monitor_list_watch_with_state_filter(mock_client, runner):
    """Test that --watch works alongside --state filter."""
    mock_monitors = [
        MockMonitor(1, "Alert Monitor", MonitorOverallStates.ALERT),
        MockMonitor(2, "OK Monitor", MonitorOverallStates.OK),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--state", "Alert", "--watch"])

            assert result.exit_code == 0
            mock_watch.assert_called_once()


def test_monitor_list_interval_without_watch(mock_client, runner):
    """Test that --interval without --watch is ignored (runs normally)."""
    mock_monitors = [
        MockMonitor(1, "Test Monitor", MonitorOverallStates.ALERT),
    ]
    mock_client.monitors.list_monitors.return_value = mock_monitors

    with patch("ddogctl.commands.monitor.get_datadog_client", return_value=mock_client):
        with patch("ddogctl.commands.monitor.watch_loop") as mock_watch:
            result = runner.invoke(monitor, ["list", "--interval", "10", "--format", "table"])

            assert result.exit_code == 0
            mock_watch.assert_not_called()
            assert "Datadog Monitors" in result.output
