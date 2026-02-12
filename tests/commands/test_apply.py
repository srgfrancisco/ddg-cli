"""Tests for apply and diff commands."""

import json
import os
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ddogctl.commands.apply import apply_cmd, diff_cmd, detect_resource_type


@pytest.fixture
def mock_client():
    """Create a mock Datadog client."""
    client = Mock()
    client.monitors = Mock()
    client.dashboards = Mock()
    client.slos = Mock()
    client.downtimes = Mock()
    return client


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


# ============================================================================
# detect_resource_type tests
# ============================================================================


class TestDetectResourceType:
    """Tests for resource type auto-detection from JSON structure."""

    def test_detect_monitor_with_query(self):
        data = {"name": "CPU Alert", "type": "metric alert", "query": "avg:system.cpu{*} > 90"}
        assert detect_resource_type(data) == "monitor"

    def test_detect_dashboard_with_layout_type(self):
        data = {"title": "My Dashboard", "layout_type": "ordered", "widgets": []}
        assert detect_resource_type(data) == "dashboard"

    def test_detect_dashboard_with_widgets_only(self):
        data = {"title": "My Dashboard", "widgets": [{"type": "timeseries"}]}
        assert detect_resource_type(data) == "dashboard"

    def test_detect_slo_metric_type(self):
        data = {
            "name": "API Availability",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
        }
        assert detect_resource_type(data) == "slo"

    def test_detect_slo_monitor_type(self):
        data = {
            "name": "API Availability",
            "type": "monitor",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
        }
        assert detect_resource_type(data) == "slo"

    def test_detect_downtime_with_scope_list(self):
        data = {"scope": ["env:prod"], "message": "Scheduled maintenance"}
        assert detect_resource_type(data) == "downtime"

    def test_detect_downtime_scope_not_list_falls_through(self):
        """scope as a string should not match downtime (must be a list)."""
        data = {"scope": "env:prod", "query": "avg:system.cpu{*} > 90"}
        assert detect_resource_type(data) == "monitor"

    def test_detect_unknown_raises_error(self):
        data = {"foo": "bar", "baz": 42}
        with pytest.raises(ValueError, match="Cannot detect resource type"):
            detect_resource_type(data)

    def test_dashboard_takes_priority_over_monitor(self):
        """If data has both layout_type and query, it should be detected as dashboard."""
        data = {"layout_type": "ordered", "query": "something", "widgets": []}
        assert detect_resource_type(data) == "dashboard"

    def test_slo_takes_priority_over_monitor(self):
        """SLO with type=metric and thresholds should win over monitor query detection."""
        data = {
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
            "query": {"numerator": "sum:requests.ok{*}", "denominator": "sum:requests{*}"},
        }
        assert detect_resource_type(data) == "slo"


# ============================================================================
# apply command tests
# ============================================================================


