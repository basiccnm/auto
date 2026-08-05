# 새 카테고리 + 추가 브랜드 27개 등록 (brands_raw2.tsv)
import re, os, sqlite3
from urllib.parse import urlparse

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
SRC = os.path.join(BASE, "data", "brands_raw2.tsv")
DB = os.path.join(BASE, "data", "eolmanama.db")

# 신규 카테고리 (slug → 이름, tier, sort)
NEW_CATS = {
    "cafe": ("카페/디저트", "대형", 9),
    "salad": ("샐러드/포케", "중형", 10),
    "bakery": ("베이커리", "중형", 11),
    "gopchang": ("곱창/막창", "소형", 12),
    "pub": ("주점/야식", "소형", 13),
}

def slug_from_url(url):
    p = urlparse(url); host = p.netloc
    labels = [l for l in host.split(".") if l not in ("www", "web")]
    sld = labels[0] if labels else host
    return re.sub(r"[^a-z0-9]", "", sld.lower())

con = sqlite3.connect(DB); cur = con.cursor()

# 신규 카테고리 생성
for slug, (nm, tier, so) in NEW_CATS.items():
    cur.execute("INSERT OR IGNORE INTO categories (name,slug,tier,sort_order,created_at) VALUES (?,?,?,?,datetime('now'))",
                (nm, slug, tier, so))

# 기존 슬러그 수집(충돌 방지)
used = {r[0]: 1 for r in cur.execute("SELECT slug FROM brands").fetchall()}

added = 0
for line in open(SRC, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip(): continue
    cat_slug, brand, home, logo = line.split("\t")
    logo = re.sub(r"\.png\d+$", ".png", logo)  # 각주번호 제거
    # 이미 있으면 skip
    if cur.execute("SELECT 1 FROM brands WHERE name=?", (brand,)).fetchone():
        continue
    s = slug_from_url(home) or "brand"
    base = s; n = used.get(base, 0)
    if n: s = f"{base}{n+1}"
    used[base] = n + 1; used.setdefault(s, 1)
    cid = cur.execute("SELECT id FROM categories WHERE slug=?", (cat_slug,)).fetchone()
    if not cid: continue
    cur.execute("INSERT INTO brands (category_id,name,slug,homepage_url,logo_url,sort_order,created_at) VALUES (?,?,?,?,?,99,datetime('now'))",
                (cid[0], brand, s, home, logo))
    added += 1

con.commit()
print(f"신규 카테고리 {len(NEW_CATS)}개, 브랜드 {added}개 추가")
print("전체 브랜드:", cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0])
con.close()
