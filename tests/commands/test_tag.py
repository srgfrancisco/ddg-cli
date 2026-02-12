"""Tests for tag management commands."""

import json
from unittest.mock import Mock, patch


def test_tag_list_table_format(mock_client, runner):
    """Test listing tags for a host in table format."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod", "service:web", "team:platform"]
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01"])

    assert result.exit_code == 0
    assert "web-prod-01" in result.output
    assert "env:prod" in result.output
    assert "service:web" in result.output
    assert "team:platform" in result.output


def test_tag_list_json_format(mock_client, runner):
    """Test listing tags for a host in JSON format."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod", "service:web"]
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01", "--format", "json"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["host"] == "web-prod-01"
    assert "env:prod" in output["tags"]
    assert "service:web" in output["tags"]


def test_tag_list_with_source(mock_client, runner):
    """Test listing tags filtered by source."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod"]
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01", "--source", "users"])

    assert result.exit_code == 0
    mock_client.tags.get_host_tags.assert_called_once_with(host_name="web-prod-01", source="users")


def test_tag_list_without_source(mock_client, runner):
    """Test listing tags without source does not pass source kwarg."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod"]
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01"])

    assert result.exit_code == 0
    mock_client.tags.get_host_tags.assert_called_once_with(host_name="web-prod-01")


def test_tag_list_empty_tags(mock_client, runner):
    """Test listing tags when host has no tags."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = []
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01"])

    assert result.exit_code == 0
    assert "No tags" in result.output


def test_tag_list_no_tags_attribute(mock_client, runner):
    """Test listing tags when response has no tags attribute (unset)."""
    from ddogctl.commands.tag import tag

    mock_response = Mock(spec=[])
    mock_response.host = "web-prod-01"
    # Simulate tags being unset by making hasattr return False
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01"])

    assert result.exit_code == 0
    assert "No tags" in result.output


def test_tag_add_single_tag(mock_client, runner):
    """Test adding a single tag to a host."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod"]
    mock_client.tags.create_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["add", "web-prod-01", "env:prod"])

    assert result.exit_code == 0
    assert "Added" in result.output or "added" in result.output
    mock_client.tags.create_host_tags.assert_called_once()
    call_kwargs = mock_client.tags.create_host_tags.call_args
    assert call_kwargs.kwargs["host_name"] == "web-prod-01"
    body = call_kwargs.kwargs["body"]
    assert body.tags == ["env:prod"]


def test_tag_add_multiple_tags(mock_client, runner):
    """Test adding multiple tags to a host."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod", "service:web", "team:platform"]
    mock_client.tags.create_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(
            tag, ["add", "web-prod-01", "env:prod", "service:web", "team:platform"]
        )

    assert result.exit_code == 0
    call_kwargs = mock_client.tags.create_host_tags.call_args
    body = call_kwargs.kwargs["body"]
    assert sorted(body.tags) == sorted(["env:prod", "service:web", "team:platform"])


def test_tag_add_with_source(mock_client, runner):
    """Test adding tags with a specific source."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod"]
    mock_client.tags.create_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["add", "web-prod-01", "env:prod", "--source", "chef"])

    assert result.exit_code == 0
    call_kwargs = mock_client.tags.create_host_tags.call_args
    assert call_kwargs.kwargs["source"] == "chef"


def test_tag_add_without_source(mock_client, runner):
    """Test adding tags without source does not pass source kwarg."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod"]
    mock_client.tags.create_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["add", "web-prod-01", "env:prod"])

    assert result.exit_code == 0
    call_kwargs = mock_client.tags.create_host_tags.call_args
    assert "source" not in call_kwargs.kwargs


def test_tag_replace_tags(mock_client, runner):
    """Test replacing all tags on a host."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:staging"]
    mock_client.tags.update_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["replace", "web-prod-01", "env:staging"])

    assert result.exit_code == 0
    assert "Replaced" in result.output or "replaced" in result.output
    mock_client.tags.update_host_tags.assert_called_once()
    call_kwargs = mock_client.tags.update_host_tags.call_args
    assert call_kwargs.kwargs["host_name"] == "web-prod-01"
    body = call_kwargs.kwargs["body"]
    assert body.tags == ["env:staging"]


def test_tag_replace_multiple_tags(mock_client, runner):
    """Test replacing tags with multiple new tags."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:staging", "service:api"]
    mock_client.tags.update_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["replace", "web-prod-01", "env:staging", "service:api"])

    assert result.exit_code == 0
    call_kwargs = mock_client.tags.update_host_tags.call_args
    body = call_kwargs.kwargs["body"]
    assert sorted(body.tags) == sorted(["env:staging", "service:api"])


def test_tag_replace_with_source(mock_client, runner):
    """Test replacing tags with a specific source."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:staging"]
    mock_client.tags.update_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["replace", "web-prod-01", "env:staging", "--source", "puppet"])

    assert result.exit_code == 0
    call_kwargs = mock_client.tags.update_host_tags.call_args
    assert call_kwargs.kwargs["source"] == "puppet"


def test_tag_detach(mock_client, runner):
    """Test detaching (removing) all tags from a host."""
    from ddogctl.commands.tag import tag

    mock_client.tags.delete_host_tags.return_value = None

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["detach", "web-prod-01"])

    assert result.exit_code == 0
    assert "Detached" in result.output or "detached" in result.output or "Removed" in result.output
    mock_client.tags.delete_host_tags.assert_called_once_with(host_name="web-prod-01")


def test_tag_detach_with_source(mock_client, runner):
    """Test detaching tags with a specific source."""
    from ddogctl.commands.tag import tag

    mock_client.tags.delete_host_tags.return_value = None

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["detach", "web-prod-01", "--source", "users"])

    assert result.exit_code == 0
    mock_client.tags.delete_host_tags.assert_called_once_with(
        host_name="web-prod-01", source="users"
    )


def test_tag_add_requires_tags_argument(runner):
    """Test that add command requires at least one tag."""
    from ddogctl.commands.tag import tag

    result = runner.invoke(tag, ["add", "web-prod-01"])
    assert result.exit_code != 0


def test_tag_replace_requires_tags_argument(runner):
    """Test that replace command requires at least one tag."""
    from ddogctl.commands.tag import tag

    result = runner.invoke(tag, ["replace", "web-prod-01"])
    assert result.exit_code != 0


def test_tag_list_table_shows_total(mock_client, runner):
    """Test that table output shows tag count."""
    from ddogctl.commands.tag import tag

    mock_response = Mock()
    mock_response.host = "web-prod-01"
    mock_response.tags = ["env:prod", "service:web", "team:platform"]
    mock_client.tags.get_host_tags.return_value = mock_response

    with patch("ddogctl.commands.tag.get_datadog_client", return_value=mock_client):
        result = runner.invoke(tag, ["list", "web-prod-01"])

    assert result.exit_code == 0
    assert "3" in result.output
