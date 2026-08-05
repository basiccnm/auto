# 썸네일 음식 일러의 **누끼 영역(알파 바운딩박스)** 을 재서 src/cards/food_trim.js 로 굽는다.
#
# 🔴 왜 필요한가 (2026-07-27 지적)
#    일러마다 투명 여백이 제각각이라, 같은 박스에 contain 으로 넣으면
#    **캔버스 크기**에 맞춰져서 화면에 보이는 음식 크기가 편마다 달라진다.
#      빙수  2816x1536 캔버스에 내용은 1427x1255  → 화면에서 502px 밖에 안 됨
#      엽떡   678x546  캔버스에 내용은  655x523   → 화면에서 648px
#    그래서 "빙수가 너무 작다" 가 된다. 배율을 손으로 만지면 편마다 또 어긋난다.
#
# 🔴 해결: 캔버스가 아니라 **내용 크기**를 기준으로 맞춘다.
#    여기서 잰 값을 ThumbTemplate 의 FoodImg 가 읽어 내용이 항상 같은 높이가 되게 그린다.
#
# 🔴 **새 음식 일러를 넣으면 이 스크립트를 다시 돌린다.**
#      python food_trim.py
import io
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIRS = ["food", "bg"]  # 썸네일 음식으로 쓰는 폴더
OUT = os.path.join(ROOT, "src", "cards", "food_trim.js")

data = {}
for d in SRC_DIRS:
    base = os.path.join(ROOT, "public", d)
    if not os.path.isdir(base):
        continue
    for name in sorted(os.listdir(base)):
        if not name.lower().endswith(".png"):
            continue
        p = os.path.join(base, name)
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue
        b = im.getbbox()
        if not b:
            continue
        w, h = im.size
        x0, y0, x1, y1 = b
        # 0~1 비율로 저장한다 — 나중에 이미지를 리사이즈해도 값이 안 깨진다
        data[f"{d}/{name}"] = [
            round(x0 / w, 4), round(y0 / h, 4),
            round((x1 - x0) / w, 4), round((y1 - y0) / h, 4),
            round(w / h, 4),  # 캔버스 가로세로비
        ]

body = ",\n".join(f'  "{k}": [{", ".join(str(v) for v in val)}]' for k, val in data.items())
js = f"""// ⚠️ 자동 생성 파일 — 손으로 고치지 마라. `python food_trim.py` 로 다시 굽는다.
//
// 음식 일러의 누끼 영역. 값은 [x, y, w, h, 캔버스비율] 이고 x,y,w,h 는 이미지 대비 0~1 비율이다.
// 투명 여백이 편마다 달라서 화면에 보이는 음식 크기가 들쭉날쭉했던 문제를 이걸로 없앤다.
export const FOOD_TRIM = {{
{body}
}};
"""
io.open(OUT, "w", encoding="utf-8").write(js)
print(f"{len(data)}개 → {OUT}")
