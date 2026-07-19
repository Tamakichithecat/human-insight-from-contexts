from __future__ import annotations

import typer

from hifc import __version__

app = typer.Typer(
    name="hifc",
    help="Human insight from contexts CLI.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    _ = version


@app.command("doctor")
def doctor() -> None:
    """Show local foundation status."""
    typer.echo("hifc foundation is installed")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
