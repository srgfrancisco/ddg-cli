"""Shell completion commands."""

import click


@click.group(invoke_without_command=True)
@click.pass_context
def completion(ctx):
    """Generate shell completion scripts.

    Output shell-specific completion scripts for bash, zsh, or fish.

    Usage:
        eval "$(ddogctl completion bash)"
        eval "$(ddogctl completion zsh)"
        ddogctl completion fish | source
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@completion.command()
def bash():
    """Output bash completion script."""
    click.echo('eval "$(_DDOGCTL_COMPLETE=bash_source ddogctl)"')


@completion.command()
def zsh():
    """Output zsh completion script."""
    click.echo('eval "$(_DDOGCTL_COMPLETE=zsh_source ddogctl)"')


@completion.command()
def fish():
    """Output fish completion script."""
    click.echo("_DDOGCTL_COMPLETE=fish_source ddogctl | source")
