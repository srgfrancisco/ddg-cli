"""Tag management commands."""

import click
import json
from rich.console import Console
from rich.table import Table
from datadog_api_client.v1.model.host_tags import HostTags
from ddogctl.client import get_datadog_client
from ddogctl.utils.error import handle_api_error

console = Console()


@click.group()
def tag():
    """Tag management commands."""
    pass


@tag.command(name="list")
@click.argument("host")
@click.option("--source", help="Filter by tag source (e.g., users, chef, puppet)")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "table"]), default="table", help="Output format"
)
@handle_api_error
def list_tags(host, source, fmt):
    """List tags for a host."""
    client = get_datadog_client()

    kwargs = {"host_name": host}
    if source:
        kwargs["source"] = source

    with console.status(f"[cyan]Fetching tags for {host}...[/cyan]"):
        response = client.tags.get_host_tags(**kwargs)

    tags = getattr(response, "tags", None) or []

    if fmt == "json":
        output = {"host": host, "tags": tags}
        print(json.dumps(output, indent=2))
    else:
        if not tags:
            console.print(f"[dim]No tags found for {host}[/dim]")
            return

        table = Table(title=f"Tags for {host}")
        table.add_column("Tag", style="cyan")

        for t in sorted(tags):
            table.add_row(t)

        console.print(table)
        console.print(f"\n[dim]Total tags: {len(tags)}[/dim]")


@tag.command(name="add")
@click.argument("host")
@click.argument("tags", nargs=-1, required=True)
@click.option("--source", help="Tag source (e.g., users, chef, puppet)")
@handle_api_error
def add_tags(host, tags, source):
    """Add tags to a host.

    Appends new tags to the existing tag list. If no source is specified,
    defaults to "users".
    """
    client = get_datadog_client()

    kwargs = {
        "host_name": host,
        "body": HostTags(tags=list(tags)),
    }
    if source:
        kwargs["source"] = source

    with console.status(f"[cyan]Adding tags to {host}...[/cyan]"):
        response = client.tags.create_host_tags(**kwargs)

    result_tags = getattr(response, "tags", None) or []
    console.print(f"[green]Added {len(list(tags))} tag(s) to {host}[/green]")
    for t in result_tags:
        console.print(f"  [cyan]{t}[/cyan]")


@tag.command(name="replace")
@click.argument("host")
@click.argument("tags", nargs=-1, required=True)
@click.option("--source", help="Tag source (e.g., users, chef, puppet)")
@handle_api_error
def replace_tags(host, tags, source):
    """Replace all tags on a host.

    Overwrites all tags in the specified source with the supplied tags.
    If no source is specified, defaults to "users".
    """
    client = get_datadog_client()

    kwargs = {
        "host_name": host,
        "body": HostTags(tags=list(tags)),
    }
    if source:
        kwargs["source"] = source

    with console.status(f"[cyan]Replacing tags on {host}...[/cyan]"):
        response = client.tags.update_host_tags(**kwargs)

    result_tags = getattr(response, "tags", None) or []
    console.print(f"[green]Replaced tags on {host} ({len(result_tags)} tag(s))[/green]")
    for t in result_tags:
        console.print(f"  [cyan]{t}[/cyan]")


@tag.command(name="detach")
@click.argument("host")
@click.option("--source", help="Tag source to detach (e.g., users, chef, puppet)")
@handle_api_error
def detach_tags(host, source):
    """Detach (remove) all tags from a host.

    Removes all tags for a single host. If no source is specified,
    only deletes from the source "users".
    """
    client = get_datadog_client()

    kwargs = {"host_name": host}
    if source:
        kwargs["source"] = source

    with console.status(f"[cyan]Detaching tags from {host}...[/cyan]"):
        client.tags.delete_host_tags(**kwargs)

    source_msg = f" (source: {source})" if source else ""
    console.print(f"[green]Detached all tags from {host}{source_msg}[/green]")
