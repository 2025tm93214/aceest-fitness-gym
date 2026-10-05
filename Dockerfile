# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ACEEST_DB=/data/aceest_fitness.db \
    PYTEST_ADDOPTS="-p no:cacheprovider"

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py setup.cfg ./
COPY tests ./tests

# Run as a non-root user and give it a writable data directory
RUN useradd --create-home appuser \
    && mkdir /data \
    && chown appuser:appuser /data
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
