# -*- coding: utf-8 -*-
"""목소리 후보 듣기 비교 — 같은 대사를 여러 음성으로 뽑는다. 2026-08-01

    python try_voices.py                       # 기본 대사
    python try_voices.py "다른 대사로 뽑아줘"

🔴 왜 만들었나 — 한국어 전용 음성은 edge-tts 에 **3개뿐**이라 캐릭터를 늘릴 수가 없었다.
   그런데 «Multilingual» 계열 12개가 **한국어도 읽는다.** 억양이 어색한 것도 있어서
   귀로 골라야 한다. 결과는 `voice/후보/` 에 이름 붙여 저장한다.

🔴 속도는 제작 기준과 같은 +70% 로 뽑는다 — 느리게 뽑아 고르면 실제와 다르게 들린다.
"""
import asyncio
import sys
from pathlib import Path

import edge_tts

HERE = Path(__file__).parent
OUT = HERE / "후보"
RATE = "+70%"

LINE = sys.argv[1] if len(sys.argv) > 1 else \
    "오천사백 원짜리 돈까스김밥, 재료값 얼마일 것 같아?"

# (파일이름, 음성, 메모)
CAND = [
    ("00_지금_올마_SunHi",        "ko-KR-SunHiNeural",                "현재 올마(여)"),
    ("01_지금_사장님_InJoon",      "ko-KR-InJoonNeural",               "현재 사장님(남)"),
    ("02_한국_Hyunsu",           "ko-KR-HyunsuMultilingualNeural",   "한국어 전용 3번째(남)"),
    ("03_다국어_Ava",             "en-US-AvaMultilingualNeural",      "여 · 미국"),
    ("04_다국어_Emma",            "en-US-EmmaMultilingualNeural",     "여 · 미국"),
    ("05_다국어_Vivienne",        "fr-FR-VivienneMultilingualNeural", "여 · 프랑스"),
    ("06_다국어_Seraphina",       "de-DE-SeraphinaMultilingualNeural","여 · 독일"),
    ("07_다국어_Thalita",         "pt-BR-ThalitaMultilingualNeural",  "여 · 브라질"),
    ("08_다국어_Andrew",          "en-US-AndrewMultilingualNeural",   "남 · 미국"),
    ("09_다국어_Brian",           "en-US-BrianMultilingualNeural",    "남 · 미국"),
    ("10_다국어_William",         "en-AU-WilliamMultilingualNeural",  "남 · 호주"),
    ("11_다국어_Remy",            "fr-FR-RemyMultilingualNeural",     "남 · 프랑스"),
    ("12_다국어_Florian",         "de-DE-FlorianMultilingualNeural",  "남 · 독일"),
    ("13_다국어_Giuseppe",        "it-IT-GiuseppeMultilingualNeural", "남 · 이탈리아"),
]


async def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.mp3"):
        f.unlink()
    print(f'대사: {LINE}\n속도: {RATE}\n')
    for name, voice, memo in CAND:
        p = OUT / f"{name}.mp3"
        try:
            await edge_tts.Communicate(LINE, voice, rate=RATE).save(str(p))
        except Exception as e:
            print(f"  {name:<24} ❌ {str(e)[:50]}")
            continue
        sec = round(p.stat().st_size / 6000, 2)   # 48kbps 고정이라 크기÷6000 = 초
        print(f"  {name:<24}{sec:>6.2f}s  {memo}")
    print(f"\n→ {OUT}")


asyncio.run(main())
