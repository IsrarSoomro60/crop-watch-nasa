FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.9 /uv /usr/local/bin/uv
WORKDIR /app

# Dependencies first for layer caching (no dev tools in the image).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN useradd --create-home appuser && mkdir -p /app/var && chown appuser /app/var
USER appuser

ENV PATH="/app/.venv/bin:$PATH" DATABASE_PATH=/app/var/cropwatch.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
