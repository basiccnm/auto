# -*- coding: utf-8 -*-
# 공유 대표 이미지(og:image) 생성 — 1200x630 PNG 1장 (2026-07-18)
#
#  왜: 링크를 카톡·페북 등에 공유하면 지금은 이미지가 없어 글자만 뜬다.
#      페이지마다 다른 이미지가 아니라 **사이트 대표 이미지 1장**을 모든 페이지가 공유한다.
#      (사용자 지시 2026-07-18: "링크공유할때 그냥 우리 고유 이미지 뜨게")
#
#  사용법: python scripts/gen_og.py   → _preview/og/share.png
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "_preview", "og")
os.makedirs(OUT, exist_ok=True)

#  귀여운 버전(2026-07-19 사용자 확정 "①번"): 소마체 로고 + 볼터치 + 방울 배경 + 말랑 피치색.
FB = r"C:\Windows\Fonts\malgunbd.ttf"   # 맑은 고딕 Bold — 설명글용
FR = r"C:\Windows\Fonts\malgun.ttf"     # 맑은 고딕 Regular
FL = r"C:\Windows\Fonts\HANSomaB.ttf"   # 소마체 — 로고/뱃지 전용(동글동글)
f = lambda p, s: ImageFont.truetype(p, s)

W, H = 1200, 630
C1, C2 = (255, 138, 92), (255, 183, 138)   # 브랜드 그라디언트(말랑 피치)
CHEEK = (255, 170, 150, 220)               # 볼터치
LOGO_INK = (255, 107, 53)                  # 뱃지 안 글자(진한 주황 유지)


def build():
    im = Image.new("RGB", (W, H), C1)
    d = ImageDraw.Draw(im)
    # 대각선 그라디언트 (가로 보간 — 썸네일에선 충분)
    for x in range(W):
        t = x / W
        d.line([(x, 0), (x, H)], fill=(int(C1[0] + (C2[0] - C1[0]) * t),
                                       int(C1[1] + (C2[1] - C1[1]) * t),
                                       int(C1[2] + (C2[2] - C1[2]) * t)))
    # 배경 방울 (반투명 흰 원 — 말랑한 느낌)
    for cx, cy, r, a in ((90, 90, 26, 60), (1120, 120, 38, 50), (180, 540, 20, 55),
                         (1060, 520, 30, 45), (1150, 320, 14, 60)):
        o = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
        ImageDraw.Draw(o).ellipse([0, 0, r * 2, r * 2], fill=(255, 255, 255, a))
        im.paste(o, (cx - r, cy - r), o)
    # 얼굴 뱃지 — 흰 라운드 사각 + 소마체 '올' + 볼터치, 살짝 기울임
    bs = 150
    badge = Image.new("RGBA", (bs, bs), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle([0, 0, bs, bs], radius=44, fill=(255, 255, 255, 255))
    fo = f(FL, 86)
    bd.text(((bs - bd.textlength("올", font=fo)) / 2, (bs - 86) / 2 - 8), "올", font=fo, fill=LOGO_INK)
    bd.ellipse([16, 100, 42, 118], fill=CHEEK)            # 볼터치 좌
    bd.ellipse([bs - 42, 100, bs - 16, 118], fill=CHEEK)  # 볼터치 우
    badge = badge.rotate(-7, expand=True, resample=Image.BICUBIC)
    im.paste(badge, ((W - badge.width) // 2, 86), badge)

    def center(text, font, y, fill):
        d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)

    center("올마나마", f(FL, 104), 278, (255, 255, 255))
    center("내가 시킨 그 메뉴, 원가가 얼마일까?", f(FB, 38), 418, (255, 255, 255))
    center("메뉴 349개 원가율 · 재료 시세 282종", f(FR, 28), 492, (255, 240, 232))
    p = os.path.join(OUT, "share.png")
    im.save(p, "PNG", optimize=True)
    return p


def favicon():
    """브라우저 탭 로고 — 얼 뱃지(주황 라운드 사각 + 흰 얼)."""
    made = []
    for size, name in ((180, "apple-touch-icon.png"), (32, "favicon-32.png"), (16, "favicon-16.png")):
        im = Image.new("RGB", (size, size), C1)
        d = ImageDraw.Draw(im)
        for x in range(size):                      # 브랜드 그라디언트
            t = x / size
            d.line([(x, 0), (x, size)], fill=(int(C1[0] + (C2[0] - C1[0]) * t),
                                              int(C1[1] + (C2[1] - C1[1]) * t),
                                              int(C1[2] + (C2[2] - C1[2]) * t)))
        fs = int(size * 0.66)
        fo = f(FL, fs)                                  # 소마체 — 작은 크기에서도 동글동글
        w = d.textlength("올", font=fo)
        d.text(((size - w) / 2, (size - fs) / 2 - size * 0.06), "올", font=fo, fill=(255, 255, 255))
        if size >= 180:                                 # 볼터치는 큰 아이콘에서만(16px엔 뭉갬)
            r, y = size * 0.055, size * 0.70
            for cx in (size * 0.20, size * 0.80):
                d.ellipse([cx - r, y - r * 0.7, cx + r, y + r * 0.7], fill=(255, 190, 170))
        p = os.path.join(os.path.dirname(OUT), name)   # _preview 루트에 저장
        im.save(p, "PNG", optimize=True)
        made.append(name)
    # favicon.ico (16/32/48 멀티사이즈)
    ico = Image.open(os.path.join(os.path.dirname(OUT), "favicon-32.png"))
    ico.save(os.path.join(os.path.dirname(OUT), "favicon.ico"),
             sizes=[(16, 16), (32, 32), (48, 48)])
    made.append("favicon.ico")
    return made


if __name__ == "__main__":
    print("공유 이미지:", build())
    print("파비콘:", ", ".join(favicon()))
