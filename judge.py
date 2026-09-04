"""LLM 판정 모듈.

사전(`data/words.txt`)에 없는 단어만 여기로 넘어온다.
streamlit 을 직접 import 하지 않는다 — API 키와 캐시는 호출자가 넘긴다.
그래야 이 모듈을 단독으로 테스트하거나 나중에 다른 프론트로 옮길 수 있다.
"""

import json
import time
from dataclasses import dataclass

__all__ = ["JudgeResult", "judge_word", "MODEL", "TIMEOUT_SECONDS"]

MODEL = "gpt-4o-mini"
TIMEOUT_SECONDS = 3.0
MAX_TOKENS = 100

FALLBACK_REASON = "AI 확인 실패 — 통과 처리했어요"

SYSTEM_PROMPT = (
    "너는 한국어 사전 판정기다. 주어진 단어가 표준국어대사전 표제어에 있는 "
    "'명사'인지 판정하라. 고유명사·방언·옛말·북한어·띄어쓰기가 있는 구(句)는 "
    "인정하지 않는다. "
    '{"valid": bool, "reason": str} 형식의 JSON만 출력하라. '
    "reason 은 한국어 한 줄로 짧게 쓴다."
)


@dataclass
class JudgeResult:
    valid: bool
    reason: str
    fallback: bool = False  # 타임아웃/실패로 통과 처리된 경우 True


def _fallback() -> JudgeResult:
    return JudgeResult(valid=True, reason=FALLBACK_REASON, fallback=True)


def _make_client(api_key: str):
    # openai 는 함수 안에서 import 한다 — 패키지 없이도 이 모듈을 import 할 수 있게.
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS)


def judge_word(
    word: str,
    cache: dict[str, JudgeResult],
    api_key: str,
    *,
    client=None,
) -> JudgeResult:
    """단어가 사전 표제어인지 LLM에 묻는다.

    - 캐시에 있으면 API를 부르지 않는다.
    - 타임아웃·네트워크 오류·JSON 파싱 실패는 예외를 던지지 않고 통과 처리한다.
      억울하게 막는 것보다 느슨하게 통과시키는 것이 파일럿 방침이다.
    - 결과는 fallback 이든 아니든 반드시 캐시에 넣는다.
    """
    started = time.perf_counter()

    if word in cache:
        elapsed = (time.perf_counter() - started) * 1000
        result = cache[word]
        print(f"[judge] {word} path=cache {elapsed:.0f}ms valid={result.valid}")
        return result

    try:
        if client is None:
            client = _make_client(api_key)
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": word},
            ],
        )
        payload = json.loads(response.choices[0].message.content)
        result = JudgeResult(
            valid=bool(payload["valid"]),
            reason=str(payload.get("reason") or "").strip() or "사전에 없는 단어예요",
        )
        path = "llm"
    except Exception as exc:  # 타임아웃·네트워크·파싱 실패를 모두 여기서 흡수한다
        result = _fallback()
        path = f"llm-fallback({type(exc).__name__})"

    cache[word] = result
    elapsed = (time.perf_counter() - started) * 1000
    print(f"[judge] {word} path={path} {elapsed:.0f}ms valid={result.valid}")
    return result
