# pyrefly: ignore [missing-import]
from datetime import datetime
from typing import Optional

import typer

from app.core import config_manager
from app.db.database import SessionLocal
from app.models.job import JobState
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
    max_retries: Optional[int] = typer.Option(None, help="Max retries (default from config)"),
    priority: int = typer.Option(0, help="Job priority (higher = runs first)"),
    timeout: Optional[int] = typer.Option(None, help="Timeout in seconds"),
    run_at: Optional[str] = typer.Option(None, help="Schedule job at ISO datetime (e.g. 2026-07-17T20:00:00)"),
):
    if max_retries is None:
        max_retries = config_manager.get("max-retries")

    scheduled_at = None
    if run_at:
        try:
            scheduled_at = datetime.fromisoformat(run_at)
        except ValueError:
            typer.echo(f"Invalid datetime format: {run_at}. Use ISO format like 2026-07-17T20:00:00")
            return

    db = SessionLocal()
    repository = JobRepository(db)
    queue = QueueService()
    service = JobService(repository, queue)

    job = service.enqueue(
        command=command,
        max_retries=max_retries,
        priority=priority,
        timeout=timeout,
        run_at=scheduled_at,
    )

    msg = f"Job created: {job.id}"
    if priority > 0:
        msg += f" (priority: {priority})"
    if timeout:
        msg += f" (timeout: {timeout}s)"
    if scheduled_at:
        msg += f" (scheduled: {scheduled_at})"

    typer.echo(msg)
    db.close()


@app.command()
def dead(job_id: str):
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


@app.command()
def status():
    """Show summary of all job states, queue size, and execution metrics."""
    db = SessionLocal()
    repository = JobRepository(db)
    queue = QueueService()

    stats = repository.get_stats()
    counts = stats["counts"]

    typer.echo("=== Queue Status ===")
    typer.echo(f"  Queue size:    {queue.size()}")
    typer.echo("")
    typer.echo("=== Job Summary ===")
    for state_name, count in counts.items():
        typer.echo(f"  {state_name:<12} {count}")
    typer.echo(f"  {'total':<12} {stats['total_jobs']}")
    typer.echo("")
    typer.echo("=== Metrics ===")
    avg = stats["avg_duration_ms"]
    typer.echo(f"  Avg duration:  {f'{avg}ms' if avg else 'N/A'}")
    typer.echo(f"  Success rate:  {stats['success_rate']}%")
    typer.echo(f"  Timed out:     {stats['timed_out']}")

    db.close()


@app.command(name="list")
def list_jobs(
    state: Optional[str] = typer.Option(None, help="Filter by job state (pending, processing, completed, failed, dead, timed_out)"),
):
    """List jobs, optionally filtered by state."""
    db = SessionLocal()
    repository = JobRepository(db)

    if state:
        try:
            job_state = JobState(state.lower())
        except ValueError:
            typer.echo(f"Invalid state: {state}. Valid: {', '.join([s.value for s in JobState])}")
            db.close()
            return
        jobs = repository.list_by_state(job_state)
    else:
        jobs = repository.list_all()

    typer.echo(f"{'ID':<36} {'COMMAND':<18} {'STATE':<12} {'PRI':<5} {'ATTEMPTS':<10} {'DURATION':<10} {'ERROR'}")
    typer.echo("-" * 120)
    for job in jobs:
        error = (job.last_error or "")[:25]
        duration = f"{job.duration_ms}ms" if job.duration_ms else "-"
        typer.echo(
            f"{job.id:<36} {job.command:<18} {job.state.value:<12} {job.priority:<5} "
            f"{job.attempts:<10} {duration:<10} {error}"
        )

    typer.echo(f"\nTotal: {len(jobs)} jobs")
    db.close()


@app.command()
def logs(job_id: str):
    """Show stdout/stderr output for a specific job."""
    db = SessionLocal()
    repository = JobRepository(db)
    job = repository.get_by_id(job_id)

    if not job:
        typer.echo("Job not found.")
        db.close()
        return

    typer.echo(f"=== Job {job.id} ===")
    typer.echo(f"Command:   {job.command}")
    typer.echo(f"State:     {job.state.value}")
    typer.echo(f"Attempts:  {job.attempts}")
    if job.duration_ms:
        typer.echo(f"Duration:  {job.duration_ms}ms")
    if job.started_at:
        typer.echo(f"Started:   {job.started_at}")
    if job.completed_at:
        typer.echo(f"Completed: {job.completed_at}")
    typer.echo("")

    if job.stdout:
        typer.echo("=== STDOUT ===")
        typer.echo(job.stdout)

    if job.stderr:
        typer.echo("=== STDERR ===")
        typer.echo(job.stderr)

    if not job.stdout and not job.stderr:
        typer.echo("No output recorded.")

    db.close()


if __name__ == "__main__":
    app()
