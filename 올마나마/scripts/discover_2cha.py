# 2차 딥리서치 파일에서 메뉴 행 파싱 → 고유 재료명·브랜드 목록 추출 (매핑표 작성용)
import json, re, os
from collections import Counter

SRC = r"C:\Users\hardb\.claude\projects\C--Users-hardb-Desktop--------------API\d7b5e9fe-4fa7-44ab-9652-0407db96dfda\tool-results\mcp-80c2493c-7e1d-4dd3-8de1-3542f548ed2c-read_file_content-1784140413634.txt"
OUT = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\discover_2cha.txt"

def clean(s):
    return s.replace("*", "").replace("\\", "").strip()

d = json.load(open(SRC, encoding="utf-8"))
t = d["fileContent"]

ing_names = Counter()
brands = Counter()
menu_count = 0
sample_rows = []

for line in t.split("\n"):
    if line.count("|") < 6:
        continue
    cells = [clean(c) for c in line.split("|")]
    if len(cells) < 7:
        continue
    if not cells[1].isdigit():
        continue
    menu_count += 1
    brand_menu = cells[2]
    # 브랜드 / 메뉴 분리
    if " / " in brand_menu:
        brand = brand_menu.split(" / ")[0].strip()
    else:
        brand = brand_menu.split()[0] if brand_menu.split() else brand_menu
    brands[brand] += 1
    ing_text = cells[6]
    if len(sample_rows) < 3:
        sample_rows.append(f"ID{cells[1]} | {brand_menu} | {ing_text[:150]}")
    # 재료: 콤마 분리 후 "이름 수량단위"
    for part in ing_text.split(","):
        part = part.strip()
        m = re.match(r"(.+?)\s+[\d.]+\s*(kg|g|L|ml|개|장|알|컵|스푼|줌)?\s*$", part)
        name = m.group(1).strip() if m else re.sub(r"[\d.]+\s*(kg|g|L|ml|개|장|알)?$", "", part).strip()
        if name:
            ing_names[name] += 1

out = [f"2차 메뉴 수: {menu_count}", "", "=== 샘플 행 ==="]
out += sample_rows
out += ["", f"=== 고유 재료명 {len(ing_names)}종 (빈도순) ==="]
for n, c in ing_names.most_common():
    out.append(f"  {c:3d}  {n}")
out += ["", f"=== 고유 브랜드 {len(brands)}종 ==="]
for b, c in brands.most_common():
    out.append(f"  {c:2d}  {b}")

open(OUT, "w", encoding="utf-8").write("\n".join(out))
print(f"메뉴 {menu_count} / 재료명 {len(ing_names)}종 / 브랜드 {len(brands)}종 → {OUT}")
