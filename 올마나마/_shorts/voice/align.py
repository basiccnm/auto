# 목소리 → 단어별 타임스탬프 (2026-07-22)
#
# 🔴 왜 필요한가: Talk.jsx의 `parts`는 한 대사가 읽히는 동안 화면을 몇 번 바꿀지 정한다.
#    지금까지 그 경계를 **글자 수 비례로 추정**해서 넣었다. 실제 말과 미세하게 어긋난다.
#    Whisper로 되받아 읽히면 단어가 몇 초에 나오는지 정확히 나온다.
#
# 🔴 무료다. faster-whisper가 로컬에서 돈다. 모델은 처음 한 번만 받는다(~150MB).
# 🔴 head(앞무음)를 뺀 **발화 기준 초**로 출력한다. Talk.jsx가 쓰는 좌표계와 같다.
#
#   python align.py            → align.json + 화면에 표
#   python align.py 5          → 5번 대사만
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

HERE = Path(__file__).parent
OUT = HERE / "out"

# small이면 한국어도 충분하다. medium은 3배 느리고 차이가 거의 없다
MODEL = "small"


def main():
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    trim = {r["file"]: r for r in json.loads((HERE / "trim.json").read_text(encoding="utf-8"))}

    print(f"모델 불러오는 중 ({MODEL}) — 처음이면 다운로드에 시간이 걸린다")
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")

    result = []
    for mp3 in sorted(OUT.glob("*.mp3")):
        idx = int(mp3.stem.split("_")[0])
        if only and idx != only:
            continue
        head = trim.get(mp3.name, {}).get("head", 0)

        segs, _ = model.transcribe(str(mp3), language="ko", word_timestamps=True)
        words = []
        for s in segs:
            for w in s.words:
                # 🔴 head를 빼서 **발화 시작이 0초**가 되게 맞춘다. Talk.jsx가 그 좌표계를 쓴다
                words.append({"w": w.word.strip(), "t": round(max(0, w.start - head), 2),
                              "e": round(max(0, w.end - head), 2)})

        result.append({"n": idx, "file": mp3.name, "words": words})
        print(f"\n[{idx}] {mp3.stem}")
        print("  " + "  ".join(f"{x['w']}({x['t']})" for x in words))

    (HERE / "align.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ align.json ({len(result)}개)")


main()
