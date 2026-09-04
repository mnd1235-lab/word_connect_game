"""game.py 단위 테스트 — PRD 6장 상태와 전이."""

import random

import pytest

import game
from game import ChainItem


def start():
    return game.new_game("사과")


# --- new_game ----------------------------------------------------------

def test_new_game_initial_state():
    s = start()
    assert s.chain == [ChainItem("사과", None)]  # 제시어의 player 는 None
    assert s.used_words == {"사과"}
    assert s.current_player == 1
    assert s.required_syllable == "과"
    assert s.last_error is None
    assert s.notice is None
    assert s.phase == "playing"
    assert s.loser_player is None


# --- accept ------------------------------------------------------------

def test_accept_switches_turn_and_updates_syllable():
    s = game.accept(start(), "과일")
    assert s.current_player == 2
    assert s.required_syllable == "일"
    assert s.chain[-1] == ChainItem("과일", 1)
    assert s.used_words == {"사과", "과일"}
    assert s.last_error is None


def test_accept_alternates_players():
    s = game.accept(game.accept(start(), "과일"), "일기")
    assert [item.player for item in s.chain] == [None, 1, 2]
    assert s.current_player == 1


def test_accept_clears_previous_error():
    s = game.reject(start(), "이미 나온 단어예요")
    s = game.accept(s, "과일")
    assert s.last_error is None


def test_accept_carries_notice():
    s = game.accept(start(), "과일", notice="AI 확인 실패 — 통과 처리했어요")
    assert s.notice == "AI 확인 실패 — 통과 처리했어요"


def test_accept_without_notice_clears_it():
    s = game.accept(start(), "과일", notice="알림")
    s = game.accept(s, "일기")
    assert s.notice is None


def test_accept_does_not_mutate_original():
    s0 = start()
    game.accept(s0, "과일")
    assert s0.chain == [ChainItem("사과", None)]
    assert s0.used_words == {"사과"}
    assert s0.current_player == 1
    assert s0.required_syllable == "과"


# --- reject ------------------------------------------------------------

def test_reject_keeps_turn():
    s = game.reject(start(), "사전에 없는 단어예요")
    assert s.current_player == 1  # 차례는 그대로
    assert s.last_error == "사전에 없는 단어예요"
    assert s.required_syllable == "과"
    assert s.chain == [ChainItem("사과", None)]
    assert s.used_words == {"사과"}


def test_reject_does_not_mutate_original():
    s0 = start()
    game.reject(s0, "이미 나온 단어예요")
    assert s0.last_error is None


# --- give_up -----------------------------------------------------------

@pytest.mark.parametrize("moves,expected_loser", [(0, 1), (1, 2), (2, 1)])
def test_give_up_loser_is_the_one_who_pressed(moves, expected_loser):
    s = start()
    for word in ["과일", "일기"][:moves]:
        s = game.accept(s, word)
    s = game.give_up(s)
    assert s.phase == "finished"
    assert s.loser_player == expected_loser


# --- pick_seed_word ----------------------------------------------------

def test_pick_seed_word_is_two_syllables_and_continuable():
    dictionary = {"사과", "과일", "기차", "바다", "일기"}
    for seed in {
        game.pick_seed_word(dictionary, rng=random.Random(i)) for i in range(30)
    }:
        assert len(seed) == 2
        assert seed in dictionary
        assert any(w != seed and w[0] == seed[-1] for w in dictionary)


def test_pick_seed_word_avoids_dead_end():
    # '기차'의 '차'로 시작하는 단어가 없으므로 '기차'는 뽑히면 안 된다.
    dictionary = {"사과", "과일", "기차"}
    for i in range(30):
        assert game.pick_seed_word(dictionary, rng=random.Random(i)) == "사과"


def test_pick_seed_word_excludes_self_reference():
    # '각각'은 '각'으로 시작하지만 자기 자신뿐이므로 이어 갈 수 없다.
    dictionary = {"각각", "사과", "과일"}
    for i in range(30):
        assert game.pick_seed_word(dictionary, rng=random.Random(i)) == "사과"


def test_pick_seed_word_raises_when_no_candidate():
    with pytest.raises(ValueError):
        game.pick_seed_word({"기차", "바다"})
