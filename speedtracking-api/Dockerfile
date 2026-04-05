# ─── speedtracking-api — dev image (CPU-only) ────────────────────────────────
# Production GPU image: FROM nvidia/cuda:12.1-runtime-ubuntu22.04
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BALL_DETECTOR_MODEL=/models/cricket_ball_best.pt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
