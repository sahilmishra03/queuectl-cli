import typer

from app.db.database import SessionLocal
from app.repositories.job import JobRepository
from app.services.job import JobService
from app.services.queue import QueueService

app = typer.Typer()


@app.callback()
def main():
    pass


@app.command()
def enqueue(
    command: str,
    max_retries: int = 3,
):
    db = SessionLocal()

    repository = JobRepository(db)
    queue = QueueService()

    service = JobService(repository, queue)

    job = service.enqueue(command, max_retries)

    typer.echo(f"Job created: {job.id}")

    db.close()


if __name__ == "__main__":
    app()