FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 임베딩(bge-m3)용 PyTorch는 CPU 전용 빌드를 먼저 깔아요. (기본 빌드는 GPU용이라 수 GB가 더 커요)
# 이미지를 가볍게 하려면: docker compose build --build-arg INSTALL_EMBEDDINGS=false
ARG INSTALL_EMBEDDINGS=true
RUN if [ "$INSTALL_EMBEDDINGS" = "true" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu torch; \
    fi

COPY pyproject.toml ./
# 의존성만 먼저 설치해서 빌드 캐시를 살려요
RUN mkdir -p app ai && touch app/__init__.py ai/__init__.py \
    && EXTRAS="dev,gemini" \
    && if [ "$INSTALL_EMBEDDINGS" = "true" ]; then EXTRAS="$EXTRAS,embeddings"; fi \
    && pip install -e ".[$EXTRAS]" \
    && rm -rf app ai

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
