# pyrefly: ignore [missing-import]
import typer

from app.core import config_manager

app = typer.Typer()


@app.callback()
def config():
    pass


@app.command()
def set(
    key: str = typer.Argument(help="Config key (e.g. max-retries, backoff-base)"),
    value: str = typer.Argument(help="Value to set"),
):
    """Manage configuration (retry, backoff, etc.): set value."""
    try:
        config_manager.set_value(key, value)
        typer.echo(f"Set {key} = {value}")
    except ValueError as e:
        typer.echo(str(e))


@app.command()
def get(
    key: str = typer.Argument(help="Config key to get"),
):
    """Get a configuration value."""
    val = config_manager.get(key)
    if val is None:
        typer.echo(f"Unknown key: {key}")
    else:
        typer.echo(f"{key} = {val}")


@app.command(name="list")
def list_config():
    """Show all configuration values."""
    cfg = config_manager.load_config()
    for k, v in cfg.items():
        typer.echo(f"{k} = {v}")


if __name__ == "__main__":
    app()
