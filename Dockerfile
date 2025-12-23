FROM python:3.14-slim

WORKDIR /app

# Install ffmpeg for audio conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY bbc2podcast ./bbc2podcast

# Install dependencies
RUN uv sync --frozen --no-dev

# Create data directory
RUN mkdir -p /app/data/audio

ENV PROGRAMME_ID=b00v4tv3

EXPOSE 5000

# Default: run uvicorn server
# Manual update: docker compose exec bbc2podcast uv run python -m bbc2podcast.update
CMD ["uv", "run", "uvicorn", "bbc2podcast.app:app", "--host", "0.0.0.0", "--port", "5000"]
