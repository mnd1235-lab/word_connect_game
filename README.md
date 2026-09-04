# 끝말잇기 파일럿

PC 한 화면에서 두 사람이 번갈아 하는 끝말잇기. 로컬 사전으로 먼저 판정하고,
사전에 없는 단어만 LLM에 물어본다.

사양은 `끝말잇기 파일럿 PRD v0.1.md`, 작업 전제는 `CLAUDE.md`를 본다.

## 로컬 실행

```powershell
py -3.12 -m venv .venv                  # 설치된 파이썬 버전에 맞춘다
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

비밀값은 `.streamlit/secrets.toml`에 넣는다. `.streamlit/secrets.toml.example`을
복사해 값을 채우면 된다.

```toml
OPENAI_API_KEY = "sk-..."
APP_PASSWORD = "..."
```

> **BOM 주의.** 이 파일은 BOM 없는 UTF-8이어야 한다. PowerShell 5.1의
> `Set-Content -Encoding utf8`은 BOM을 붙이고, 그러면 TOML 파싱이 첫 줄부터
> 실패해 "키가 죽은 것처럼" 보인다. `[IO.File]::WriteAllText`로 쓰거나
> 에디터에서 "UTF-8 (BOM 없음)"으로 저장한다.

```powershell
streamlit run app.py
```

## 사전 다시 만들기

`data/raw/*.txt`를 고친 뒤:

```powershell
python scripts\build_words.py
```

총 단어 수와 막다른 음절 통계가 함께 출력된다. `data/words.txt`는
**반드시 커밋한다** — 저장소에 없으면 클라우드에서 앱이 죽는다.

## 테스트

```powershell
python -m pytest -q
```

## 배포 앱

- URL: (배포 후 여기에 적는다)
- **비공개 앱이고 비밀번호 게이트가 걸려 있다.** URL만으로는 들어갈 수 없다.
- **한동안 아무도 안 들어가면 앱이 잠든다.** 다시 열 때 첫 화면이 뜨기까지
  수십 초가 걸릴 수 있다. 고장이 아니다. 시연 전에는 미리 한 번 열어 깨워 둔다.

## 아직 없는 것

PRD "범위" 표에서 제외로 둔 것들 — 타이머, 두음법칙, 3인 이상, 한방단어 처리,
탈락 카운트, 뜻풀이, PWA, 결과 통계 화면. 파일럿 결과를 보고 정한다.
