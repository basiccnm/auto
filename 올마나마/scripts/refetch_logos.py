# -*- coding: utf-8 -*-
# 로고 재수집 2차 (2026-07-17) — 텍스트 배지 31개 브랜드를 제대로 다시 찾는다.
#
# ★ 1차(fetch_logos.py)가 78개 중 17개(22%)를 틀린 이유:
#   폴백으로 **og:image**를 썼다. og:image는 로고가 아니라 **홍보 배너·음식 사진**이다.
#   (명랑핫도그가 음식 사진이었던 게 이것) → 여기선 og:image를 아예 쓰지 않는다.
#
# 이번 전략: 헤더/네비의 **진짜 로고 <img>** 를 찾는다.
#   1순위 src/class/alt/id 에 logo 힌트가 있는 <img>  (진짜 로고일 확률 최고)
#   2순위 apple-touch-icon (보통 브랜드 심볼)
#   3순위 favicon
#   ❌ og:image 제외
#
# 받아온 건 **자동으로 믿지 않는다.** logo_pending=1 로 표시 → _logo_audit.html 에서 사용자가 확인.
# 사용법: python scripts/refetch_logos.py
import sqlite3, os, re, urllib.request, urllib.parse, ssl
from concurrent.futures import ThreadPoolExecutor

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "logos")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
cols = {r[1] for r in cur.execute("PRAGMA table_info(brands)")}
if "logo_pending" not in cols:
    cur.execute("ALTER TABLE brands ADD COLUMN logo_pending INTEGER DEFAULT 0")
    print("  + 컬럼: brands.logo_pending (사용자 확인 대기 표시)")
con.commit()

def get(url, t=10):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t, context=ctx)

LOGO_HINT = re.compile(r"logo|symbol|bi[_-]|ci[_-]|brand", re.I)
BAD_HINT = re.compile(r"sprite|banner|bg[_-]|background|event|popup|sns|facebook|insta|youtube|blog|kakao|btn|icon[_-]arrow", re.I)

def candidates(html, base_url):
    """헤더의 진짜 로고 <img>를 우선순위대로. og:image는 절대 쓰지 않는다."""
    out = []
    for m in re.finditer(r"<img[^>]+>", html, re.I):
        tag = m.group(0)
        src = re.search(r'(?:data-src|src)=["\']([^"\']+)', tag, re.I)
        if not src: continue
        u = src.group(1).strip()
        if u.startswith("data:"): continue
        blob = tag  # class/alt/id/src 전체에서 힌트 탐색
        if not LOGO_HINT.search(blob): continue
        if BAD_HINT.search(blob): continue
        out.append((0, urllib.parse.urljoin(base_url, u)))
    # 2순위: apple-touch-icon (브랜드 심볼인 경우가 많음)
    for m in re.finditer(r'<link[^>]+apple-touch-icon[^>]*>', html, re.I):
        h = re.search(r'href=["\']([^"\']+)', m.group(0), re.I)
        if h: out.append((1, urllib.parse.urljoin(base_url, h.group(1))))
    # 3순위: favicon
    for m in re.finditer(r'<link[^>]+rel=["\']?[^"\'>]*\bicon\b[^"\'>]*["\']?[^>]*>', html, re.I):
        h = re.search(r'href=["\']([^"\']+)', m.group(0), re.I)
        if h: out.append((2, urllib.parse.urljoin(base_url, h.group(1))))
    seen, res = set(), []
    for pri, u in sorted(out, key=lambda x: x[0]):
        if u in seen: continue
        seen.add(u); res.append(u)
    return res[:6]

def download(url, slug):
    try:
        r = get(url)
        ct = (r.headers.get("Content-Type") or "").lower()
        data = r.read(900_000)
    except Exception:
        return None
    if "image" not in ct or len(data) < 200:
        return None
    ext = ".png"
    for k, e in (("svg", ".svg"), ("jpeg", ".jpg"), ("jpg", ".jpg"),
                 ("x-icon", ".ico"), ("vnd.microsoft.icon", ".ico"), ("webp", ".webp")):
        if k in ct: ext = e; break
    path = os.path.join(OUT, f"{slug}_v2{ext}")
    open(path, "wb").write(data)
    return f"logos/{slug}_v2{ext}", len(data)

def work(r):
    home = r["homepage_url"]
    if not home: return (r["id"], r["name"], None, "홈페이지 없음")
    try:
        html = get(home).read(400_000).decode("utf-8", "ignore")
    except Exception as e:
        return (r["id"], r["name"], None, f"접속 실패({type(e).__name__})")
    for u in candidates(html, home):
        got = download(u, r["slug"])
        if got:
            return (r["id"], r["name"], got[0], f"{got[1]//1024}KB · {u[:60]}")
    return (r["id"], r["name"], None, "로고 후보 없음")

# 대상: 텍스트 배지로 나가는 31개 (1차 탈락 17 + 처음부터 못 받은 14)
rows = cur.execute("SELECT id,name,slug,homepage_url FROM brands WHERE logo_url IS NULL ORDER BY id").fetchall()
print(f"재수집 대상: {len(rows)}개\n")

ok = fail = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    for bid, name, path, note in ex.map(work, rows):
        if path:
            cur.execute("UPDATE brands SET logo_url=?, logo_pending=1, logo_rejected=0 WHERE id=?", (path, bid))
            print(f"  ✓ {name:16} {note}")
            ok += 1
        else:
            print(f"  · {name:16} {note} → 이름 배지 유지")
            fail += 1
con.commit()
print(f"\n찾음 {ok}개(사용자 확인 대기) · 못 찾음 {fail}개(이름 배지)")
print("→ python scripts/gen_logo_audit.py 로 검수 시트 재생성 후 확인 필요")
con.close()
