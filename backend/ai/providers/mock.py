"""AI_MOCK=true일 때 쓰는 provider. 외부 호출 없이 항상 같은 결과를 내요."""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from ai.providers.base import AIError

MOCKS_DIR = Path(__file__).resolve().parent.parent / "mocks"


class MockLLM:
    name = "mock"

    def generate_json(self, *, feature: str, system: str, user: str, json_schema: dict[str, Any]) -> str:  # noqa: ARG002
        path = MOCKS_DIR / f"{feature}.json"
        if not path.exists():
            raise AIError(f"'{feature}' 기능의 mock 응답 파일이 없어요: {path.name}", feature=feature)
        return path.read_text(encoding="utf-8")


class MockEmbedder:
    """글자 n-gram 해싱 임베딩.

    의미를 이해하진 못하지만, 'PPT', '엑셀'처럼 같은 단어가 들어간 문장끼리는 유사도가 높게 나와서
    키 없이도 매칭 데모가 그럴듯하게 돌아가요.
    """

    name = "mock-ngram"

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        norm_text = re.sub(r"\s+", " ", text.lower()).strip()
        grams: list[str] = []
        for token in norm_text.split(" "):
            grams.append(f"w:{token}")
            padded = f" {token} "
            for n in (2, 3):
                grams.extend(padded[i : i + n] for i in range(len(padded) - n + 1))
        for g in grams:
            h = int.from_bytes(hashlib.md5(g.encode("utf-8")).digest()[:8], "big")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        length = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / length for x in v]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


def load_mock(feature: str) -> Any:
    return json.loads((MOCKS_DIR / f"{feature}.json").read_text(encoding="utf-8"))
