"""Tests for command aliases."""

from unittest.mock import patch, Mock
from click.testing import CliRunner
from ddogctl.cli import main


class TestAliasResolution:
    """Tests that short aliases resolve to full command groups."""

    def test_mon_resolves_to_monitor(self):
        runner = CliRunner()
        result = runner.invoke(main, ["mon", "--help"])
        assert result.exit_code == 0
        # Should show monitor group help
        assert "monitor" in result.output.lower() or "Monitor" in result.output

    def test_dash_resolves_to_dashboard(self):
        runner = CliRunner()
        result = runner.invoke(main, ["dash", "--help"])
        assert result.exit_code == 0
        assert "dashboard" in result.output.lower() or "Dashboard" in result.output

    def test_dt_resolves_to_downtime(self):
        runner = CliRunner()
        result = runner.invoke(main, ["dt", "--help"])
        assert result.exit_code == 0
        assert "downtime" in result.output.lower() or "Downtime" in result.output

    def test_sc_resolves_to_service_check(self):
        runner = CliRunner()
        result = runner.invoke(main, ["sc", "--help"])
        assert result.exit_code == 0
        assert "service" in result.output.lower() or "Service" in result.output

    def test_inv_resolves_to_investigate(self):
        runner = CliRunner()
        result = runner.invoke(main, ["inv", "--help"])
        assert result.exit_code == 0
        assert "investigate" in result.output.lower() or "Investigate" in result.output


class TestAliasSubcommands:
    """Tests that aliases work with subcommands."""

    def test_mon_list_works(self):
        """mon list should invoke monitor list."""
        runner = CliRunner()
        with patch("ddogctl.commands.monitor.get_datadog_client") as mock_get:
            mock_client = Mock()
            mock_client.monitors = Mock()
            mock_client.monitors.list_monitors.return_value = []
            mock_get.return_value = mock_client
            result = runner.invoke(main, ["mon", "list"])
            assert result.exit_code == 0

    def test_inv_with_subcommand(self):
        """inv should accept investigate subcommands."""
        runner = CliRunner()
        # Just verify the alias resolves and the subcommand help is accessible
        result = runner.invoke(main, ["inv", "latency", "--help"])
        assert result.exit_code == 0


class TestFullCommandsStillWork:
    """Tests that full command names still work alongside aliases."""

    def test_monitor_still_works(self):
        runner = CliRunner()
        result = runner.invoke(main, ["monitor", "--help"])
        assert result.exit_code == 0

    def test_dashboard_still_works(self):
        runner = CliRunner()
        result = runner.invoke(main, ["dashboard", "--help"])
        assert result.exit_code == 0

    def test_downtime_still_works(self):
        runner = CliRunner()
        result = runner.invoke(main, ["downtime", "--help"])
        assert result.exit_code == 0

    def test_service_check_still_works(self):
        runner = CliRunner()
        result = runner.invoke(main, ["service-check", "--help"])
        assert result.exit_code == 0

    def test_investigate_still_works(self):
        runner = CliRunner()
        result = runner.invoke(main, ["investigate", "--help"])
        assert result.exit_code == 0


class TestUnknownCommand:
    """Tests that unknown commands still fail properly."""

    def test_unknown_command_fails(self):
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code != 0

    def test_unknown_alias_fails(self):
        runner = CliRunner()
        result = runner.invoke(main, ["xyz"])
        assert result.exit_code != 0