class TestApplyCommand:
    """Tests for the apply command."""

    def test_apply_requires_file_option(self, runner):
        result = runner.invoke(apply_cmd, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_apply_file_not_found(self, runner):
        result = runner.invoke(apply_cmd, ["-f", "/nonexistent/file.json"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_apply_invalid_json(self, runner):
        with runner.isolated_filesystem():
            with open("bad.json", "w") as f:
                f.write("not valid json{{{")
            result = runner.invoke(apply_cmd, ["-f", "bad.json"])
            assert result.exit_code != 0

    def test_apply_unrecognized_resource(self, runner):
        with runner.isolated_filesystem():
            with open("unknown.json", "w") as f:
                json.dump({"foo": "bar"}, f)
            result = runner.invoke(apply_cmd, ["-f", "unknown.json"])
            assert result.exit_code != 0
            assert "Cannot detect resource type" in result.output

    # --- Monitor apply ---

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_create_monitor(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        created_monitor = Mock()
        created_monitor.id = 12345
        created_monitor.to_dict.return_value = {"id": 12345, "name": "CPU Alert"}
        mock_client.monitors.create_monitor.return_value = created_monitor

        monitor_data = {
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(monitor_data, f)
            result = runner.invoke(apply_cmd, ["-f", "monitor.json"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "monitor" in result.output.lower()
        assert "12345" in result.output
        mock_client.monitors.create_monitor.assert_called_once()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_update_monitor(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        updated_monitor = Mock()
        updated_monitor.id = 12345
        updated_monitor.to_dict.return_value = {"id": 12345, "name": "CPU Alert Updated"}
        mock_client.monitors.update_monitor.return_value = updated_monitor

        monitor_data = {
            "id": 12345,
            "name": "CPU Alert Updated",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 95",
        }

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(monitor_data, f)
            result = runner.invoke(apply_cmd, ["-f", "monitor.json"])

        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "monitor" in result.output.lower()
        assert "12345" in result.output
        mock_client.monitors.update_monitor.assert_called_once()

    # --- Dashboard apply ---

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_create_dashboard(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        created = Mock()
        created.id = "abc-def-123"
        created.to_dict.return_value = {"id": "abc-def-123", "title": "My Dashboard"}
        mock_client.dashboards.create_dashboard.return_value = created

        data = {"title": "My Dashboard", "layout_type": "ordered", "widgets": []}

        with runner.isolated_filesystem():
            with open("dash.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "dash.json"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "dashboard" in result.output.lower()
        assert "abc-def-123" in result.output
        mock_client.dashboards.create_dashboard.assert_called_once()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_update_dashboard(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        updated = Mock()
        updated.id = "abc-def-123"
        updated.to_dict.return_value = {"id": "abc-def-123", "title": "Updated"}
        mock_client.dashboards.update_dashboard.return_value = updated

        data = {"id": "abc-def-123", "title": "Updated", "layout_type": "ordered", "widgets": []}

        with runner.isolated_filesystem():
            with open("dash.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "dash.json"])

        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "dashboard" in result.output.lower()
        mock_client.dashboards.update_dashboard.assert_called_once()

    # --- SLO apply ---

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_create_slo(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        created = Mock()
        created.id = "slo-abc123"
        created.to_dict.return_value = {"id": "slo-abc123", "name": "API SLO"}
        slo_response = Mock()
        slo_response.data = [created]
        mock_client.slos.create_slo.return_value = slo_response

        data = {
            "name": "API SLO",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
        }

        with runner.isolated_filesystem():
            with open("slo.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "slo.json"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "slo" in result.output.lower()
        mock_client.slos.create_slo.assert_called_once()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_update_slo(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        updated = Mock()
        updated.id = "slo-abc123"
        updated.to_dict.return_value = {"id": "slo-abc123", "name": "API SLO"}
        slo_response = Mock()
        slo_response.data = [updated]
        mock_client.slos.update_slo.return_value = slo_response

        data = {
            "id": "slo-abc123",
            "name": "API SLO",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
        }

        with runner.isolated_filesystem():
            with open("slo.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "slo.json"])

        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "slo" in result.output.lower()
        mock_client.slos.update_slo.assert_called_once()

    # --- Downtime apply ---

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_create_downtime(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        created = Mock()
        created.id = 9876
        created.to_dict.return_value = {"id": 9876, "scope": ["env:prod"]}
        mock_client.downtimes.create_downtime.return_value = created

        data = {"scope": ["env:prod"], "message": "Maintenance window"}

        with runner.isolated_filesystem():
            with open("downtime.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "downtime.json"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "downtime" in result.output.lower()
        mock_client.downtimes.create_downtime.assert_called_once()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_update_downtime(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        updated = Mock()
        updated.id = 9876
        updated.to_dict.return_value = {"id": 9876, "scope": ["env:prod"]}
        mock_client.downtimes.update_downtime.return_value = updated

        data = {"id": 9876, "scope": ["env:prod"], "message": "Extended maintenance"}

        with runner.isolated_filesystem():
            with open("downtime.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "downtime.json"])

        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "downtime" in result.output.lower()
        mock_client.downtimes.update_downtime.assert_called_once()

    # --- Dry-run ---

    def test_apply_dry_run_monitor_create(self, runner):
        """Dry-run should NOT make API calls."""
        data = {
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "monitor.json", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "create" in result.output.lower()
        assert "monitor" in result.output.lower()

    def test_apply_dry_run_monitor_update(self, runner):
        data = {
            "id": 12345,
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "monitor.json", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "update" in result.output.lower()
        assert "12345" in result.output

    def test_apply_dry_run_dashboard(self, runner):
        data = {"title": "My Dashboard", "layout_type": "ordered", "widgets": []}

        with runner.isolated_filesystem():
            with open("dash.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(apply_cmd, ["-f", "dash.json", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "dashboard" in result.output.lower()

    # --- Recursive directory scanning ---

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_apply_recursive_directory(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client

        created_monitor = Mock()
        created_monitor.id = 111
        created_monitor.to_dict.return_value = {"id": 111}
        mock_client.monitors.create_monitor.return_value = created_monitor

        created_dash = Mock()
        created_dash.id = "dash-abc"
        created_dash.to_dict.return_value = {"id": "dash-abc"}
        mock_client.dashboards.create_dashboard.return_value = created_dash

        with runner.isolated_filesystem():
            os.makedirs("resources")
            with open("resources/monitor.json", "w") as f:
                json.dump({"name": "Test", "type": "metric alert", "query": "avg:cpu{*} > 90"}, f)
            with open("resources/dashboard.json", "w") as f:
                json.dump({"title": "Dash", "layout_type": "ordered", "widgets": []}, f)
            # Non-json file should be ignored
            with open("resources/readme.txt", "w") as f:
                f.write("not json")

            result = runner.invoke(apply_cmd, ["-f", "resources", "--recursive"])

        assert result.exit_code == 0
        assert mock_client.monitors.create_monitor.called
        assert mock_client.dashboards.create_dashboard.called

    def test_apply_recursive_without_flag_on_directory(self, runner):
        """Passing a directory without --recursive should error."""
        with runner.isolated_filesystem():
            os.makedirs("resources")
            with open("resources/monitor.json", "w") as f:
                json.dump({"name": "Test", "type": "metric alert", "query": "q"}, f)

            result = runner.invoke(apply_cmd, ["-f", "resources"])

        assert result.exit_code != 0

    def test_apply_recursive_empty_directory(self, runner):
        with runner.isolated_filesystem():
            os.makedirs("empty_dir")
            result = runner.invoke(apply_cmd, ["-f", "empty_dir", "--recursive"])

        assert result.exit_code != 0 or "No JSON files" in result.output

    def test_apply_recursive_dry_run(self, runner):
        """Recursive + dry-run should list all files without API calls."""
        with runner.isolated_filesystem():
            os.makedirs("resources")
            with open("resources/monitor.json", "w") as f:
                json.dump({"name": "Test", "type": "metric alert", "query": "q"}, f)
            with open("resources/dash.json", "w") as f:
                json.dump({"title": "Dash", "layout_type": "ordered", "widgets": []}, f)

            result = runner.invoke(apply_cmd, ["-f", "resources", "--recursive", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output


# ============================================================================
# diff command tests
# ============================================================================


class TestDiffCommand:
    """Tests for the diff command."""

    def test_diff_requires_file_option(self, runner):
        result = runner.invoke(diff_cmd, [])
        assert result.exit_code != 0

    def test_diff_file_not_found(self, runner):
        result = runner.invoke(diff_cmd, ["-f", "/nonexistent/file.json"])
        assert result.exit_code != 0

    def test_diff_requires_id_in_file(self, runner):
        """Diff needs an 'id' field to fetch the live state."""
        data = {"name": "CPU Alert", "type": "metric alert", "query": "q"}

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(data, f)
            result = runner.invoke(diff_cmd, ["-f", "monitor.json"])

        assert result.exit_code != 0
        assert "id" in result.output.lower()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_diff_monitor_shows_differences(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        live_monitor = Mock()
        live_monitor.to_dict.return_value = {
            "id": 12345,
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }
        mock_client.monitors.get_monitor.return_value = live_monitor

        local_data = {
            "id": 12345,
            "name": "CPU Alert Updated",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 95",
        }

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(local_data, f)
            result = runner.invoke(diff_cmd, ["-f", "monitor.json"])

        assert result.exit_code == 0
        # Should show differences between local and live
        assert "CPU Alert Updated" in result.output or "---" in result.output

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_diff_monitor_no_differences(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        live_data = {
            "id": 12345,
            "name": "CPU Alert",
            "type": "metric alert",
            "query": "avg:system.cpu{*} > 90",
        }
        live_monitor = Mock()
        live_monitor.to_dict.return_value = live_data
        mock_client.monitors.get_monitor.return_value = live_monitor

        with runner.isolated_filesystem():
            with open("monitor.json", "w") as f:
                json.dump(live_data, f)
            result = runner.invoke(diff_cmd, ["-f", "monitor.json"])

        assert result.exit_code == 0
        assert "no differences" in result.output.lower() or "identical" in result.output.lower()

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_diff_dashboard(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        live_dash = Mock()
        live_dash.to_dict.return_value = {
            "id": "abc-123",
            "title": "Old Title",
            "layout_type": "ordered",
            "widgets": [],
        }
        mock_client.dashboards.get_dashboard.return_value = live_dash

        local_data = {
            "id": "abc-123",
            "title": "New Title",
            "layout_type": "ordered",
            "widgets": [],
        }

        with runner.isolated_filesystem():
            with open("dash.json", "w") as f:
                json.dump(local_data, f)
            result = runner.invoke(diff_cmd, ["-f", "dash.json"])

        assert result.exit_code == 0
        mock_client.dashboards.get_dashboard.assert_called_once_with("abc-123")

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_diff_slo(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        live_slo = Mock()
        live_slo.to_dict.return_value = {
            "id": "slo-abc",
            "name": "API SLO",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.9}],
        }
        slo_response = Mock()
        slo_response.data = live_slo
        mock_client.slos.get_slo.return_value = slo_response

        local_data = {
            "id": "slo-abc",
            "name": "API SLO Updated",
            "type": "metric",
            "thresholds": [{"timeframe": "30d", "target": 99.95}],
        }

        with runner.isolated_filesystem():
            with open("slo.json", "w") as f:
                json.dump(local_data, f)
            result = runner.invoke(diff_cmd, ["-f", "slo.json"])

        assert result.exit_code == 0
        mock_client.slos.get_slo.assert_called_once_with("slo-abc")

    @patch("ddogctl.commands.apply.get_datadog_client")
    def test_diff_downtime(self, mock_get_client, mock_client, runner):
        mock_get_client.return_value = mock_client
        live_dt = Mock()
        live_dt.to_dict.return_value = {
            "id": 9876,
            "scope": ["env:prod"],
            "message": "Original",
        }
        mock_client.downtimes.get_downtime.return_value = live_dt

        local_data = {
            "id": 9876,
            "scope": ["env:prod"],
            "message": "Updated",
        }

        with runner.isolated_filesystem():
            with open("downtime.json", "w") as f:
                json.dump(local_data, f)
            result = runner.invoke(diff_cmd, ["-f", "downtime.json"])

        assert result.exit_code == 0
        mock_client.downtimes.get_downtime.assert_called_once_with(9876)


# ============================================================================
# Integration with CLI
# ============================================================================


class TestApplyCliRegistration:
    """Tests that apply and diff are registered as top-level commands."""

    def test_apply_registered_on_main(self, runner):
        from ddogctl.cli import main

        result = runner.invoke(main, ["apply", "--help"])
        assert result.exit_code == 0
        assert "apply" in result.output.lower() or "--file" in result.output.lower()

    def test_diff_registered_on_main(self, runner):
        from ddogctl.cli import main

        result = runner.invoke(main, ["diff", "--help"])
        assert result.exit_code == 0
        assert "diff" in result.output.lower() or "--file" in result.output.lower()
