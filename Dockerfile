FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pytest.ini .
COPY src/ src/
COPY tests/ tests/

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["pytest", "tests/test_harness.py", "-v"]
