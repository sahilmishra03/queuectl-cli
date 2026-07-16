# QueueCTL

A CLI-based background job queue system built with Python. It uses PostgreSQL for persistent job storage and Redis for queue management.

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy
- Alembic
- Typer

## Installation

### Clone the repository

```bash
git clone <repository-url>
cd queuectl
```

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate the virtual environment

**Windows**

```bash
.venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root.

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/queuectl
REDIS_URL=redis://localhost:6379/0
```

### Create the database

```sql
CREATE DATABASE queuectl;
```

### Run migrations

```bash
alembic upgrade head
```

### Verify database and Redis connection

```bash
python test.py
```

Expected output:

```text
Engine(postgresql://...)
True
```

## Project Structure

```text
queuectl/
│
├── app/
│   ├── cli/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── workers/
│
├── alembic/
├── tests/
├── .env.example
├── README.md
└── requirements.txt
```

## Architecture

```text
CLI
 │
 ├── PostgreSQL
 │     └── Persistent Job Storage
 │
 └── Redis
       └── Queue
```