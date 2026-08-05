# AI가 만든 배경 그림 → 9:16 배경으로 자르기 (2026-07-22)
#
# 🔴 이미지 생성 모델이 뱉는 그림은 테두리가 육각형이거나 흰 여백이 남는다.
#    그대로 쓰면 쇼츠 화면에 흰 모서리가 뜬다.
# 🔴 그래서 **흰 부분이 하나도 안 걸리는 가장 큰 9:16 사각형**을 찾아 자른다.
#    가운데에서 시작해 네 모서리가 흰색이면 조금씩 줄여가며 맞춘다.
#
#   사용법:  python crop169.py "그림.png" store03
import sys
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 1080, 1920
WHITE = 238  # 이 값 이상이면 여백으로 본다


def content_box(a):
    """흰 여백을 뺀 내용 영역."""
    solid = (a[..., :3].min(axis=2) < WHITE)
    ys, xs = np.where(solid)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def largest_169(a, x0, y0, x1, y1):
    """내용 영역 안에서 흰 픽셀이 거의 없는 가장 큰 9:16 사각형."""
    solid = (a[..., :3].min(axis=2) < WHITE)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    best = None

    # 높이를 크게 잡고 점점 줄인다
    for h in range(y1 - y0, 200, -8):
        w = int(h * 9 / 16)
        if w > x1 - x0:
            continue
        # 가로·세로 위치를 조금씩 옮겨보며 여백이 안 걸리는 자리를 찾는다
        for dy in range(0, (y1 - y0 - h) // 2 + 1, 8):
            for sy in (1, -1):
                top = cy - h // 2 + sy * dy
                if top < y0 or top + h > y1:
                    continue
                for dx in range(0, (x1 - x0 - w) // 2 + 1, 8):
                    for sx in (1, -1):
                        left = cx - w // 2 + sx * dx
                        if left < x0 or left + w > x1:
                            continue
                        patch = solid[top:top + h, left:left + w]
                        # 🔴 가장자리 한 줄만 본다(2026-07-22). 안쪽 흰색은 벽·조명이라 정상이고,
                        #    테두리에 흰색이 닿으면 화면에 흰 줄로 뜬다.
                        edges = np.concatenate([patch[0], patch[-1], patch[:, 0], patch[:, -1]])
                        if edges.all():
                            best = (left, top, left + w, top + h)
                            break
                    if best:
                        break
                if best:
                    break
            if best:
                break
        if best:
            break
    return best


def run(src, name):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im)
    x0, y0, x1, y1 = content_box(a)
    box = largest_169(a, x0, y0, x1, y1)
    if box is None:
        print("9:16 사각형을 못 찾음 — 가운데를 그냥 자릅니다")
        w = min(x1 - x0, int((y1 - y0) * 9 / 16))
        h = int(w * 16 / 9)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        box = (cx - w // 2, cy - h // 2, cx + w // 2, cy - h // 2 + h)

    out = im.crop(box).resize((W, H), Image.LANCZOS)
    dst = Path(__file__).parent.parent / "remotion" / "public" / "bg" / f"{name}.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    print(f"완료: {dst.name}  (원본 {im.size} → 크롭 {box})")


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "store")
