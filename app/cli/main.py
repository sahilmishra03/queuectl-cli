# pyrefly: ignore [missing-import]
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

@app.command()
def dead(job_id: str):
    from app.models.job import JobState
    db = SessionLocal()
    repository = JobRepository(db)
    job = repository.get_by_id(job_id)
    
    if not job:
        typer.echo("Job not found.")
        db.close()
        return
        
    job.state = JobState.DEAD
    job.attempts = 3
    repository.update(job)
    db.close()
    
    typer.echo(f"Job {job_id} manually marked as DEAD.")


if __name__ == "__main__":
    app()