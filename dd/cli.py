"""Main CLI entry point for Datadog CLI."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Datadog CLI for Kojo troubleshooting.

    A comprehensive CLI tool for querying Datadog APIs across monitors,
    metrics, events, logs, APM, and database monitoring.

    Configuration:
        DD_API_KEY - Datadog API key (required)
        DD_APP_KEY - Datadog Application key (required)
        DD_SITE - Datadog site (default: datadoghq.com)

    Examples:
        dd monitor list --state Alert
        dd metric query "avg:system.cpu.user{service:web-prod-blue}" --from 1h
        dd investigate latency web-prod-blue
    """
    pass


# Import and register all command groups
from dd.commands.monitor import monitor
from dd.commands.metric import metric
from dd.commands.event import event
from dd.commands.host import host
from dd.commands.apm import apm

main.add_command(monitor)
main.add_command(metric)
main.add_command(event)
main.add_command(host)
main.add_command(apm)


if __name__ == "__main__":
    main()
