# 끝말잇기 파일럿 — 프로젝트 지침

이 파일은 이 저장소에서 작업하는 모든 세션이 **먼저 읽는** 전제 모음이다.
혼동이 반복되는 지점만 적는다. 세부 사양은 아래 두 문서가 원본이다.

## 문서 위계

1. `끝말잇기 파일럿 PRD v0.1.md` — **유일한 사양서.** 규칙·상태·화면 정의는 여기가 원본.
2. `구현-프롬프트.md` — 0~9단계 실행 계획. 단계별 지시문과 커밋 메시지가 들어 있다.
3. 이 파일(`CLAUDE.md`) — 위 둘과 실제 구현 사이의 **차이와 현황**.

충돌하면 PRD가 이긴다. 단 아래 "PRD와 달라지는 것"은 예외다.

## PRD와 달라지는 것 (2026-09-04 확정)

- **스택.** PRD 6장은 React + TypeScript + Vite로 적혀 있으나, 실제 구현은
  **Python + Streamlit**이다. 판정 로직과 상태 정의는 PRD 그대로 유지한다.
  (PRD 6장 첫머리에 같은 취지의 각주를 넣어 두었다.)
- **프록시 조항 삭제.** 파이썬이 서버에서 도니까 API 키가 브라우저로 갈 경로가 없다.
  PRD 4장의 "개발 서버 프록시 경유"는 적용 대상이 아니다.
- **새 위험: 공개 URL.** 배포처인 Streamlit Community Cloud는 기본이 공개 URL이다.
  키는 안 새지만 URL을 아는 누구나 OpenAI 크레딧을 쓸 수 있다.
  8단계에서 뷰어 제한 + 비밀번호 게이트 + 사용량 상한을 **모두** 건다. 선택이 아니다.
- **모바일 조항 제외.** PC 한 화면에서 두 사람이 번갈아 플레이한다.
  PRD 5장의 `compositionstart`/`compositionend`, 7장의 모바일 입력 조항은 적용하지 않는다.
  데스크톱 IME의 Enter 조합 문제는 `rules.py`의 V1 정규식이 자모를 걸러 처리한다.
  **별도 IME 처리 코드를 넣지 않는다.**

## 절대 만들지 않는 것

PRD "범위" 표에서 제외로 표시된 것들. 코드에 흔적도 남기지 않는다.

타이머 · 두음법칙 · 3인 이상 · 한방단어 처리 · 탈락 카운트 ·
뜻풀이 · PWA · 결과 통계/기록 화면

## 파일 지도

```
app.py                  Streamlit 화면 (5단계)
rules.py                판정 순수 함수 V1~V5 (2단계) — streamlit/openai import 금지
judge.py                LLM 질의 (3단계) — streamlit import 금지, api_key는 호출자가 주입
game.py                 GameState와 전이 (4단계) — 모든 전이는 새 상태를 반환하는 순수 함수
data/words.txt          사전 (1단계). 배포에 필요하므로 반드시 커밋한다
data/raw/*.txt          사전 원천, 카테고리별
scripts/build_words.py  raw → words.txt 생성 + 막다른 음절 통계
tests/                  pytest. rules.py와 game.py만 테스트한다
.streamlit/secrets.toml 로컬 비밀값 (커밋 금지). 클라우드는 대시보드 Secrets
pytest.ini              pythonpath=. (테스트에서 루트 모듈 import용)
```

## 코딩 규약

- **판정 순서는 V1 → V2 → V3 → V4 → V5.** 여러 조건을 어겨도 먼저 걸린 하나만 반환한다.
  LLM 호출을 아끼는 것이 이 순서의 이유다.
- **무효 사유는 한 줄, 하나만.** 여러 줄을 쌓지 않는다.
- **LLM 실패는 통과 처리.** 타임아웃·네트워크 오류·JSON 파싱 실패는 예외를 던지지 말고
  `valid=True, fallback=True`로 돌려준다. 억울하게 막는 것보다 느슨하게 통과시킨다.
  이때 메시지는 에러가 아니라 알림(`notice`)으로 띄운다.
- **reject는 차례를 넘기지 않는다.** accept만 `current_player`를 바꾼다.
- `judge_cache`는 **세션 단위**다. '다시 하기'로 판이 바뀌어도 비우지 않는다.
- 비밀값은 항상 `st.secrets` 우선. `python-dotenv`와 `.env`는 쓰지 않는다.

## 밟기 쉬운 함정

- **`secrets.toml` 은 BOM 없는 UTF-8이어야 한다.** Windows PowerShell 5.1의
  `Set-Content -Encoding utf8` 은 파일 앞에 BOM 3바이트를 붙이고, TOML 파서가
  첫 줄부터 실패한다. 증상은 "키가 죽은 것처럼 보임"이다. 다시 만들 때는
  `[IO.File]::WriteAllText($f, $t, (New-Object Text.UTF8Encoding $false))` 를 쓴다.
  확인: `python -c "import tomllib; print(list(tomllib.load(open('.streamlit/secrets.toml','rb'))))"`
- **키를 못 읽으면 조용히 다 통과된다.** `judge.py` 는 실패를 통과로 처리하므로,
  키가 비어 있으면 사전에 없는 단어가 전부 "AI 확인 실패 — 통과 처리했어요"로
  넘어간다. 판정이 이상하게 관대하면 키부터 확인한다.

## 알려진 한계

- **막다른 음절.** 두음법칙을 구현하지 않으므로 `력·름·락·래·류·니·루·람` 등으로 끝나는
  단어는 이어 갈 수 없다. 사전 보강으로 152종 → 109종까지 줄였고 나머지는 구조적이다.
  어휘를 더 넣어도 줄지 않는다. 파일럿에서 실제 빈도를 보고 판단한다.

## 진행 현황

| 단계 | 산출물 | 상태 |
| --- | --- | --- |
| 0 | 파이썬 스캐폴드, secrets 구조 | 완료 |
| 1 | `data/words.txt` (4,311개) | 완료 |
| 2 | `rules.py` + 테스트 | 완료 |
| 3 | `judge.py` | 완료 |
| 4 | `game.py` + 테스트 | 완료 |
| 5 | `app.py` 화면 | 완료 (표시·입력 폼까지) |
| 6 | 판정 파이프라인 결선 | 완료 |
| 7 | 포기·승패·다시 하기 | 완료 |
| 8 | Cloud 배포 · 접근 제한 | 코드 완료, 배포는 수동 |
| 9 | 완료 조건 점검 · 기록지 | — |

단계를 끝낼 때마다 `구현-프롬프트.md`에 적힌 커밋 메시지로 커밋하고 이 표를 갱신한다.

## 작업 환경 메모

- 개발 PC는 Windows / PowerShell. 프로젝트 폴더는 `Desktop\끝말잇기`.
- 로컬 실행: `.\.venv\Scripts\Activate.ps1` → `streamlit run app.py`
- 테스트: 루트에서 `python -m pytest`
- 사전 재생성: `python scripts\build_words.py`
- 요청한 파일 외에는 건드리지 않는다. 작업이 끝나면 변경 파일 목록과 확인 방법만 짧게 보고한다.
