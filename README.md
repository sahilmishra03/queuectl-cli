# QueueCTL

A production-grade, CLI-based background job queue and monitoring system built with Python. It uses PostgreSQL for persistent job state storage and Redis (Sorted Sets) for high-performance priority queueing and execution.

## Features

- **Job Enqueueing & Lifecycle Management**: Persistent job tracking across states (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `DEAD`, `TIMED_OUT`).
- **Worker Process**: Background worker execution loop with automatic retry and scheduling capabilities.
- **Exponential Backoff & Retries**: Automatic retries for failed jobs with configurable retry count and exponential backoff base (`delay = base ** attempts`).
- **Dead Letter Queue (DLQ)**: Jobs failing beyond maximum retries move to the DLQ where they can be inspected (`dlq list`) and re-enqueued (`dlq retry <id>`).
- **Priority Queueing**: Redis Sorted Sets (`ZADD`/`ZPOPMIN`) ensure higher priority jobs execute before lower priority jobs.
- **Job Timeout Handling**: Subprocess execution includes strict timeout enforcement (`--timeout`). Timed out jobs transition to `TIMED_OUT` state.
- **Scheduled Jobs (`run_at`)**: Schedule background jobs to run at or after a specific ISO timestamp (`--run-at`).
- **Output Logging**: Captures `stdout` and `stderr` for every job directly to the database (`logs <id>`).
- **Execution Metrics & Statistics**: Real-time summary of job counts, average execution duration (`duration_ms`), success rate, and timeout metrics (`status`).
- **Web Dashboard**: Minimal, real-time FastAPI web dashboard featuring dark theme, stats cards, job filtering, detail modal, and auto-refresh (`dashboard start`).
- **Configuration Management**: Persistent local CLI config storage for default retry rules (`config set/list`).

---

## Tech Stack

- **Python 3.13+**
- **Typer** (CLI Framework)
- **FastAPI + Uvicorn** (Web Dashboard)
- **PostgreSQL + SQLAlchemy 2.0** (Database & ORM)
- **Alembic** (Database Migrations)
- **Redis** (Priority Queue via Sorted Sets)
- **Pytest + Pytest-Cov** (Automated Testing & Coverage)

---

## Installation & Setup

### 🚀 One-Click Reviewer Setup (Docker)

If you have Docker installed, you can spin up the entire architecture (PostgreSQL, Redis, Worker, and Web Dashboard) in a single command without installing any local dependencies!

```bash
# 1. Clone the repository
git clone <repository-url>
cd queuectl

# 2. Start the entire cluster in the background
docker-compose up -d --build
```

