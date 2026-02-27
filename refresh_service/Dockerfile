FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency definition first (cache layer)
COPY pyproject.toml .

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY main.py .
COPY app/ app/

EXPOSE 8331

CMD ["uv", "run", "main.py"]
