"""rules.py 단위 테스트 — PRD 3장 V1~V5."""

import pytest

import rules

DICT = {"사과", "과일", "기차", "차표"}


def check(text, required="", used=None):
    return rules.check_local(
        rules.normalize(text),
        required_syllable=required,
        used_words=used or set(),
        dictionary=DICT,
    )


# --- V1 한글 음절로만 구성 ---------------------------------------------

@pytest.mark.parametrize(
    "text", ["abc", "사과1", "사 과", "ㄱㄴ", "사과ㅇ", "", "사과!", "１２"]
)
def test_v1_non_hangul_is_invalid(text):
    result = check(text)
    assert result.kind == "invalid"
    assert result.reason == "한글 단어만 쓸 수 있어요"


def test_normalize_strips_outer_space_only():
    assert rules.normalize("  사과  ") == "사과"
    assert rules.normalize(" 사 과 ") == "사 과"


def test_v1_passes_after_trimming_outer_space():
    assert check("  사과  ").kind == "accepted"


# --- V2 2음절 이상 -----------------------------------------------------

def test_v2_single_syllable_is_invalid():
    result = check("산")
    assert result.kind == "invalid"
    assert result.reason == "두 글자 이상이어야 해요"


# --- V3 앞 단어의 마지막 음절로 시작 -----------------------------------

def test_v3_wrong_first_syllable_is_invalid():
    result = check("차표", required="기")
    assert result.kind == "invalid"
    assert result.reason == "'기'로 시작해야 해요"
    assert "기" in result.reason


def test_v3_matching_first_syllable_passes():
    assert check("기차", required="기").kind == "accepted"


def test_v3_no_dueum_rule():
    # 두음법칙은 구현하지 않는다 — '력'을 '역'으로 받아 주지 않는다.
    result = check("역사", required="력")
    assert result.kind == "invalid"
    assert result.reason == "'력'로 시작해야 해요"


# --- V4 이번 판에 아직 안 쓰임 -----------------------------------------

def test_v4_used_word_is_invalid():
    result = check("사과", used={"사과"})
    assert result.kind == "invalid"
    assert result.reason == "이미 나온 단어예요"


# --- 검사 우선순위 -----------------------------------------------------

def test_v1_beats_v3():
    # 한글이 아니면서 요구 음절도 어긴 입력 → V1 문구가 나와야 한다.
    result = check("abc", required="기")
    assert result.reason == "한글 단어만 쓸 수 있어요"


def test_v2_beats_v3():
    result = check("산", required="기")
    assert result.reason == "두 글자 이상이어야 해요"


def test_v3_beats_v4():
    result = check("사과", required="기", used={"사과"})
    assert result.reason == "'기'로 시작해야 해요"


def test_v4_beats_v5():
    # 사전에 없지만 이미 쓴 단어 → LLM으로 넘기지 않는다.
    result = check("햇살", used={"햇살"})
    assert result.kind == "invalid"
    assert result.reason == "이미 나온 단어예요"


# --- V5 사전 조회 ------------------------------------------------------

def test_v5_in_dictionary_is_accepted():
    result = check("과일")
    assert result.kind == "accepted"
    assert result.reason is None


def test_v5_not_in_dictionary_needs_judge():
    result = check("햇살")
    assert result.kind == "needs_judge"
    assert result.reason is None


# --- load_dictionary ---------------------------------------------------

def test_load_dictionary(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("사과\n과일\n\n  기차  \n", encoding="utf-8")
    assert rules.load_dictionary(str(path)) == {"사과", "과일", "기차"}
