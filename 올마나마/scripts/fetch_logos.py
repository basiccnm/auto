# -*- coding: utf-8 -*-
# 브랜드 공식 홈페이지에서 로고(아이콘) 실제 다운로드 → _preview/logos/ 에 호스팅, brands.logo_url 갱신.
#  기존 logo_url은 Gemini 추측값이라 116/122가 404 → 폐기하고 실제 파일로 교체.
#  우선순위: apple-touch-icon > link rel=icon(큰것) > og:image(정사각 추정) > 구글 파비콘 서비스(sz=128)
import sqlite3, os, re, ssl, urllib.request, urllib.parse, concurrent.futures

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "logos")
os.makedirs(OUT, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

def get(url, timeout=8):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)

def find_icons(html, base_url):
    out = []
    # apple-touch-icon (보통 180x180 정사각 = 배지에 최적)
    for m in re.finditer(r'<link[^>]+rel=["\']?[^"\'>]*apple-touch-icon[^"\'>]*["\']?[^>]*>', html, re.I):
        h = re.search(r'href=["\']([^"\']+)', m.group(0), re.I)
        if h: out.append((0, urllib.parse.urljoin(base_url, h.group(1))))
    # link rel=icon / shortcut icon
    for m in re.finditer(r'<link[^>]+rel=["\']?[^"\'>]*\bicon\b[^"\'>]*["\']?[^>]*>', html, re.I):
        h = re.search(r'href=["\']([^"\']+)', m.group(0), re.I)
        if h: out.append((1, urllib.parse.urljoin(base_url, h.group(1))))
    # og:image
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
    if m: out.append((2, urllib.parse.urljoin(base_url, m.group(1))))
    out.sort(key=lambda x: x[0])
    return [u for _, u in out]

def download(url, slug):
    r = get(url, 10)
    ct = (r.headers.get("Content-Type") or "").lower()
    data = r.read(600_000)
    if "image" not in ct or len(data) < 120:
        return None
    ext = ".png"
    for k, e in (("svg", ".svg"), ("jpeg", ".jpg"), ("jpg", ".jpg"), ("x-icon", ".ico"), ("vnd.microsoft.icon", ".ico"), ("webp", ".webp")):
        if k in ct: ext = e; break
    path = os.path.join(OUT, slug + ext)
    open(path, "wb").write(data)
    return f"logos/{slug}{ext}"

def work(row):
    bid, name, slug, home = row["id"], row["name"], row["slug"], row["homepage_url"]
    dom = urllib.parse.urlparse(home).netloc
    # 1) 공식 홈페이지에서 아이콘 링크 추출
    try:
        r = get(home, 10)
        html = r.read(400_000).decode("utf-8", "ignore")
        for u in find_icons(html, r.geturl())[:4]:
            try:
                p = download(u, slug)
                if p: return (bid, name, p, "site")
            except Exception:
                continue
    except Exception:
        pass
    # 2) /favicon.ico 직접
    try:
        p = download(urllib.parse.urljoin(home, "/favicon.ico"), slug)
        if p: return (bid, name, p, "favicon")
    except Exception:
        pass
    # 3) 구글 파비콘 서비스 (거의 항상 성공)
    try:
        p = download(f"https://www.google.com/s2/favicons?domain={dom}&sz=128", slug)
        if p: return (bid, name, p, "google")
    except Exception:
        pass
    return (bid, name, None, "FAIL")

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
# 로고 없는 브랜드만 대상(이미 확보/업그레이드된 로고는 보존). 전체 재수집하려면 AND절 제거.
# logo_rejected=1 = 사용자가 눈으로 보고 "이건 그 브랜드 로고가 아니다"라고 판정한 것(2026-07-17, 17건).
#  이 가드를 빼면 여기서 똑같이 틀린 로고를 다시 가져와 덮어쓴다. 근거: data/research/logo_audit.json
rows = cur.execute("""SELECT id,name,slug,homepage_url FROM brands
    WHERE homepage_url!='' AND logo_url IS NULL AND COALESCE(logo_rejected,0)=0 ORDER BY id""").fetchall()
res = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(work, rows))

ok = 0
for bid, name, path, how in res:
    if path:
        cur.execute("UPDATE brands SET logo_url=? WHERE id=?", (path, bid)); ok += 1
    else:
        cur.execute("UPDATE brands SET logo_url=NULL WHERE id=?", (bid,))
con.commit()
from collections import Counter
c = Counter(h for _, _, _, h in res)
print(f"로고 확보: {ok}/{len(res)}  (출처: {dict(c)})")
print("\n[실패 = 텍스트 배지 유지]")
for bid, name, path, how in res:
    if not path: print(f"  [{bid}] {name}")
con.close()
