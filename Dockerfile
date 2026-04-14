FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .
COPY app/ app/
COPY web_client/ web_client/

RUN uv sync --no-dev

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6567", "--ssl-certfile", "/certs/cert.pem", "--ssl-keyfile", "/certs/key.pem"]
