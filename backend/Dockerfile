FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# place seed CSVs/docs where the app expects them (app/data)
COPY data ./app/data
COPY .env.example ./.env

# ensure data/uploads remain writable at runtime
RUN mkdir -p /app/app/data/uploads

RUN adduser --disabled-login --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
