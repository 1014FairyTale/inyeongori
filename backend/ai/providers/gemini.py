"""Google Gemini (AI Studio 무료 등급) LLM provider."""

from typing import Any

from google import genai
from google.genai import errors, types

from ai.providers.base import AIError

TIMEOUT_MS = 60_000


class GeminiLLM:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise AIError("GEMINI_API_KEY가 비어 있어요. .env에 키를 넣거나 AI_MOCK=true로 실행해 주세요")
        self.model = model
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))

    def generate_json(self, *, feature: str, system: str, user: str, json_schema: dict[str, Any]) -> str:
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=json_schema,
                    temperature=0.4,
                ),
            )
        except errors.ClientError as e:  # 4xx: 키 오류, 무료 한도 초과(429) 등
            msg = "AI 무료 사용 한도를 넘었어요. 잠시 후 다시 시도해 주세요" if e.code == 429 else "AI 요청이 거부됐어요"
            raise AIError(f"{msg} (Gemini {e.code})", feature=feature) from e
        except errors.APIError as e:  # 5xx 등
            raise AIError(f"AI 서버에 문제가 생겼어요 (Gemini {e.code})", feature=feature) from e
        except Exception as e:  # 네트워크·타임아웃
            raise AIError("AI 서버에 연결하지 못했어요", feature=feature) from e

        text = resp.text
        if not text:
            raise AIError("AI가 빈 응답을 보냈어요", feature=feature)
        return text
