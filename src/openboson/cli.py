"""Command-line interface for OpenBoson.

Commands:
    openboson --version        Print version.
    openboson serve            Run the FastAPI engine server.
    openboson gui              Launch the PySide6 desktop GUI.
"""

from __future__ import annotations

import sys

import click

from openboson import __version__


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="openboson")
@click.pass_context
def main(ctx: click.Context) -> None:
    """OpenBoson — local ExSim + NetSim practice platform."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option(
    "--port",
    type=int,
    default=0,
    show_default=True,
    help="Bind port (0 = ephemeral, printed to stdout on first line).",
)
def serve(host: str, port: int) -> None:
    """Run the FastAPI engine server."""
    import uvicorn

    from openboson.server import app

    # uvicorn will pick a free port when port==0; we surface the actual port
    # after binding by inspecting the server socket in a lifespan hook.
    if port == 0:
        # Use a log-config that prints the listening address to stdout.
        uvicorn.run(app, host=host, port=port, log_level="warning")
    else:
        click.echo(f"Starting OpenBoson engine on http://{host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning")


@main.command()
def gui() -> None:
    """Launch the PySide6 desktop GUI."""
    from openboson.gui.app import run_gui

    run_gui()


if __name__ == "__main__":
    sys.exit(main())
