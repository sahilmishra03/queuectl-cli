import typer
import uvicorn

app = typer.Typer()


@app.callback()
def dashboard_group():
    pass


@app.command()
def start(
    port: int = typer.Option(8000, help="Port to run dashboard on"),
):
    """Start the web dashboard."""
    typer.echo(f"Starting dashboard at http://localhost:{port}")
    from app.dashboard.dashboard import dashboard_app
    uvicorn.run(dashboard_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    app()
