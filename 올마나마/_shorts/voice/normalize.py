# 목소리 볼륨 맞추기 (2026-07-22)
#
# 🔴 왜 필요한가: 목소리마다 크기가 다르다. 특히 선히(사장님)가 인준(올마)보다 작게 들린다.
#    영상 중간에 소리 크기가 널뛰면 시청자가 볼륨을 계속 만지게 되고 그러다 나간다.
# 🔴 ffmpeg의 loudnorm은 **방송 표준(EBU R128)**으로 맞춘다. 단순 볼륨 배수와 달리
#    "사람이 느끼는 크기"를 맞추기 때문에 큰 소리는 안 깨지고 작은 소리만 올라온다.
# 🔴 원본은 `out_raw\`에 남긴다. 다시 뽑고 싶으면 거기서 꺼낸다.
#
#   python normalize.py
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out"
RAW = HERE / "out_raw"


def find_ffmpeg():
    """🔴 winget으로 깐 직후엔 PATH가 아직 갱신 안 돼 있다(셸을 다시 켜야 먹는다).
    그래서 PATH에 없으면 winget 설치 폴더를 직접 뒤진다."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    base = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WinGet" / "Packages"
    hits = list(base.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"))
    return str(hits[0]) if hits else None


FFMPEG = find_ffmpeg()

# 유튜브 권장은 -14 LUFS다. 쇼츠는 폰 스피커로 듣는 경우가 많아 조금 더 크게 잡는다.
TARGET_I = -13.0   # 평균 크기
TARGET_TP = -1.5   # 최대 순간 크기 (넘으면 깨진다)
TARGET_LRA = 8.0   # 크기 변화 폭


def main():
    if not FFMPEG:
        print("ffmpeg을 못 찾음. winget install Gyan.FFmpeg 로 설치할 것")
        return
    RAW.mkdir(exist_ok=True)
    files = sorted(OUT.glob("*.mp3"))
    if not files:
        print("out\\ 에 mp3가 없다. make_voice.py 부터 돌릴 것")
        return

    for f in files:
        raw = RAW / f.name
        if not raw.exists():
            shutil.copy(f, raw)   # 원본 보관 (한 번만)

        tmp = OUT / (f.stem + ".norm.mp3")
        r = subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw),
             "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}",
             "-b:a", "48k", "-ar", "24000", "-ac", "1", str(tmp)],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or not tmp.exists():
            print(f"실패: {f.name}  {r.stderr.strip()[:120]}")
            continue
        tmp.replace(f)
        print(f"맞춤: {f.name}")

    print(f"\n원본은 {RAW.name}\\ 에 있다.")
    print("⚠️ 길이가 미세하게 달라질 수 있으니 trim.py 를 다시 돌릴 것")


main()
