# -*- coding: utf-8 -*-
"""대표컷을 **내려받아 webp 로 줄여** `_preview/menuimg/` 에 넣는다. 2026-07-28

    python scripts/menu_image_fetch.py --only 굽네
    python scripts/menu_image_fetch.py --need        # 아직 안 받은 것만
    python scripts/menu_image_fetch.py --recheck     # rejected 도 다시

🔴 왜 R2 가 아니라 정적 자산인가 (2026-07-28 판단)
   대표가 «R2 도 있다» 고 했지만, 이 사이트는 **워커 스크립트가 없는 정적 자산 배포**다
   (`wrangler.toml` 의 `[assets] directory = ../../_dist`, `main` 없음).
   R2 를 쓰려면 워커 스크립트를 되살리고 바인딩·라우팅을 새로 짜야 한다.
   **로고 102장이 이미 `_dist/logos` 로 잘 나가고 있다** — 사진도 같은 길로 보낸다.
   정적 자산 한도는 20,000개 / 개당 25MiB 라 메뉴 사진 1,000여 장은 여유가 크다.

🔴 왜 원본을 그대로 안 쓰나
   목록 썸네일에 1,200px PNG 를 그대로 깔면 한 페이지가 수십 MB 가 된다.
   **가로 420px webp** 로 줄인다 — 카드 그리드에서 2배 밀도(210pt)까지 선명하다.

⛔ 핫링크 금지. 받아서 우리 도메인으로 서빙한다. 브랜드 CDN 경로는 시즌마다 바뀐다.
⛔ 받아본 뒤 **로고·아이콘으로 판명되면 `rejected`** 로 돌리고 다음 후보를 올린다
   (가로세로가 같고 작으면 대개 아이콘이다).
"""
import io
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu_image_store as S                                     # noqa: E402
from PIL import Image                                            # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "_preview", "menuimg")
WIDTH = 420
QUALITY = 78
MIN_SIDE = 120          # 이보다 작으면 썸네일이 아니라 아이콘이다
WORKERS = 6

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}


def slugify(brand_slug, name):
    s = re.sub(r"[^\w가-힣]+", "-", (name or "")).strip("-")[:48] or "x"
    return "%s-%s" % (brand_slug or "b", s)


def one(job):
    """(row, brand_slug) → 받아서 줄이고 **파일로만** 저장한다.

    🔴 DB 는 손대지 않는다 (2026-07-28 `database is locked`).
       스레드 6개가 각자 커넥션을 열고 쓰면 백그라운드 수집기와 물려 잠긴다.
       **쓰기는 메인 스레드 한 곳에서** 몰아서 한다.
    """
    r, bslug = job
    try:
        req = urllib.request.Request(r["src_url"], headers=dict(
            UA, Referer="%s://%s/" % urllib.parse.urlparse(r["src_url"])[:2]))
        blob = urllib.request.urlopen(req, timeout=20, context=ctx).read(8_000_000)
        if len(blob) < 400:
            return {"id": r["id"], "kind": "reject", "nm": r["menu_name"],
                    "why": "파일이 너무 작다(%dB)" % len(blob)}
        im = Image.open(io.BytesIO(blob))
        w, h = im.size
        if min(w, h) < MIN_SIDE:
            return {"id": r["id"], "kind": "reject", "nm": r["menu_name"],
                    "why": "너무 작다 %dx%d — 아이콘" % (w, h)}
        sha = S.sha1_of(blob)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if w > WIDTH:
            im = im.resize((WIDTH, max(1, round(h * WIDTH / w))), Image.LANCZOS)
        os.makedirs(OUT, exist_ok=True)
        key = "menuimg/%s.webp" % slugify(bslug, r["menu_name"])
        path = os.path.join(BASE, "_preview", key)
        im.save(path, "WEBP", quality=QUALITY, method=5)
        return {"id": r["id"], "kind": "ok", "nm": r["menu_name"], "w": w, "h": h,
                "bytes": os.path.getsize(path), "sha1": sha, "key": key}
    except Exception as e:
        return {"id": r["id"], "kind": "fail", "nm": r["menu_name"], "why": str(e)[:90]}


def main():
    c = S.connect()
    cur = c.cursor()
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    st = "status IN ('found','rejected')" if "--recheck" in sys.argv else "status='found'"
    q = """SELECT i.*, b.slug bslug, b.name bname FROM menu_image i
           JOIN brands b ON b.id=i.brand_id
           WHERE i.picked=1 AND %s""" % st
    rows = [dict(r) for r in cur.execute(q)]
    if only:
        rows = [r for r in rows if only in (r["bname"] or "")]
    print("대표컷 %d장 내려받아 webp %dpx 로 줄인다\n" % (len(rows), WIDTH), flush=True)
    c.close()
    jobs = [(r, r["bslug"]) for r in rows]
    ok = rej = fail = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(one, jobs))
    # 쓰기는 여기 한 곳에서만 (스레드에서 쓰면 잠긴다)
    c = S.connect()
    cur = c.cursor()
    for d in res:
        if d["kind"] == "ok":
            ok += 1
            cur.execute("""UPDATE menu_image SET status='uploaded', width=?, height=?,
                           bytes=?, sha1=?, r2_key=?, why=NULL WHERE id=?""",
                        (d["w"], d["h"], d["bytes"], d["sha1"], d["key"], d["id"]))
        else:
            cur.execute("UPDATE menu_image SET status='rejected', picked=0, why=? WHERE id=?",
                        (d["why"], d["id"]))
            if d["kind"] == "reject":
                rej += 1
            else:
                fail += 1
                print("  ✗ %-18s %s" % (d["nm"][:18], d["why"][:60]), flush=True)
    c.commit()
    c.close()
    print("\n받음 %d · 걸러냄 %d · 실패 %d → _preview/menuimg/" % (ok, rej, fail))

    # 걸러낸 자리에는 **다음 후보**를 올린다 — 한 번 실패했다고 그 메뉴를 비우지 않는다
    c = S.connect()
    cur = c.cursor()
    n = 0
    for b, nm in cur.execute("""SELECT DISTINCT brand_id,menu_name FROM menu_image
        WHERE brand_id||'|'||menu_name NOT IN
              (SELECT brand_id||'|'||menu_name FROM menu_image WHERE status='uploaded')
          AND status<>'rejected'""").fetchall():
        if S.pick_best(cur, b, nm):
            n += 1
    c.commit()
    if n:
        print("다음 후보로 교체한 메뉴 %d개 — 한 번 더 돌리면 채워진다" % n)


if __name__ == "__main__":
    main()
