# mp3 앞뒤 무음 재기 (2026-07-22)
#
# 🔴 왜: edge-tts는 문장 앞뒤에 0.3~0.6초씩 무음을 붙인다.
#    대사를 이어 붙이면 그 무음이 그대로 쌓여 **말이 뚝뚝 끊긴다**(2026-07-22 지적).
# 🔴 파일을 직접 자르지 않는다. 무음 길이만 재서 JSON으로 내보내고,
#    Remotion의 <Audio trimBefore/trimAfter>로 재생할 때 건너뛴다. 원본이 안 상한다.
# 🔴 이 PC엔 ffprobe가 없다. Remotion에 딸린 ffmpeg로 wav를 만들어 재고, wav는 지운다.
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
OUT = HERE / "out_puradak"
TMP = HERE / "_wav"
FFMPEG = ["npx", "remotion", "ffmpeg"]
REMOTION = HERE.parent / "remotion"

THRESH = 0.012   # 이 값 아래면 무음으로 본다
# 🔴 말 앞뒤로 남기는 여유. 0.06으로 뒀더니 "말이 부드럽지 않다"는 지적을 받았다(2026-07-22).
#    숨 쉴 자리가 없어서 문장이 서로 밀치는 느낌이 난다. 0.2초는 있어야 사람 말처럼 들린다.
#    ⚠️ 이 값을 키우면 전체 길이가 늘어난다(13줄이면 +5초). gap으로 다시 맞춰야 한다.
KEEP = 0.20


def to_wav(mp3, wav):
    subprocess.run(
        FFMPEG + ["-y", "-i", str(mp3), "-ac", "1", "-ar", "16000", str(wav)],
        cwd=str(REMOTION), capture_output=True, shell=True,
    )


def measure(wav):
    with wave.open(str(wav), "rb") as w:
        n, sr = w.getnframes(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    loud = np.abs(a) > THRESH
    if not loud.any():
        return 0.0, 0.0, n / sr
    i, j = np.argmax(loud), len(loud) - np.argmax(loud[::-1])
    total = n / sr
    head = max(0.0, i / sr - KEEP)
    tail = max(0.0, total - j / sr - KEEP)
    return round(head, 3), round(tail, 3), round(total, 3)


def main():
    TMP.mkdir(exist_ok=True)
    rows = []
    for mp3 in sorted(OUT.glob("*.mp3")):
        wav = TMP / (mp3.stem + ".wav")
        to_wav(mp3, wav)
        if not wav.exists():
            print(f"변환 실패: {mp3.name}")
            continue
        head, tail, total = measure(wav)
        wav.unlink()
        rows.append({"file": mp3.name, "head": head, "tail": tail, "total": total,
                     "speech": round(total - head - tail, 2)})
        print(f"{mp3.stem:22s} 전체 {total:5.2f}  앞무음 {head:4.2f}  뒤무음 {tail:4.2f}  → {total-head-tail:5.2f}")

    # 🔴 윈도우는 폴더를 잡고 있으면 rmdir이 실패한다. 실패해도 결과 저장은 계속돼야 한다
    try:
        TMP.rmdir()
    except OSError:
        pass
    (HERE / "trim_puradak.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    saved = sum(r["head"] + r["tail"] for r in rows)
    print(f"\n무음 총 {saved:.1f}초 — 잘라내면 {sum(r['total'] for r in rows):.1f}초 → {sum(r['speech'] for r in rows):.1f}초")


main()
