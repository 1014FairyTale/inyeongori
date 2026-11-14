"""Gemini 임베딩 API (gemini-embedding-001). 배포 환경용 — 로컬 bge-m3처럼 메모리를 쓰지 않아요.

1024차원으로 받아서 DB의 vector(1024)와 그대로 맞아요. 3072 미만 차원은 정규화돼서 오지 않으니 직접 정규화해요.
"""

import math

from google import genai
from google.genai import errors, types

from ai.providers.base import AIError

BATCH = 100
TIMEOUT_MS = 30_000


class GeminiEmbedder:
    name = "gemini-embed"

    def __init__(self, api_key: str, model: str, dim: int) -> None:
        if not api_key:
            raise AIError("GEMINI_API_KEY가 비어 있어요. 임베딩에도 Gemini 키가 필요해요")
        self.model = model
        self.dim = dim
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))

    @staticmethod
    def _normalize(v: list[float]) -> list[float]:
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            chunk = texts[i : i + BATCH]
            try:
                resp = self._client.models.embed_content(
                    model=self.model,
                    contents=chunk,
                    config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY", output_dimensionality=self.dim),
                )
            except errors.APIError as e:
                raise AIError(f"임베딩 요청이 실패했어요 (Gemini {e.code})", feature="embedding") from e
            except Exception as e:
                raise AIError("임베딩 서버에 연결하지 못했어요", feature="embedding") from e
            if not resp.embeddings or len(resp.embeddings) != len(chunk):
                raise AIError("임베딩 응답이 올바르지 않아요", feature="embedding")
            out.extend(self._normalize(list(e.values or [])) for e in resp.embeddings)
        if out and len(out[0]) != self.dim:
            raise AIError(f"임베딩 차원이 맞지 않아요: {len(out[0])} != {self.dim}")
        return out
