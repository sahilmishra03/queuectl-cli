import multiprocessing
import os
import signal
import typer

from app.db.database import SessionLocal
from app.repositories.job import JobRepository
from app.services.queue import QueueService
from app.services.worker import WorkerService

app = typer.Typer()


@app.callback()
def worker():
    pass


def run_worker():
    db = SessionLocal()
    worker = WorkerService(
        JobRepository(db),
        QueueService(),
    )
    worker.start()
    db.close()


@app.command()
def start(count: int = 1):
    typer.echo(f"Starting {count} worker(s)...")
    processes = []
    pids = []
    for _ in range(count):
        p = multiprocessing.Process(target=run_worker)
        p.start()
        processes.append(p)
        pids.append(str(p.pid))

    with open(".worker_pids", "w") as f:
        f.write("\n".join(pids))

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user. Shutting down workers...")
        for p in processes:
            p.join()
    finally:
        if os.path.exists(".worker_pids"):
            os.remove(".worker_pids")


@app.command()
def stop():
    if not os.path.exists(".worker_pids"):
        typer.echo("No workers are currently running (no .worker_pids file).")
        return

    with open(".worker_pids", "r") as f:
        pids = f.read().splitlines()

    for pid_str in pids:
        if pid_str:
            pid = int(pid_str)
            try:
                os.kill(pid, signal.SIGTERM)
                typer.echo(f"Sent SIGTERM to worker PID {pid}")
            except ProcessLookupError:
                typer.echo(f"Worker PID {pid} not found.")

    if os.path.exists(".worker_pids"):
        os.remove(".worker_pids")
    typer.echo("All workers stopped.")


if __name__ == "__main__":
    app()