# pyrefly: ignore [missing-import]
import typer

from app.cli.dlq import app as dlq_app
from app.cli.main import app as main_app
from app.cli.worker import app as worker_app

app = main_app
app.add_typer(worker_app, name="worker")
app.add_typer(dlq_app, name="dlq")


if __name__ == "__main__":
    app()
