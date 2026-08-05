# -*- coding: utf-8 -*-
"""효과음 입히기 — 무음 mp4 + 효과음 → 완성본 (2026-07-21)

  python mix.py                       # out/ppuringkle.mp4 에 소리 입힘
  python mix.py --in test_intro.mp4   # 다른 파일

🔴 소리는 HTML 타임라인과 **같은 초**를 쓴다. 편집기에서 타이밍을 바꾸면
   여기 CUES도 같이 고쳐야 어긋나지 않는다.
"""
import argparse
import os
import subprocess
import sys

import imageio_ffmpeg

BASE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(os.path.dirname(BASE), "Sound")
OUT = os.path.join(BASE, "out")

# (시각초, 파일명, 볼륨)  — 볼륨 1.0이 원본
CUES = [
    (0.00, "Lit Fuse.mp3",                    0.55),  # 인트로 — 타들어가는 긴장
    (2.05, "Shattered Glass Hitting Metal.mp3", 0.9),  # 소용돌이 폭발
    (2.25, "Metallic Clank.mp3",              0.7),   # 올마 등장
    (3.40, "Pen Clicking.mp3",                0.8),   # 후킹 타자
    (12.8, "Wood Hit Metal Crash.mp3",        0.7),   # 재료비 합계
    (19.3, "Gunfire And Voices.mp3",          0.8),   # 차액 터짐
    (20.5, "Slapping Three Faces.mp3",        0.85),  # "헐"
    (22.6, "Windshield Hit With Bar.mp3",     0.75),  # 털썩
]


def main(src, dst):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    vid = os.path.join(OUT, src)
    if not os.path.exists(vid):
        print(f"❌ 영상 없음: {vid}"); sys.exit(1)

    # 영상 길이(초)
    pr = subprocess.run([exe, "-i", vid], capture_output=True)
    txt = pr.stderr.decode("utf-8", "replace")
    vdur = 33.0
    for line in txt.splitlines():
        if "Duration:" in line:
            hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
            vdur = int(hh) * 3600 + int(mm) * 60 + float(ss)
            break

    cmd = [exe, "-y", "-i", vid]
    miss = []
    used = []
    for t, name, vol in CUES:
        p = os.path.join(SFX, name)
        if not os.path.exists(p):
            miss.append(name); continue
        cmd += ["-i", p]
        used.append((t, name, vol))
    if miss:
        print("⚠️ 못 찾은 효과음:", ", ".join(miss))
    if not used:
        print("❌ 쓸 효과음이 없습니다"); sys.exit(1)

    # 각 효과음을 지정 시각으로 밀고(adelay), 볼륨 맞춘 뒤 합친다(amix)
    parts, tags = [], []
    for i, (t, name, vol) in enumerate(used, start=1):
        ms = int(t * 1000)
        parts.append(f"[{i}:a]adelay={ms}|{ms},volume={vol}[a{i}]")
        tags.append(f"[a{i}]")
    fc = (";".join(parts) + ";" + "".join(tags)
          + f"amix=inputs={len(used)}:duration=longest:normalize=0[aout]")

    out = os.path.join(OUT, dst)
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            # 🔴 -shortest를 쓰면 마지막 효과음이 끝나는 지점에서 영상까지 잘린다(33→23.8초).
            #    apad로 늘리면 무한히 인코딩된다. → 영상 길이(-t)로 못 박는다.
            "-t", f"{vdur:.2f}", "-movflags", "+faststart", out]

    print(f"  효과음 {len(used)}개 배치 중...")
    for t, name, vol in used:
        print(f"    {t:>5.1f}초  {name}")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(r.stderr.decode("utf-8", "replace")[-1800:]); sys.exit(1)
    mb = os.path.getsize(out) / 1024 / 1024
    print(f"\n✅ 완료: {out}  ({mb:.1f}MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="ppuringkle.mp4")
    ap.add_argument("--out", dest="dst", default="ppuringkle_sfx.mp4")
    a = ap.parse_args()
    main(a.src, a.dst)
