FROM python:3.12-slim

WORKDIR /app

# Dépendances système pour bcrypt / psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Installe uniquement les dépendances du projet (pas dev)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[postgres]"

COPY . .

# Migrations puis démarrage
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8080"]
