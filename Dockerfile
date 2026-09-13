FROM python:3.12-slim

WORKDIR /srv

# git is needed to install the pinned aiforge-core tag
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY prompts ./prompts
COPY samples ./samples
COPY static ./static
COPY migrations ./migrations

# demo extra = aiforge-core[embeddings] -> real MiniLM embeddings in the image
RUN pip install --no-cache-dir ".[demo]"

ENV EMBEDDER=minilm

EXPOSE 8000

# production_app() runs migrations and loads the sample catalog idempotently
CMD ["sh", "-c", "uvicorn app.main:production_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
