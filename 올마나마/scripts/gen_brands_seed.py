# brands_raw.tsv → categories + brands 시드 SQL 생성
# 슬러그: 홈페이지 도메인 SLD(또는 경로 세그먼트)에서 추출, 충돌 시 -N 부여
import re, os
from urllib.parse import urlparse

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
SRC = os.path.join(BASE, "data", "brands_raw.tsv")
OUT = os.path.join(BASE, "data", "seed_brands.sql")

# 카테고리 → (slug, tier)
CAT = {
    "치킨": ("chicken", "대형"),
    "피자": ("pizza", "대형"),
    "버거": ("burger", "대형"),
    "분식/떡볶이": ("bunsik", "대형"),
    "족발/보쌈": ("jokbal", "중형"),
    "한식/죽/국밥": ("hansik", "중형"),
    "중식/마라탕": ("jungsik", "중형"),
    "일식/돈까스": ("ilsik", "중형"),
}

def slug_from_url(url):
    p = urlparse(url)
    host = p.netloc
    path_segs = [s for s in p.path.split("/") if s]
    # 경로 세그먼트가 있으면(예: /nobrandburger/) 그걸 우선 사용
    if path_segs and not path_segs[-1].isdigit():
        return re.sub(r"[^a-z0-9]", "", path_segs[-1].lower())
    # 도메인 SLD 추출: www/web 접두 제거 후 첫 라벨
    labels = host.split(".")
    labels = [l for l in labels if l not in ("www", "web")]
    sld = labels[0] if labels else host
    return re.sub(r"[^a-z0-9]", "", sld.lower())

rows = []
for line in open(SRC, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) < 4:
        continue
    cat, brand, home, logo = parts[0], parts[1], parts[2], parts[3]
    rows.append((cat, brand, home, logo))

# 카테고리 시드
cats_seen = []
for cat, *_ in rows:
    if cat not in cats_seen:
        cats_seen.append(cat)

out = ["-- 얼마남아 카테고리+브랜드 시드 (자동생성: gen_brands_seed.py)", ""]
for i, cat in enumerate(cats_seen, 1):
    slug, tier = CAT[cat]
    out.append(
        f"INSERT INTO categories (name,slug,tier,sort_order,created_at) "
        f"VALUES ('{cat}','{slug}','{tier}',{i},datetime('now'));")
out.append("")

# 브랜드 시드 (슬러그 충돌 처리)
used = {}
brand_sort = {}
for cat, brand, home, logo in rows:
    cat_slug = CAT[cat][0]
    s = slug_from_url(home)
    if not s:
        s = "brand"
    base = s
    n = used.get(base, 0)
    if n:
        s = f"{base}{n+1}"
    used[base] = n + 1
    brand_sort[cat_slug] = brand_sort.get(cat_slug, 0) + 1
    b = brand.replace("'", "''")
    out.append(
        "INSERT INTO brands (category_id,name,slug,homepage_url,logo_url,sort_order,created_at) "
        f"VALUES ((SELECT id FROM categories WHERE slug='{cat_slug}'),'{b}','{s}',"
        f"'{home}','{logo}',{brand_sort[cat_slug]},datetime('now'));")

open(OUT, "w", encoding="utf-8").write("\n".join(out))
print(f"카테고리 {len(cats_seen)}개, 브랜드 {len(rows)}개 → {OUT}")
