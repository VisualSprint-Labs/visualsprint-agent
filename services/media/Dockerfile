# Cloud Run image for the VisualSprint media service.
# Build context is services/media.
FROM python:3.12-slim

# Install ffmpeg for frame extraction before Gemini vision classification.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV PORT=8080 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["sh", "-c", "uvicorn visualsprint_media.main:app --host 0.0.0.0 --port ${PORT}"]
