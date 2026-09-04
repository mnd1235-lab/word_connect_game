"""끝말잇기 판정 순수 함수.

PRD 3장 유효 조건 V1~V5 를 구현한다.
streamlit 도 openai 도 import 하지 않는다 — 이 모듈만 단위 테스트한다.
"""

import re
from typing import Literal, NamedTuple

__all__ = [
    "CheckKind",
    "LocalCheck",
    "normalize",
    "check_local",
    "load_dictionary",
]

CheckKind = Literal["invalid", "accepted", "needs_judge"]

# V1 — 한글 음절로만 구성. 자모(ㄱ-ㅎ, ㅏ-ㅣ)는 이 범위에 없으므로
# IME 조합이 덜 끝난 입력도 여기서 걸린다.
HANGUL_RE = re.compile(r"^[가-힣]+$")

MSG_NOT_HANGUL = "한글 단어만 쓸 수 있어요"
MSG_TOO_SHORT = "두 글자 이상이어야 해요"
MSG_ALREADY_USED = "이미 나온 단어예요"
MSG_NOT_IN_DICT = "사전에 없는 단어예요"


class LocalCheck(NamedTuple):
    kind: CheckKind
    reason: str | None = None


def normalize(text: str) -> str:
    """앞뒤 공백만 제거한다. 내부 공백은 V1에서 걸러야 하므로 남긴다."""
    return text.strip()


def check_local(
    text: str,
    *,
    required_syllable: str,
    used_words: set[str],
    dictionary: set[str],
) -> LocalCheck:
    """V1 → V2 → V3 → V4 → V5 순서로 검사한다.

    여러 조건을 어겨도 **먼저 걸린 하나만** 반환한다.
    LLM 호출을 아끼는 것이 이 순서의 이유다.
    """
    # V1 한글 음절로만 구성
    if not HANGUL_RE.match(text):
        return LocalCheck("invalid", MSG_NOT_HANGUL)

    # V2 2음절 이상
    if len(text) < 2:
        return LocalCheck("invalid", MSG_TOO_SHORT)

    # V3 앞 단어의 마지막 음절로 시작 (두음법칙 없음 — 정확한 일치만)
    if required_syllable and text[0] != required_syllable:
        return LocalCheck("invalid", f"'{required_syllable}'로 시작해야 해요")

    # V4 이번 판에 아직 안 쓰임
    if text in used_words:
        return LocalCheck("invalid", MSG_ALREADY_USED)

    # V5 사전 기준 명사
    if text in dictionary:
        return LocalCheck("accepted")
    return LocalCheck("needs_judge")


def load_dictionary(path: str = "data/words.txt") -> set[str]:
    """사전 파일을 읽어 단어 집합으로 돌려준다."""
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}
