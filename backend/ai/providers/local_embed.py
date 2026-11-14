"""로컬 임베딩 (sentence-transformers + BAAI/bge-m3, 1024차원).

처음 호출할 때 모델(약 2GB)을 내려받아요. 컨테이너에서는 hf_cache 볼륨에 저장돼서 다시 받지 않아요.
"""

import threading

from ai.providers.base import AIError


class LocalEmbedder:
    name = "local"

    def __init__(self, model_name: str, dim: int) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model = None
        self._lock = threading.Lock()

    def _load(self):  # noqa: ANN202
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as e:
                        raise AIError("sentence-transformers가 설치돼 있지 않아요 (pip install -e '.[embeddings]')") from e
                    self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        if vectors.shape[1] != self.dim:
            raise AIError(f"임베딩 차원이 맞지 않아요: {vectors.shape[1]} != {self.dim}")
        return vectors.tolist()
