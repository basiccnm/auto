# 캐릭터 목소리 생성 — 엣지 TTS (무료, API키 없음) · 2026-07-22
#
# 🔴 옹알이는 폐기했다. 3편부터 **한국어 대사**로 간다(2026-07-22 지시).
# 🔴 한국어 목소리가 3개뿐인데 캐릭터는 4명이다.
#    → 같은 목소리라도 **피치·속도를 바꾸면** 다른 인물로 들린다. 그걸로 4명을 만든다.
# 🔴 대사 길이가 곧 장면 길이다. 이 스크립트가 뽑아주는 초 단위를 config.js 타임라인에 넣는다.
#
#   사용법:  python make_voice.py            → 샘플 4줄
#            python make_voice.py script     → 대본 전체
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import edge_tts

HERE = Path(__file__).parent

# 배역별 목소리. 🔴 올마와 교촌은 베이스가 달라야 한다 — 같으면 누가 말하는지 안 들린다.
# 🔴 속도를 +40%까지 올렸다가 되돌렸다(2026-07-22).
#    짧게 쪼갠 대사를 빠르게 읽으니 **말이 뚝뚝 끊기고 무슨 말인지 안 들렸다.**
#    해법은 속도가 아니라 **문장을 완결형으로 길게 쓰는 것**이었다.
#    문장이 이어지면 천천히 읽어도 같은 시간에 더 많은 내용이 들어간다.
# 🔴 사장님은 남자 목소리를 낮추고 늦춰 썼더니 **너무 느려서 흐름이 죽었다**(2026-07-22).
#    소비자볼을 빼면서 여자 목소리가 비었으니 그걸 사장님에게 준다.
#    올마(남)와 성별이 갈려서 누가 말하는지도 더 잘 들린다.
# 🔴 속도는 +40% → +15% → +20% → **+35%**로 왔다(2026-07-22).
#    처음 +40%가 안 들렸던 건 속도 탓이 아니라 **대사를 짧게 쪼갰기 때문**이었다.
#    완결 문장으로 바꾸고 나니 +20%도 오히려 느려 보였다. 쇼츠 평균 템포가 그만큼 빠르다.
# 🔴 교촌 피치를 -8 → **-30Hz**로 낮췄다.
#    HyunsuMultilingual은 원래 "밝고 친근한" 목소리라 **너무 착하게** 들렸다.
#    변명하는 기업인데 목소리가 선하면 시청자가 그 말에 넘어간다.
#    낮추면 사무적이고 무게 있는 대변인 톤이 된다.
# 🔴 +35% → +45% → +50% → **+70%** (2026-07-24). 배달 1편부터 적용.
#    +50%도 "엄청 잘 들린다"고 해서 60·70%를 음성만 뽑아 들려주고 **70%로 확정**했다.
#    쇼츠 시청자는 이미 빠른 템포에 익숙하다 — 느리면 넘긴다.
#    ⚠️ 마라탕 2·3·5편의 lines_*.js 타이밍은 **+35%로 잰 값**이다.
#       그 편들을 다시 뽑으려면 rate를 되돌리거나 trim을 다시 재야 더빙이 맞는다.
# 🔴 2026-07-25 **배역 스왑** — 여성 타깃으로 방향을 틀면서 메인 화자를 여성으로 바꿨다.
#    올마(진행자)=여성 SunHi / 사장님=남성 InJoon.
#    한국어 여성 목소리가 SunHi 하나뿐이라 둘 다 여성으로 두면 구분이 안 된다.
#    사장님이 발끈하는 역할이라 남성 목소리가 오히려 자연스럽다.
# 🔴 2026-08-01 **사장님을 편마다 바꾼다** (대표 지시: *"사장님은 조금씩 바꿔 그리고 스타일도"*).
#    편마다 브랜드가 다르니 사장님도 다른 사람이다. 같은 목소리가 매번 나오면 한 사람처럼 들린다.
#
#    한국어 **전용** 음성은 edge-tts 에 3개뿐인데, 「Multilingual」 12개가 **한국어도 읽는다**.
#    그래서 사장님 후보가 8명까지 늘었다. 속도·피치를 조금씩 달리해 사람을 갈라놓는다.
#    ⚠️ 다국어 음성은 한국어 전용보다 **0.3~0.8초 빠르게** 읽는다. 대사 길이가 달라지니
#       편을 바꿀 때마다 `trim.py` → `sync` 를 반드시 다시 돌린다.
#
#    쓰는 법 — `script_*.json` 의 `who` 에 아래 키를 적는다. 화면 캐릭터 이름(`lines_*.js` 의
#    `who: "사장님"`)과는 **별개**다. 목소리만 갈아끼우는 것이다.
CAST = {
    "올마": dict(voice="ko-KR-SunHiNeural", rate="+70%", pitch="+0Hz"),

    # 사장님 — 편마다 골라 쓴다
    "사장님": dict(voice="ko-KR-InJoonNeural", rate="+70%", pitch="+0Hz"),          # 기본(한국어)
    "사장님2": dict(voice="fr-FR-RemyMultilingualNeural", rate="+65%", pitch="+0Hz"),   # 김밥편 · 차분
    "사장님3": dict(voice="en-US-AndrewMultilingualNeural", rate="+70%", pitch="-15Hz"), # 낮고 무겁게
    "사장님4": dict(voice="en-AU-WilliamMultilingualNeural", rate="+72%", pitch="+0Hz"),
    "사장님5": dict(voice="de-DE-FlorianMultilingualNeural", rate="+68%", pitch="-10Hz"),
    "사장님6": dict(voice="it-IT-GiuseppeMultilingualNeural", rate="+70%", pitch="+5Hz"), # 억울한 톤
    "사장님7": dict(voice="en-US-BrianMultilingualNeural", rate="+70%", pitch="+0Hz"),
    "사장님8": dict(voice="ko-KR-HyunsuMultilingualNeural", rate="+70%", pitch="-20Hz"),  # 사무적 대변인

    "교촌": dict(voice="ko-KR-HyunsuMultilingualNeural", rate="+35%", pitch="-30Hz"),
    "소비자": dict(voice="ko-KR-SunHiNeural", rate="+38%", pitch="+20Hz"),
    # 여성 목소리가 SunHi 하나뿐이라 못 쓰던 배역들 — 다국어로 열렸다(2026-08-01)
    "소비자2": dict(voice="en-US-AvaMultilingualNeural", rate="+70%", pitch="+0Hz"),
    "소비자3": dict(voice="de-DE-SeraphinaMultilingualNeural", rate="+68%", pitch="+0Hz"),
    "소비자4": dict(voice="fr-FR-VivienneMultilingualNeural", rate="+70%", pitch="+0Hz"),
}

