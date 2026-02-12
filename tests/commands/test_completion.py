"""Tests for completion commands."""

from click.testing import CliRunner
from ddogctl.cli import main


class TestCompletionBash:
    """Tests for bash completion output."""

    def test_bash_outputs_completion_script(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_DDOGCTL_COMPLETE=bash_source" in result.output
        assert "ddogctl" in result.output

    def test_bash_outputs_eval_wrapper(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "bash"])
        assert result.exit_code == 0
        assert "eval" in result.output


class TestCompletionZsh:
    """Tests for zsh completion output."""

    def test_zsh_outputs_completion_script(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "_DDOGCTL_COMPLETE=zsh_source" in result.output
        assert "ddogctl" in result.output

    def test_zsh_outputs_eval_wrapper(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "eval" in result.output


class TestCompletionFish:
    """Tests for fish completion output."""

    def test_fish_outputs_completion_script(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "fish"])
        assert result.exit_code == 0
        assert "_DDOGCTL_COMPLETE=fish_source" in result.output
        assert "ddogctl" in result.output

    def test_fish_outputs_source_pipe(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "fish"])
        assert result.exit_code == 0
        assert "source" in result.output


class TestCompletionGroup:
    """Tests for the completion group itself."""

    def test_completion_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", "--help"])
        assert result.exit_code == 0
        assert "completion" in result.output.lower()

    def test_completion_no_args_shows_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion"])
        assert result.exit_code == 0
        # Should show available subcommands
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output
