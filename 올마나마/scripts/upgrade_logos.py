# -*- coding: utf-8 -*-
# 작은 로고(16~32px)를 더 큰 버전으로 업그레이드. 구글 파비콘 sz=128 / og:image 시도 후 더 큰 것 채택.
import sqlite3, os, re, ssl, struct, urllib.request, urllib.parse, concurrent.futures

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "logos")
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
MIN = 48

def get(url, t=8):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t, context=ctx)

def dims(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "rb") as f: d = f.read(26)
        if d[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", d[16:24])
        if d[:4] == b"\x00\x00\x01\x00": return (d[6] or 256, d[7] or 256)
        if ext == ".svg": return (512, 512)   # 벡터=충분
    except Exception: pass
    return (0, 0)

def try_dl(url, slug, tag):
    try:
        r = get(url, 10)
        ct = (r.headers.get("Content-Type") or "").lower()
        data = r.read(900_000)
        if "image" not in ct or len(data) < 200: return None
        ext = ".png"
        for k, e in (("svg", ".svg"), ("jpeg", ".jpg"), ("jpg", ".jpg"), ("x-icon", ".ico"), ("webp", ".webp")):
            if k in ct: ext = e; break
        tmp = os.path.join(OUT, f"_{tag}_{slug}{ext}")
        open(tmp, "wb").write(data)
        return tmp
    except Exception:
        return None

def work(r):
    bid, name, slug, home, cur_url = r["id"], r["name"], r["slug"], r["homepage_url"], r["logo_url"]
    cur_path = os.path.join(BASE, "_preview", cur_url.replace("/", os.sep))
    cw, ch = dims(cur_path)
    if min(cw, ch) >= MIN: return None
    dom = urllib.parse.urlparse(home).netloc
    best = (min(cw, ch), cur_url)
    cands = [(f"https://www.google.com/s2/favicons?domain={dom}&sz=128", "g")]
    # og:image 후보
    try:
        h = get(home, 8).read(300_000).decode("utf-8", "ignore")
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)', h, re.I)
        if m: cands.append((urllib.parse.urljoin(home, m.group(1)), "og"))
    except Exception: pass
    for url, tag in cands:
        p = try_dl(url, slug, tag)
        if not p: continue
        w, h2 = dims(p)
        if min(w, h2) > best[0]:
            final = os.path.join(OUT, slug + os.path.splitext(p)[1])
            os.replace(p, final)
            best = (min(w, h2), f"logos/{os.path.basename(final)}")
        else:
            try: os.remove(p)
            except Exception: pass
    if best[1] != cur_url:
        return (bid, name, cur_url, best[1], best[0])
    return None

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
# logo_rejected=1 = 사용자 육안 검수에서 탈락한 브랜드(2026-07-17, 17건) — 재수집 금지.
#  근거: data/research/logo_audit.json
rows = cur.execute("""SELECT id,name,slug,homepage_url,logo_url FROM brands
    WHERE logo_url IS NOT NULL AND homepage_url!='' AND COALESCE(logo_rejected,0)=0""").fetchall()
res = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    res = [x for x in ex.map(work, rows) if x]
for bid, name, old, new, px in res:
    cur.execute("UPDATE brands SET logo_url=? WHERE id=?", (new, bid))
    print(f"  ↑ {name}: {old} → {new} ({px}px)")
con.commit()
print(f"\n업그레이드: {len(res)}개")
con.close()
