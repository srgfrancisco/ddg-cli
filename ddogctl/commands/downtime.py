"""Downtime management commands."""

import re
import time
import click
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error
from ddogctl.utils.file_input import load_json_option
from ddogctl.utils.confirm import confirm_action

console = Console()


def parse_downtime_time(value: str) -> int:
    """Parse a time string for downtime start/end.

    Supports:
        - "now" -> current Unix timestamp
        - Relative offsets: "2h", "30m", "1d" -> current time + offset
        - ISO datetime strings -> parsed to Unix timestamp

    Args:
        value: Time string to parse.

    Returns:
        Unix timestamp as integer.

    Raises:
        ValueError: If the time string format is not recognized.
    """
    if value == "now":
        return int(time.time())

    # Relative time: e.g. "2h", "30m", "1d"
    match = re.fullmatch(r"(\d+)([hmd])", value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {"m": 60, "h": 3600, "d": 86400}
        return int(time.time()) + amount * multipliers[unit]

    # ISO datetime
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid time format: '{value}'. Use 'now', relative (2h, 30m, 1d), or ISO datetime."
        )


@click.group()
def downtime():
    """Downtime management commands."""
    pass


@downtime.command(name="list")
@click.option("--current-only", is_flag=True, help="Show only currently active downtimes")
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_downtimes(current_only, format):
    """List all downtimes."""
    client = get_datadog_client()

    kwargs = {}
    if current_only:
        kwargs["current_only"] = True

    with console.status("[cyan]Fetching downtimes...[/cyan]"):
        downtimes = client.downtimes.list_downtimes(**kwargs)

    if format == "json":
        print(json.dumps([d.to_dict() for d in downtimes], indent=2, default=str))
    else:
        table = Table(title="Downtimes")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Scope", style="white", min_width=20)
        table.add_column("Message", style="dim", min_width=30)
        table.add_column("Start", style="yellow", width=20)
        table.add_column("End", style="yellow", width=20)
        table.add_column("Disabled", style="red", width=10)

        for d in downtimes:
            scope_str = ", ".join(d.scope) if d.scope else ""
            start_str = (
                datetime.fromtimestamp(d.start).strftime("%Y-%m-%d %H:%M:%S") if d.start else "N/A"
            )
            end_str = (
                datetime.fromtimestamp(d.end).strftime("%Y-%m-%d %H:%M:%S") if d.end else "None"
            )

            table.add_row(
                str(d.id),
                scope_str,
                d.message or "",
                start_str,
                end_str,
                str(d.disabled),
            )

        console.print(table)
        console.print(f"\n[dim]Total downtimes: {len(downtimes)}[/dim]")


