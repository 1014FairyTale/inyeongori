FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
# 의존성만 먼저 설치해서 빌드 캐시를 살려요
RUN mkdir -p app ai && touch app/__init__.py ai/__init__.py \
    && pip install -e ".[dev]" \
    && rm -rf app ai

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
