import typer

from app.db.database import SessionLocal
from app.repositories.job import JobRepository
from app.services.queue import QueueService
from app.services.worker import WorkerService

app = typer.Typer()


@app.callback()
def worker():
    pass


@app.command()
def start():
    db = SessionLocal()

    worker = WorkerService(
        JobRepository(db),
        QueueService(),
    )

    worker.start()

    db.close()


if __name__ == "__main__":
    app()