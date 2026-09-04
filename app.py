"""끝말잇기 파일럿 — 화면.

PC 모니터를 두 사람이 함께 보는 상황을 전제로 한 단일 화면.
모바일 대응은 하지 않는다(PRD 5장 모바일 조항은 적용 대상 아님).

5단계에서는 표시와 입력 폼까지만 만든다. 제출 처리는 6단계에서 붙인다.
"""

import html
from pathlib import Path

import streamlit as st

import game
import rules

# --- 색상 상수 ---------------------------------------------------------
# 두 사람이 1미터 떨어져서도 "지금 누구 차례인가"를 알아야 한다.
# 글자 크기만으로는 부족해서 배경색도 함께 바꾼다.
PLAYER_COLORS = {
    1: {"bg": "#1d4ed8", "fg": "#ffffff"},  # 파랑
    2: {"bg": "#c2410c", "fg": "#ffffff"},  # 주황
}
FINISHED_COLOR = {"bg": "#374151", "fg": "#ffffff"}
ACCENT = "#dc2626"  # 이어야 할 음절 강조
MUTED = "#6b7280"

DICT_PATH = Path(__file__).resolve().parent / "data" / "words.txt"
VISIBLE_HISTORY = 10  # 접지 않고 보여 줄 지난 단어 수


# --- 자원 로드 ---------------------------------------------------------

@st.cache_resource
def get_dictionary() -> set[str]:
    return rules.load_dictionary(str(DICT_PATH))


def get_state() -> game.GameState:
    if "game" not in st.session_state:
        seed = game.pick_seed_word(get_dictionary())
        st.session_state["game"] = game.new_game(seed)
    return st.session_state["game"]


# --- 마크업 만들기 (streamlit 없이도 부를 수 있게 순수 함수로) ----------

def banner_html(state: game.GameState) -> str:
    if state.phase == "finished":
        color = FINISHED_COLOR
        label = "판이 끝났어요"
    else:
        color = PLAYER_COLORS[state.current_player]
        label = f"플레이어 {state.current_player} 차례"
    return (
        f'<div class="turn-banner" style="background:{color["bg"]};'
        f'color:{color["fg"]}">{html.escape(label)}</div>'
    )


def current_word_html(state: game.GameState) -> str:
    """최신 단어를 크게, 이어야 할 마지막 음절을 색과 굵기로 강조한다."""
    word = state.chain[-1].word
    head, tail = html.escape(word[:-1]), html.escape(word[-1])
    return (
        '<div class="current-word">'
        f"{head}<span class='tail'>{tail}</span>"
        "</div>"
        f'<div class="hint">다음 단어는 <b>{tail}</b>(으)로 시작해요</div>'
    )


def history_html(items: list[game.ChainItem]) -> str:
    """지난 단어를 최신순으로 작게 쌓는다."""
    if not items:
        return ""
    rows = []
    for item in reversed(items):
        who = "제시어" if item.player is None else f"P{item.player}"
        rows.append(
            f'<div class="history-row"><span class="who">{who}</span>'
            f"<span class='word'>{html.escape(item.word)}</span></div>"
        )
    return '<div class="history">' + "".join(rows) + "</div>"


CSS = f"""
<style>
.turn-banner {{
  text-align: center;
  font-size: 4.2rem;
  font-weight: 800;
  letter-spacing: .06em;
  padding: 1.1rem 0;
  border-radius: 14px;
  margin-bottom: 1.6rem;
}}
.current-word {{
  text-align: center;
  font-size: 4.6rem;
  font-weight: 800;
  line-height: 1.15;
  margin: .2rem 0 .1rem;
}}
.current-word .tail {{ color: {ACCENT}; font-weight: 900; }}
.hint {{
  text-align: center;
  font-size: 1.15rem;
  color: {MUTED};
  margin-bottom: 1.4rem;
}}
.hint b {{ color: {ACCENT}; }}
.history {{ margin: 0 0 1.2rem; }}
.history-row {{
  display: flex; gap: .7rem; align-items: baseline;
  padding: .12rem 0; font-size: 1.05rem; color: {MUTED};
}}
.history-row .who {{
  min-width: 3.2rem; font-size: .8rem; opacity: .75;
}}
.history-row .word {{ color: var(--text-color, #111827); font-weight: 600; }}
div[data-testid="stForm"] input {{ font-size: 1.6rem !important; }}
</style>
"""


def _read_api_key() -> str:
    """secrets 가 아직 없어도 화면은 뜨게 한다. 실제 사용은 6단계."""
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


# --- 화면 --------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="끝말잇기", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)

    st.session_state.setdefault("judge_cache", {})
    # 키는 6단계에서 judge_word 에 넘긴다. 여기서는 읽어 두기만 한다.
    st.session_state.setdefault("api_key", _read_api_key())

    state = get_state()
    finished = state.phase == "finished"

    # 상단 — 턴 배너
    st.markdown(banner_html(state), unsafe_allow_html=True)

    # 중앙 — 단어 체인
    st.markdown(current_word_html(state), unsafe_allow_html=True)
    history = state.chain[:-1]
    st.markdown(history_html(history[-VISIBLE_HISTORY:]), unsafe_allow_html=True)
    if len(history) > VISIBLE_HISTORY:
        older = history[:-VISIBLE_HISTORY]
        with st.expander(f"지난 단어 {len(older)}개 더 보기"):
            st.markdown(history_html(older), unsafe_allow_html=True)

    # 하단 — 입력 폼
    # key 에 체인 길이를 붙인다. 턴이 넘어가면 key 가 바뀌어 새 위젯이 되므로
    # 입력창이 자동으로 비고, 무효면 같은 key 라 값이 남는다(PRD 5장).
    with st.form("word_form", clear_on_submit=False):
        st.text_input(
            "단어 입력",
            key=f"word_{len(state.chain)}",
            placeholder="이어질 단어를 입력하세요",
            label_visibility="collapsed",
            disabled=finished,
        )
        st.form_submit_button("제출", disabled=finished, use_container_width=True)
        # 6단계에서 이 반환값으로 판정 파이프라인을 돌린다.

    # 무효 사유와 알림은 입력창 아래에 한 줄씩
    if state.last_error:
        st.error(state.last_error)
    if state.notice:
        st.info(state.notice)

    st.button("포기", key="give_up", disabled=finished)
    # 7단계에서 game.give_up 을 붙인다.


if __name__ == "__main__":
    main()
