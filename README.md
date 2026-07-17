# QueueCTL

A production-ready CLI-based background job queue built with **Python**, **PostgreSQL**, and **Redis**. QueueCTL provides reliable background job execution with retries, scheduling, priority queues, timeout handling, logging, monitoring, and a lightweight web dashboard.

![Architecture](docs/architecture.png)

---

## Core Features

- CLI-based background job processing
- PostgreSQL persistence
- Redis priority queue (Sorted Sets)
- Background worker
- Automatic retries with exponential backoff
- Dead Letter Queue (DLQ)
- Scheduled jobs (`run_at`)
- Job timeout handling
- Output logging (`stdout` / `stderr`)
- Execution metrics

---

## Bonus Features

- Live Terminal Monitor (Textual TUI)
- FastAPI Dashboard
- Docker support
- Installable CLI package (`queuectl`)
- Persistent configuration management

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.13+ |
| CLI | Typer |
| Terminal UI | Textual |
| Dashboard | FastAPI |
| Database | PostgreSQL |
| Queue | Redis |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Testing | Pytest + Pytest-Cov |
| Containerization | Docker |

---

## Installation & Setup

Clone the repository:

```bash
git clone https://github.com/sahilmishra03/queuectl-cli.git
cd queuectl
```

Create a virtual environment.

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install QueueCTL as a CLI package:

```bash
pip install -e .
```

Create a `.env` file:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/queuectl
REDIS_URL=redis://localhost:6379/0
```

Run database migrations:

```bash
alembic upgrade head
```

### Default Configuration

QueueCTL uses the following defaults:

- Maximum retries: **3**
- Exponential backoff: `delay = 2^attempts`

These values can be updated using:

```bash
queuectl config set max-retries <value>
```

---

## Docker

Start the complete development environment:

```bash
docker compose up --build
```

This starts:

- PostgreSQL
- Redis
- QueueCTL application

---

## CLI Commands

View all available commands:

```bash
queuectl --help
```

View help for a specific command:

```bash
queuectl enqueue --help
queuectl worker --help
queuectl monitor --help
```

Common commands:

```bash
queuectl enqueue '{"id":"job1","command":"sleep 2"}'

queuectl worker start --count 3

queuectl worker stop

queuectl status

queuectl list --state pending

queuectl logs <job-id>

queuectl dlq list

queuectl dlq retry job1

queuectl dashboard start

queuectl monitor

queuectl config list

queuectl config set max-retries 3
```

---

## Demo

A complete walkthrough of QueueCTL is available here:

**Video:** https://youtu.be/your-demo-link

---

## Testing

Run all tests:

```bash
pytest
```

Generate a coverage report:

```bash
pytest --cov=app
```

Current Status

- 45 / 45 tests passing
- 85% code coverage

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```text
MIT License

Copyright (c) 2026 Sahil Mishra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```