@downtime.command(name="get")
@click.argument("downtime_id", type=int)
@click.option(
    "--format", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def get_downtime(downtime_id, format):
    """Get downtime details."""
    client = get_datadog_client()

    with console.status(f"[cyan]Fetching downtime {downtime_id}...[/cyan]"):
        dt = client.downtimes.get_downtime(downtime_id)

    if format == "json":
        print(json.dumps(dt.to_dict(), indent=2, default=str))
    else:
        console.print(f"\n[bold cyan]Downtime #{dt.id}[/bold cyan]")
        scope_str = ", ".join(dt.scope) if dt.scope else "N/A"
        console.print(f"[bold]Scope:[/bold] {scope_str}")

        if dt.message:
            console.print(f"[bold]Message:[/bold] {dt.message}")

        start_str = (
            datetime.fromtimestamp(dt.start).strftime("%Y-%m-%d %H:%M:%S") if dt.start else "N/A"
        )
        console.print(f"[bold]Start:[/bold] {start_str}")

        end_str = datetime.fromtimestamp(dt.end).strftime("%Y-%m-%d %H:%M:%S") if dt.end else "None"
        console.print(f"[bold]End:[/bold] {end_str}")
        console.print(f"[bold]Disabled:[/bold] {dt.disabled}")

        if dt.monitor_id:
            console.print(f"[bold]Monitor ID:[/bold] {dt.monitor_id}")


@downtime.command(name="create")
@click.option("--scope", default=None, help="Downtime scope (e.g., 'env:prod')")
@click.option("--start", "start_time", default=None, help="Start time (now, 2h, ISO datetime)")
@click.option("--end", "end_time", default=None, help="End time (2h, 30m, 1d, ISO datetime)")
@click.option("--message", default=None, help="Downtime message")
@click.option("--monitor-id", type=int, default=None, help="Scope to a specific monitor")
@click.option(
    "-f",
    "--file",
    "file_data",
    callback=load_json_option,
    default=None,
    help="JSON file with downtime definition",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def create_downtime_cmd(scope, start_time, end_time, message, monitor_id, file_data, fmt):
    """Create a downtime from inline flags or a JSON file."""
    from datadog_api_client.v1.model.downtime import Downtime

    if file_data:
        downtime_body = Downtime(**file_data)
    else:
        if not scope:
            raise click.UsageError("Missing option '--scope' (required without -f)")

        kwargs = {"scope": [scope]}

        if start_time:
            kwargs["start"] = parse_downtime_time(start_time)

        if end_time:
            kwargs["end"] = parse_downtime_time(end_time)

        if message:
            kwargs["message"] = message

        if monitor_id is not None:
            kwargs["monitor_id"] = monitor_id

        downtime_body = Downtime(**kwargs)

    client = get_datadog_client()

    with console.status("[cyan]Creating downtime...[/cyan]"):
        result = client.downtimes.create_downtime(body=downtime_body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]Downtime {result.id} created[/green]")
        scope_str = ", ".join(result.scope) if result.scope else "N/A"
        console.print(f"[bold]Scope:[/bold] {scope_str}")
        if result.message:
            console.print(f"[bold]Message:[/bold] {result.message}")


@downtime.command(name="update")
@click.argument("downtime_id", type=int)
@click.option("--scope", default=None, help="New scope (e.g., 'env:staging')")
@click.option("--end", "end_time", default=None, help="New end time (4h, 30m, ISO datetime)")
@click.option("--message", default=None, help="New message")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def update_downtime_cmd(downtime_id, scope, end_time, message, fmt):
    """Update a downtime by ID."""
    from datadog_api_client.v1.model.downtime import Downtime

    kwargs = {}
    if scope is not None:
        kwargs["scope"] = [scope]
    if end_time is not None:
        kwargs["end"] = parse_downtime_time(end_time)
    if message is not None:
        kwargs["message"] = message

    if not kwargs:
        raise click.UsageError("No update fields specified. Use --scope, --end, or --message.")

    update_body = Downtime(**kwargs)
    client = get_datadog_client()

    with console.status(f"[cyan]Updating downtime {downtime_id}...[/cyan]"):
        result = client.downtimes.update_downtime(downtime_id, body=update_body)

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        console.print(f"[green]Downtime {downtime_id} updated[/green]")


@downtime.command(name="delete")
@click.argument("downtime_id", type=int)
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@handle_api_error
def delete_downtime_cmd(downtime_id, confirmed):
    """Cancel (delete) a downtime by ID."""
    if not confirm_action(f"Cancel downtime {downtime_id}?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    with console.status(f"[cyan]Cancelling downtime {downtime_id}...[/cyan]"):
        client.downtimes.cancel_downtime(downtime_id)

    console.print(f"[green]Downtime {downtime_id} cancelled[/green]")


@downtime.command(name="cancel-by-scope")
@click.argument("scope")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
@handle_api_error
def cancel_by_scope_cmd(scope, confirmed, fmt):
    """Cancel all active downtimes matching a scope (bulk operation)."""
    from datadog_api_client.v1.model.cancel_downtimes_by_scope_request import (
        CancelDowntimesByScopeRequest,
    )

    if not confirm_action(f"Cancel all downtimes with scope '{scope}'?", confirmed):
        console.print("[yellow]Aborted[/yellow]")
        return

    client = get_datadog_client()

    body = CancelDowntimesByScopeRequest(scope=scope)

    with console.status(f"[cyan]Cancelling downtimes with scope '{scope}'...[/cyan]"):
        result = client.downtimes.cancel_downtimes_by_scope(body=body)

    if fmt == "json":
        print(json.dumps({"cancelled_ids": result.cancelled_ids}, indent=2, default=str))
    else:
        count = len(result.cancelled_ids) if result.cancelled_ids else 0
        console.print(f"[green]{count} downtime(s) cancelled for scope '{scope}'[/green]")
        if result.cancelled_ids:
            console.print(f"[dim]IDs: {', '.join(str(i) for i in result.cancelled_ids)}[/dim]")
