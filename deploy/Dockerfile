# The VocabBot server. Build from the repository root:
#   docker compose -f deploy/compose.yaml up -d --build
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install ".[server]" && rm -rf /build

RUN useradd --system --uid 10001 --home-dir /data --no-create-home vocabbot \
    && mkdir -p /data && chown vocabbot:vocabbot /data
USER vocabbot
WORKDIR /data

# only the reverse proxy reaches the container, so it may set X-Forwarded-For
ENV VOCABBOT_SERVER_DATA=/data \
    VOCABBOT_SERVER_HOST=0.0.0.0 \
    VOCABBOT_SERVER_PORT=8000 \
    VOCABBOT_SERVER_PROXIES=*

EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]
CMD ["vocabbot-server", "serve"]
