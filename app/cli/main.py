from datetime import datetime
from typing import Optional

# pyrefly: ignore [missing-import]
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
    command: list[str] = typer.Argument(help="Job command or JSON payload"),
    job_id: Optional[str] = typer.Option(None, "--id", help="Optional custom job ID"),
    max_retries: Optional[int] = typer.Option(None, help="Max retries (default from config)"),
    priority: int = typer.Option(0, help="Job priority (higher = runs first)"),
    timeout: Optional[int] = typer.Option(None, help="Timeout in seconds"),
    run_at: Optional[str] = typer.Option(None, help="Schedule job at ISO datetime (e.g. 2026-07-17T20:00:00)"),
):
    """Add a new job to the queue."""
    import json
    raw_command = " ".join(command)
    parsed_command = raw_command
    if raw_command.strip().startswith("{") and raw_command.strip().endswith("}"):
        payload = None
        try:
            payload = json.loads(raw_command)
        except Exception:
            import re
            payload = {}
            id_match = re.search(r'[\'"]?id[\'"]?\s*:\s*[\'"]?([^\'",}]+)[\'"]?', raw_command, re.IGNORECASE)
            if id_match:
                payload["id"] = id_match.group(1).strip()
            cmd_match = re.search(r'[\'"]?(?:command|cmd)[\'"]?\s*:\s*[\'"]?(.+?)[\'"]?\s*(?:,[\'"]?(?:id|priority|timeout|run_at|max_retries)[\'"]?\s*:|\}$)', raw_command, re.IGNORECASE)
            if cmd_match:
                payload["command"] = cmd_match.group(1).strip()

        if isinstance(payload, dict):
            parsed_command = payload.get("command") or payload.get("cmd") or raw_command
            if not job_id and ("id" in payload or "job_id" in payload):
                job_id = str(payload.get("id") or payload.get("job_id"))
            if priority == 0 and payload.get("priority") is not None:
                priority = int(payload["priority"])
            if timeout is None and payload.get("timeout") is not None:
                timeout = int(payload["timeout"])
            if run_at is None and payload.get("run_at") is not None:
                run_at = str(payload["run_at"])

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
        command=parsed_command,
        max_retries=max_retries,
        priority=priority,
        timeout=timeout,
        run_at=scheduled_at,
        job_id=job_id,
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
    """Manually move a job to the DEAD (DLQ) state."""
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
    """Show summary of all job states & active workers."""
    import os
    db = SessionLocal()
    repository = JobRepository(db)
    queue = QueueService()

    stats = repository.get_stats()
    counts = stats["counts"]

    active_workers = 0
    if os.path.exists(".worker_pids"):
        try:
            with open(".worker_pids", "r") as f:
                active_workers = len([p for p in f.read().splitlines() if p.strip()])
        except Exception:
            pass

    typer.echo("=== Queue Status ===")
    typer.echo(f"  Queue size:    {queue.size()}")
    typer.echo(f"  Active workers: {active_workers}")
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
    """List jobs by state."""
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

    typer.echo(f"{'ID':<36} {'COMMAND':<38} {'STATE':<12} {'PRI':<5} {'ATTEMPTS':<10} {'DURATION':<10} {'ERROR'}")
    typer.echo("-" * 140)
    for job in jobs:
        cmd = (job.command[:35] + "...") if len(job.command) > 38 else job.command
        error = (job.last_error or "").strip().split("\n")[0][:30]
        duration = f"{job.duration_ms}ms" if job.duration_ms is not None else "-"
        typer.echo(
            f"{job.id:<36} {cmd:<38} {job.state.value:<12} {job.priority:<5} "
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

