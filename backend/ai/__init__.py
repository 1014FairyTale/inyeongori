"""AI 모듈. LLM·임베딩 호출은 반드시 이 패키지의 provider를 통해서만 해요.

- providers/base.py : 공급사와 무관한 인터페이스
- providers/mock.py : AI_MOCK=true일 때 쓰는 고정 응답
- prompts/          : 프롬프트 파일 (4단계부터 추가)
- mocks/            : 기능별 고정 예시 응답 JSON (4단계부터 추가)
"""

from ai.factory import get_embedder, get_llm

__all__ = ["get_embedder", "get_llm"]
