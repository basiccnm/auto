# -*- coding: utf-8 -*-
"""
검수 몽타주 만들기 (2026-08-07)

    python scripts/make_montage.py <입력폴더> <출력파일> [열수]

왜 필요한가
  검수 보고 규칙: **스크린샷 개별 전송 금지.** 라이트 1장 + 다크 1장으로 합쳐 보낸다.
  (전 프로젝트 공통 규칙 — 낱장을 뿌리면 대표님이 화면을 오가며 봐야 한다.)

⚠ 6열 2000px 아래로 줄이면 글씨가 뭉개져 «잘린 것»으로 읽힌다(2026-08-03 실측).
  열 수를 늘리기보다 장수를 나누는 편이 낫다.
⚠ 파일명 아래쪽 라벨은 넣지 않는다 — 화면 자체를 가린다. 순서로 읽게 한다.
"""
import sys, os, glob
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3

files = sorted(glob.glob(os.path.join(src, "*.png")))
if not files:
    print("이미지가 없습니다:", src); sys.exit(1)

ims = [Image.open(f).convert("RGB") for f in files]

# 폰 스샷은 세로가 길다 — 한 장 폭을 정해 두고 비율대로 줄인다
TILE_W = 380
tiles = []
for im in ims:
    w, h = im.size
    tiles.append(im.resize((TILE_W, int(h * TILE_W / w)), Image.LANCZOS))

rows = (len(tiles) + cols - 1) // cols
row_h = [max(t.height for t in tiles[r*cols:(r+1)*cols]) for r in range(rows)]
GAP = 14
W = cols * TILE_W + (cols + 1) * GAP
H = sum(row_h) + (rows + 1) * GAP

canvas = Image.new("RGB", (W, H), (24, 24, 28))
y = GAP
for r in range(rows):
    x = GAP
    for t in tiles[r*cols:(r+1)*cols]:
        canvas.paste(t, (x, y))
        x += TILE_W + GAP
    y += row_h[r] + GAP

os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
# 드라이브로 올릴 것이라 용량을 줄인다(품질 82 면 글씨가 안 뭉갠다)
canvas.save(dst, quality=82, optimize=True)
print(f"{dst}  {W}x{H}  {os.path.getsize(dst)//1024}KB  ({len(tiles)}장)")
