"""게임 상태와 전이.

PRD 6장 GameState 를 파이썬으로 옮긴 것.
Streamlit 의 rerun 에 휘둘리지 않도록 전이는 모두
**새 GameState 를 반환하는 순수 함수**로 둔다. 상태를 제자리에서 바꾸지 않는다.
"""

import random
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Literal

__all__ = [
    "Phase",
    "ChainItem",
    "GameState",
    "new_game",
    "accept",
    "reject",
    "give_up",
    "pick_seed_word",
]

Phase = Literal["playing", "finished"]


@dataclass(frozen=True)
class ChainItem:
    word: str
    player: int | None  # 제시어는 None


@dataclass
class GameState:
    chain: list[ChainItem] = field(default_factory=list)
    used_words: set[str] = field(default_factory=set)
    current_player: int = 1  # 1 또는 2
    required_syllable: str = ""
    last_error: str | None = None  # 무효 사유 (한 줄)
    notice: str | None = None  # "AI 확인 실패 — 통과 처리했어요" 같은 알림
    phase: Phase = "playing"
    loser_player: int | None = None


def new_game(seed_word: str) -> GameState:
    """제시어 하나로 새 판을 연다. 언제나 플레이어 1부터 시작한다."""
    return GameState(
        chain=[ChainItem(seed_word, None)],
        used_words={seed_word},
        current_player=1,
        required_syllable=seed_word[-1],
        last_error=None,
        notice=None,
        phase="playing",
        loser_player=None,
    )


def accept(state: GameState, word: str, notice: str | None = None) -> GameState:
    """유효한 단어를 받아 차례를 넘긴다."""
    return replace(
        state,
        chain=[*state.chain, ChainItem(word, state.current_player)],
        used_words={*state.used_words, word},
        current_player=_other(state.current_player),
        required_syllable=word[-1],
        last_error=None,
        notice=notice,
    )


def reject(state: GameState, reason: str) -> GameState:
    """무효 사유만 세우고 **차례는 그대로 유지한다.**"""
    return replace(state, last_error=reason, notice=None)


def give_up(state: GameState) -> GameState:
    """포기한 사람이 진다."""
    return replace(
        state,
        phase="finished",
        loser_player=state.current_player,
        last_error=None,
        notice=None,
    )


def pick_seed_word(dictionary: set[str], rng: random.Random | None = None) -> str:
    """제시어를 고른다.

    2음절이고, 사전에 있고, **그 마지막 음절로 시작하는 다른 단어가 사전에 있는**
    단어 중에서 무작위로. 첫 수부터 막히면 안 된다.
    """
    # 첫 음절 빈도를 한 번만 세고 쓴다 — 후보마다 사전을 훑으면 느리다.
    start_counts = Counter(w[0] for w in dictionary)
    candidates = [
        w
        for w in dictionary
        # 자기 자신은 이미 쓴 단어이므로 이어 갈 후보에서 뺀다.
        if len(w) == 2 and start_counts[w[-1]] - (1 if w[0] == w[-1] else 0) > 0
    ]
    if not candidates:
        raise ValueError("제시어로 쓸 만한 2음절 단어가 사전에 없습니다")
    picker = rng or random
    return picker.choice(sorted(candidates))


def _other(player: int) -> int:
    return 2 if player == 1 else 1
