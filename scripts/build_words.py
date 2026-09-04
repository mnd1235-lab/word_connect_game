"""data/raw/*.txt 를 모아 data/words.txt 를 만든다.

  python scripts/build_words.py

필터: 한글 음절로만 구성된 2음절 이상 단어 → 중복 제거 → 정렬.
끝에 총 단어 수와 '막다른 음절'(그 음절로 끝나는 단어는 있는데
그 음절로 시작하는 단어가 없는 음절) 상위 30개를 출력한다.
"""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = ROOT / "data" / "words.txt"

WORD_RE = re.compile(r"^[가-힣]{2,}$")


def collect(raw_dir: Path) -> set[str]:
    words: set[str] = set()
    for path in sorted(raw_dir.glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if WORD_RE.match(token):
                words.add(token)
    return words


def dead_end_syllables(words: set[str]) -> list[tuple[str, int]]:
    """이어 갈 단어가 없는 끝 음절을 많이 등장하는 순으로."""
    starts = {w[0] for w in words}
    tail_counts = Counter(w[-1] for w in words)
    dead = [(syl, n) for syl, n in tail_counts.items() if syl not in starts]
    dead.sort(key=lambda item: (-item[1], item[0]))
    return dead


def main() -> None:
    if not RAW_DIR.is_dir():
        raise SystemExit(f"원천 폴더가 없습니다: {RAW_DIR}")

    words = collect(RAW_DIR)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(sorted(words)) + "\n", encoding="utf-8")

    dead = dead_end_syllables(words)
    dead_total = sum(n for _, n in dead)

    print(f"총 단어 수: {len(words)}")
    print(f"막다른 음절: {len(dead)}종 / 그 음절로 끝나는 단어 {dead_total}개")
    print("막다른 음절 상위 30 (음절 x 그 음절로 끝나는 단어 수):")
    for syl, n in dead[:30]:
        print(f"  {syl} x{n}")


if __name__ == "__main__":
    main()