That's it!
- The **Dashboard** is now live at [http://localhost:8000](http://localhost:8000).
- The **Database migrations** run automatically.
- **3 parallel workers** are already running in the background.

To test it, you can enqueue jobs from your local terminal (just ensure your `.env` points to `localhost` ports) or dive into the dashboard!

---

### Local Manual Setup (Without Docker)

### 1. Clone the repository

```bash
git clone <repository-url>
cd queuectl
```

### 2. Create and activate virtual environment

**Windows (PowerShell/CMD):**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-cov httpx
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/queuectl
REDIS_URL=redis://localhost:6379/0
```

### 5. Create database and run migrations

Ensure PostgreSQL and Redis servers are running locally, then initialize the schema:

```bash
alembic upgrade head
```

---

## CLI Usage Guide

Run all commands using `python -m app.cli.app <command> [options]`:

### Enqueueing Jobs

```powershell
# Basic enqueue
python -m app.cli.app enqueue "echo Hello World"

# Enqueue with high priority (runs first) and 5-second timeout
python -m app.cli.app enqueue "ping localhost -n 20" --priority 10 --timeout 5

# Enqueue scheduled job for a specific datetime
python -m app.cli.app enqueue "echo Scheduled Task" --run-at "2026-07-17T20:30:00"
```

### Starting the Worker

```powershell
# Start worker processing loop
python -u -m app.cli.worker start
```

### Checking Status, List, and Logs

```powershell
# View real-time queue status and execution metrics
python -m app.cli.app status

# List all jobs or filter by state (pending, processing, completed, failed, dead, timed_out)
python -m app.cli.app list --state completed

# View stdout and stderr logs for a specific job
python -m app.cli.app logs <job-id>
```

### Dead Letter Queue (DLQ) & Configuration

```powershell
# List jobs in the DLQ
python -m app.cli.app dlq list

# Re-enqueue a dead job for retry
python -m app.cli.app dlq retry <job-id>

# Set global max retries or backoff base
python -m app.cli.app config set max-retries 5
python -m app.cli.app config list
```

### Launching the Web Dashboard

```powershell
# Start the real-time FastAPI dashboard on port 8000
python -m app.cli.app dashboard start --port 8000
```
Open `http://localhost:8000` in your browser to view the interactive dashboard.

---

## Automated Testing & Coverage

The project includes a robust, isolated automated testing suite built with **pytest** and **pytest-cov**.

### Key Testing Architecture
- **Isolated In-Memory Database**: Tests use an in-memory SQLite database (`sqlite:///:memory:`) with `StaticPool` and savepoint rollback transactions (`conftest.py`). Tests run in milliseconds without requiring or modifying the local development PostgreSQL database.
- **Automatic Redis Queue Cleanup**: An `autouse` fixture drains and purges test queue keys in Redis before and after every test run.

### Running the Tests

To run the entire test suite and generate a terminal coverage report:

```powershell
# Run with coverage report
.\.venv\Scripts\pytest -v --cov=app --cov-report=term-missing
```

To generate an interactive HTML coverage report:

```powershell
.\.venv\Scripts\pytest --cov=app --cov-report=html
# Open htmlcov/index.html in your browser
```

### Test Suite Structure (`tests/`)

The suite consists of **41 automated tests** achieving **85% code coverage** (exceeding the 80%+ target):

```text
tests/
├── conftest.py             # Shared DB isolation, rollback sessions, and clean_redis fixtures
├── test_job_repository.py  # 10 tests covering CRUD, retryable/scheduled queries, dead reset, and stats
├── test_queue_service.py   # 3 tests covering enqueue/dequeue, empty checks, and priority ordering
├── test_retry_service.py   # 2 tests verifying exponential backoff calculation (2 ** attempts)
├── test_executor.py        # 4 tests verifying command execution, failure, timeout, and output capture
├── test_worker.py          # 7 tests verifying job processing states, logging, polling, and priority
├── test_cli.py             # 9 tests using CliRunner for enqueue, status, list, logs, dead, config, dlq
├── test_dashboard.py       # 4 tests using TestClient covering HTML root, /api/stats, /api/jobs, details
└── test_stats.py           # 2 tests covering empty DB stats and multi-state calculation verification
```

### Coverage Summary

| Module / Package | Coverage | Description |
|---|---|---|
| **`app.repositories.job`** | **100%** | All SQL queries (`list_by_state`, `get_retryable_jobs`, `get_scheduled_jobs`, `get_stats`) |
| **`app.services.queue`** | **100%** | Redis sorted set operations (`ZADD`, `ZPOPMIN`, `ZCARD`) |
| **`app.services.retry`** | **100%** | Exponential delay calculations |
| **`app.services.job`** | **100%** | Enqueue orchestration with priority/timeout/schedule support |
| **`app.workers.executor`** | **100%** | Subprocess execution & `TimeoutExpired` handling |
| **`app.services.worker`** | **96%** | Processing loop, state transitions (`TIMED_OUT`, `DEAD`, `COMPLETED`), and logging |
| **`app.dashboard.dashboard`** | **100%** | FastAPI routes and HTML dashboard generator |
| **`app.cli.main` & `dlq`** | **91%** | All CLI subcommands and options |
| **Overall Project Total** | **85%** | **41 / 41 Tests Passing** |

---

## Project Structure

```text
queuectl/
│
├── app/
│   ├── cli/            # Typer CLI subcommands (app.py, main.py, worker.py, dlq.py, config.py, dashboard.py)
│   ├── core/           # Configuration manager & settings
│   ├── dashboard/      # FastAPI minimal web dashboard & API routes
│   ├── db/             # SQLAlchemy engine & Redis client connection
│   ├── models/         # Job & JobState SQLAlchemy models
│   ├── repositories/   # JobRepository data access layer
│   ├── services/       # Business logic (JobService, QueueService, WorkerService, RetryService, DLQService)
│   └── workers/        # CommandExecutor subprocess execution engine
│
├── alembic/            # Database migrations
├── tests/              # Pytest automated test suite
├── pytest.ini          # Pytest configuration
├── .env.example        # Environment variable template
├── README.md           # Project documentation
└── requirements.txt    # Project dependencies
```