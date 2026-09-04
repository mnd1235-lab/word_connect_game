"""끝말잇기 파일럿 — 화면.

PC 모니터를 두 사람이 함께 보는 상황을 전제로 한 단일 화면.
모바일 대응은 하지 않는다(PRD 5장 모바일 조항은 적용 대상 아님).

제출 → 로컬 판정(rules) → 필요하면 LLM 판정(judge) → 상태 전이(game) 순서로 돈다.
Streamlit 은 동기 실행이라 st.spinner 가 도는 동안 화면이 잠긴다.
별도의 'judging' 상태나 중복 제출 방지 로직은 필요 없다 — 넣지 않는다.
"""

import html
import time
from pathlib import Path

import streamlit as st

import game
import judge
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


def start_new_game() -> None:
    """새 판을 연다.

    judge_cache 는 **비우지 않는다** — 같은 단어를 다시 묻지 않기 위해서다.
    이건 판 단위가 아니라 세션 단위 캐시다.
    입력창 위젯 key(word_N)는 지운다. 안 지우면 새 판 첫 턴에
    지난 판의 첫 입력값이 그대로 남아 있다.
    """
    for key in [k for k in st.session_state if k.startswith("word_")]:
        del st.session_state[key]
    st.session_state["game"] = game.new_game(game.pick_seed_word(get_dictionary()))


def get_state() -> game.GameState:
    if "game" not in st.session_state:
        start_new_game()
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
.result {{
  text-align: center;
  font-size: 2.6rem;
  font-weight: 800;
  margin: .4rem 0 1.2rem;
}}
</style>
"""


def read_secret(name: str) -> str:
    """secrets.toml 이나 클라우드 Secrets 에서 값을 읽는다. 없으면 빈 문자열."""
    try:
        return str(st.secrets.get(name, "") or "")
    except Exception:
        return ""


# --- 접근 제한 ---------------------------------------------------------
# Streamlit Community Cloud 앱은 URL만 알면 열린다. 키가 새지는 않지만
# 열린 사람이 단어를 칠 때마다 OpenAI 크레딧이 나간다.
# 뷰어 제한(클라우드 설정)이 1차 방어선이고, 이 게이트가 2차다.

def require_password() -> None:
    """비밀번호가 맞을 때까지 화면을 열지 않는다.

    APP_PASSWORD 가 **설정돼 있지 않으면 통과시키지 않는다.** 설정을 깜빡한
    앱이 조용히 공개되는 것보다, 안 열리는 편이 낫다.
    """
    password = read_secret("APP_PASSWORD")

    if not password:
        st.error(
            "APP_PASSWORD 가 설정되지 않았습니다. "
            "로컬은 .streamlit/secrets.toml, 클라우드는 앱 Secrets 에 넣어 주세요."
        )
        st.stop()

    if st.session_state.get("authed"):
        return

    st.title("끝말잇기")
    with st.form("auth_form"):
        entered = st.text_input("비밀번호", type="password")
        unlocked = st.form_submit_button("들어가기")
    if unlocked:
        if entered == password:
            st.session_state["authed"] = True
            st.rerun()
        st.error("비밀번호가 맞지 않아요")
    st.stop()


# --- 판 종료 -----------------------------------------------------------

def winner_of(state: game.GameState) -> int:
    """진 사람의 반대편이 이긴다."""
    return 2 if state.loser_player == 1 else 1


@st.dialog("게임 종료")
def result_dialog(state: game.GameState) -> None:
    """화면을 갈아끼우지 않고 위에 덮는다(PRD 5장)."""
    st.markdown(
        f'<div class="result">플레이어 {winner_of(state)} 승리</div>',
        unsafe_allow_html=True,
    )
    if st.button("다시 하기", use_container_width=True):
        start_new_game()
        st.rerun()


# --- 제출 처리 ---------------------------------------------------------

def handle_submit(state: game.GameState, raw: str) -> game.GameState:
    """한 번의 제출을 처리해 다음 상태를 돌려준다.

    LLM 호출을 아끼려고 로컬 판정을 먼저 돌린다.
    사전에 있으면 즉시 통과, 규칙 위반이면 즉시 무효, 둘 다 아닐 때만 LLM.
    """
    started = time.perf_counter()
    word = rules.normalize(raw)

    result = rules.check_local(
        word,
        required_syllable=state.required_syllable,
        used_words=state.used_words,
        dictionary=get_dictionary(),
    )

    if result.kind == "invalid":
        next_state = game.reject(state, result.reason)
        path = "local-invalid"
    elif result.kind == "accepted":
        next_state = game.accept(state, word)
        path = "local-accepted"
    else:
        with st.spinner("확인 중..."):
            verdict = judge.judge_word(
                word,
                st.session_state["judge_cache"],
                st.session_state["api_key"],
            )
        if verdict.valid:
            next_state = game.accept(
                state, word, notice=verdict.reason if verdict.fallback else None
            )
        else:
            next_state = game.reject(state, rules.MSG_NOT_IN_DICT)
        path = "llm"

    elapsed = (time.perf_counter() - started) * 1000
    print(f"[submit] {word!r} path={path} {elapsed:.0f}ms")
    return next_state


# --- 화면 --------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="끝말잇기", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)

    require_password()  # 통과 못 하면 여기서 st.stop()

    st.session_state.setdefault("judge_cache", {})
    st.session_state.setdefault("api_key", read_secret("OPENAI_API_KEY"))

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
    input_key = f"word_{len(state.chain)}"
    with st.form("word_form", clear_on_submit=False):
        st.text_input(
            "단어 입력",
            key=input_key,
            placeholder="이어질 단어를 입력하세요",
            label_visibility="collapsed",
            disabled=finished,
        )
        submitted = st.form_submit_button(
            "제출", disabled=finished, use_container_width=True
        )

    if submitted and not finished:
        st.session_state["game"] = handle_submit(
            state, st.session_state.get(input_key, "")
        )
        st.rerun()

    # 무효 사유와 알림은 입력창 아래에 한 줄씩
    if state.last_error:
        st.error(state.last_error)
    if state.notice:
        st.info(state.notice)

    # 포기 — 누른 사람이 진다. 확인 대화상자는 두지 않는다(파일럿).
    if st.button("포기", key="give_up", disabled=finished):
        st.session_state["game"] = game.give_up(state)
        st.rerun()

    if finished:
        result_dialog(state)


if __name__ == "__main__":
    main()
