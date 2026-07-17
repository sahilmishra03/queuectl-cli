# pyrefly: ignore [missing-import]
import typer

from app.cli.config import app as config_app
from app.cli.dashboard import app as dashboard_app
from app.cli.dlq import app as dlq_app
from app.cli.main import app as main_app
from app.cli.monitor import app as monitor_app
from app.cli.worker import app as worker_app

app = main_app
app.add_typer(worker_app, name="worker")
app.add_typer(dlq_app, name="dlq")
app.add_typer(config_app, name="config")
app.add_typer(dashboard_app, name="dashboard")
app.add_typer(monitor_app, name="monitor")


if __name__ == "__main__":
    app()
