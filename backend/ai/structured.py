"""LLM 호출 → JSON 파싱 → Pydantic 검증. 실패하면 1회 재시도하고, 그래도 안 되면 AIError."""

import logging
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ai.factory import get_llm
from ai.providers.base import AIError

log = logging.getLogger("ai")
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(feature: str) -> str:
    return (PROMPTS_DIR / f"{feature}.md").read_text(encoding="utf-8")


T = TypeVar("T", bound=BaseModel)


def generate(feature: str, user: str, schema: type[T], *, max_attempts: int = 2) -> T:
    llm = get_llm()
    system = load_prompt(feature)
    json_schema = schema.model_json_schema()
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            raw = llm.generate_json(feature=feature, system=system, user=user, json_schema=json_schema)
            result = schema.model_validate_json(raw)
            log.info("ai ok feature=%s provider=%s attempt=%d %.0fms", feature, llm.name, attempt, (time.monotonic() - started) * 1000)
            return result
        except ValidationError as e:
            last_error = e
            log.warning("ai invalid feature=%s attempt=%d: %s", feature, attempt, e.errors()[:3])
        except AIError as e:
            last_error = e
            log.warning("ai error feature=%s attempt=%d: %s", feature, attempt, e)

    if isinstance(last_error, AIError):
        raise last_error
    raise AIError("AI 응답을 이해하지 못했어요. 다시 시도해 주세요", feature=feature) from last_error