SAMPLE = [
    ("올마", "교촌 허니콤보, 이만 육천 원."),
    ("소비자", "이만 육천 원? 이거 너무한 거 아니야?"),
    ("교촌", "저희는 붓으로 하나하나 바릅니다."),
    ("사장님", "저도 남는 게 없어요."),
]


async def say(who, text, out):
    c = CAST[who]
    tts = edge_tts.Communicate(text, c["voice"], rate=c["rate"], pitch=c["pitch"])
    await tts.save(str(out))


def dur(path):
    """mp3 길이(초).

    🔴 이 PC엔 ffprobe가 따로 안 깔려 있다(2026-07-22). 대신 edge-tts 출력이
       **48kbps 고정**이라 파일크기 ÷ 6000 으로 계산하면 remotion ffprobe 값과 맞는다.
       (검증: 23,760바이트 → 3.96초, ffprobe도 3.96초)
    """
    return round(path.stat().st_size / 6000, 2)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
    if mode == "script":
        raw = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
        lines = [(l["who"], l["text"], l.get("scene", "-")) for l in raw]
        outdir = HERE / "out"
        # 🔴 normalize.py는 out_raw\ 를 원본으로 삼는다. 새로 뽑았는데 옛 백업이 남아 있으면
        #    normalize가 그걸 되살려서 **새 음성이 통째로 날아간다**(2026-07-22 실제로 당함).
        # 🔴 폴더째 지우면 윈도우가 "액세스 거부"를 낸다(탐색기가 폴더를 잡고 있으면).
        #    안에 든 mp3만 지우면 목적은 같고 안 죽는다.
        old = HERE / "out_raw"
        if old.exists():
            for f in old.glob("*.mp3"):
                try:
                    f.unlink()
                except OSError:
                    pass
    else:
        lines = [(w, t, "샘플") for w, t in SAMPLE]
        outdir = HERE / "sample"
    outdir.mkdir(exist_ok=True)

    total = 0.0
    scene_total = {}
    for i, (who, text, scene) in enumerate(lines, 1):
        f = outdir / f"{i:02d}_{who}.mp3"
        await say(who, text, f)
        d = dur(f)
        total += d
        scene_total[scene] = round(scene_total.get(scene, 0) + d, 2)
        print(f"{i:02d}  {scene:5s} {who:4s} {d:5.2f}s  {text}")

    print(f"\n합계 {round(total, 1)}초")
    if len(scene_total) > 1:
        print("\n장면별 (config.js의 T 타임라인은 이 값으로 맞춘다)")
        for s, d in scene_total.items():
            print(f"  {s:6s} {d:5.2f}s")


asyncio.run(main())
