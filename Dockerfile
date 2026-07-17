FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (e.g. for psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

# Default command (can be overridden by docker-compose)
CMD ["queuectl", "--help"]
