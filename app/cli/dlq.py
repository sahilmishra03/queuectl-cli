# pyrefly: ignore [missing-import]
import typer

from app.db.database import SessionLocal
from app.repositories.job import JobRepository
from app.services.dlq import DLQService
from app.services.queue import QueueService

app = typer.Typer()


@app.callback()
def dlq():
    pass


@app.command()
def list():
    db = SessionLocal()
    repository = JobRepository(db)
    queue = QueueService()
    service = DLQService(repository, queue)

    jobs = service.list_jobs()
    
    typer.echo(f"{'ID':<36} {'COMMAND':<18} ATTEMPTS")
    typer.echo("-" * 63)
    for job in jobs:
        typer.echo(f"{job.id:<36} {job.command:<18} {job.attempts}")

    db.close()


@app.command()
def retry(job_id: str):
    db = SessionLocal()
    repository = JobRepository(db)
    queue = QueueService()
    service = DLQService(repository, queue)

    try:
        service.retry(job_id)
        typer.echo(f"Job {job_id} moved back to queue.")
    except ValueError as e:
        typer.echo(str(e))
    finally:
        db.close()


if __name__ == "__main__":
    app()
