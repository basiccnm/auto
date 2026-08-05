# -*- coding: utf-8 -*-
"""올마 옹알이 만들기 (2026-07-21)

왜 옹알이인가:
  TTS로 또박또박 읽으면 정보 전달이 되고, 그건 이미 자막이 한다.
  **알아들을 수 없는 소리 + 자막** 조합이 훨씬 웃기고, 캐릭터가 산다.

방법:
  ① OpenAI TTS로 뜻 없는 소리를 읽힌다 (아주 짧아서 비용 1원 미만)
  ② ffmpeg으로 **피치를 확 올리고 고음을 깎아** 알아들을 수 없게 뭉갠다

🔴 감정별 5개만 만들면 68편 내내 돌려쓴다. 추가 비용 0원.
🔴 한 번 만들면 다시 돌릴 일 없다. 재실행 전 반드시 물어볼 것(유료 API).

  python make_babble.py
"""
import os
import subprocess
import sys

import imageio_ffmpeg
from openai import OpenAI

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remotion", "public", "sfx")

# (파일명, 읽을 소리, 피치배수, 속도)
#  🔴 피치가 높을수록 아기 같고, 1.4를 넘으면 뭐라는지 아예 안 들린다 — 그게 목적이다.
#     그래서 **실제 대사를 그대로 읽혀도 된다.** 감정이 실려서 오히려 더 낫다.
#     "졸라 맛있어"처럼 자막에 못 쓸 말도 소리로는 안 들리니 문제없다(2026-07-21 대표 확인).
VOICES = [
    # 훅 — 영수증 싸대기
    ("babble_surprise", "뺙?! 뭐야 이거!",          1.52, 1.10),
    # 변명 깨기 — 의심 / 어이없음 / 따짐
    ("babble_huh",      "엥? 진짜로?",              1.46, 1.05),
    ("babble_pfft",     "에이 말도 안 돼 왱알왱알",   1.44, 1.08),
    ("babble_point",    "이거 봐 이거! 고작 이거야?", 1.48, 1.12),
    # 원가 폭격 — 하나씩 맞을 때
    ("babble_ouch",     "윽! 아야! 어어?",           1.50, 1.15),
    # 극대노
    ("babble_rage",     "뚜쉬뚜쉬 우아아아앙!! 말도 안 돼!", 1.50, 1.15),
    # 급발진 정적 — 먹으면서
    ("babble_yum",      "우움~ 뇸뇸 졸라 맛있어",     1.38, 0.95),
    ("babble_sigh",     "하아... 젠장",              1.34, 0.92),
    # 마무리
    ("babble_cheer",    "뺘뱌! 그럼 이 돈 어디 갔냐고!", 1.55, 1.10),
]

VOICE = "nova"  # 밝고 높은 편 — 변조하면 만화 캐릭터처럼 된다


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY 없음"); sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    client = OpenAI()
    exe = imageio_ffmpeg.get_ffmpeg_exe()

    total_chars = sum(len(t) for _, t, _, _ in VOICES)
    print(f"글자 수 {total_chars}자 → 예상 비용 약 {total_chars/1000*0.015*1400:.1f}원\n")

    for name, text, pitch, tempo in VOICES:
        raw = os.path.join(OUT, f"_raw_{name}.mp3")
        dst = os.path.join(OUT, f"{name}.mp3")

        # ① TTS
        r = client.audio.speech.create(model="tts-1", voice=VOICE, input=text, speed=1.0)
        with open(raw, "wb") as fp:
            fp.write(r.content)

        # ② 변조 — 피치 올리고(asetrate) 속도 되돌리고(atempo) 고음 깎아 뭉갠다(lowpass)
        #    🔴 asetrate만 쓰면 속도까지 빨라진다. atempo로 되돌려야 피치만 올라간다.
        af = (
            f"asetrate=24000*{pitch},"
            f"atempo={1/pitch:.4f},"
            f"atempo={tempo},"
            f"lowpass=f=2600,"
            f"highpass=f=180,"
            f"volume=1.6"
        )
        cmd = [exe, "-y", "-i", raw, "-af", af, "-ar", "44100", dst]
        p = subprocess.run(cmd, capture_output=True)
        if p.returncode != 0:
            print(p.stderr.decode("utf-8", "replace")[-800:]); sys.exit(1)
        os.remove(raw)

        mb = os.path.getsize(dst) / 1024
        print(f"  ✅ {name}.mp3  ({mb:.0f}KB)  «{text}»  피치×{pitch}")

    print(f"\n완료 → {OUT}")


if __name__ == "__main__":
    main()
