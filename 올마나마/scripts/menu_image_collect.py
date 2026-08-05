# -*- coding: utf-8 -*-
"""브랜드 공식 페이지에서 **메뉴 사진 주소**를 모은다. 2026-07-28

    python scripts/menu_image_collect.py --need          # 사진 0장인 브랜드만
    python scripts/menu_image_collect.py --only 굽네
    python scripts/menu_image_collect.py --cat 치킨

🔴 왜 «alt 만» 보면 안 되나
   목록이 `<img alt="황금올리브치킨">` 처럼 친절한 곳은 절반도 안 된다.
   `alt=""` 이거나 `alt="menu01"` 인 곳이 더 많다. 그래서 세 가지로 판정한다:

     alt   (100점)  alt/title 이 메뉴명과 맞는다            — 제일 확실
     near  ( 60점)  img 태그 **주변 DOM** 에 메뉴명이 있다  — 카드형 목록
     file  ( 30점)  파일 이름이 메뉴명과 맞는다             — 영문 슬러그 쓰는 곳

⛔ **점수가 낮다고 버리지 않는다.** 후보로 담아두고 대표컷만 골라 쓴다
   (`assume-my-filter-is-wrong-first`: «없다» 는 대개 내 필터 탓이다).
⛔ 여기서는 **주소만** 모은다. 내려받기·R2 업로드는 다음 단계다.
"""
import io
import os
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu_image_store as S                                    # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "11000"
WORKERS = 3
MAX_PAGES = 14
GUESS = ("menu/", "menu", "menu.html", "html/menu.html", "sub/menu.html",
         "product", "products", "menu/index.php")

RX_IMG = re.compile(r"(?is)<img\b[^>]*>")
RX_ATTR = re.compile(r'(?is)([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))')
RX_PATHISH = re.compile(
    r"""["'(]\s*(/?[\w/\.\-]{0,60}(?:menu|categor|product|goods)[\w/\.\-]{0,40}"""
    r"""(?:\.(?:php|html?|asp|jsp)|/)?)\s*["')]""", re.I)
SRC_ATTRS = ("src", "data-src", "data-original", "data-lazy", "data-lazy-src",
             "data-echo", "data-url", "data-img", "data-original-src")


def render(url):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,6000",
             "--virtual-time-budget=" + BUDGET, "--dump-dom", url],
            capture_output=True, timeout=90)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def attrs_of(tag):
    d = {}
    for m in RX_ATTR.finditer(tag):
        d[m.group(1).lower()] = (m.group(2) or m.group(3) or m.group(4) or "").strip()
    return d


def best_src(a, base):
    """lazy-load 를 쓰는 곳이 많다 — src 만 보면 1x1 투명 gif 만 잡힌다."""
    cands = []
    for k in SRC_ATTRS:
        if a.get(k):
            cands.append(a[k])
    if a.get("srcset"):
        # 가장 큰 것을 고른다 (`... 2x` / `... 800w`)
        best, bw = None, -1
        for part in a["srcset"].split(","):
            bits = part.strip().split()
            if not bits:
                continue
            w = 1
            if len(bits) > 1:
                mm = re.match(r"(\d+)([wx])", bits[1])
                if mm:
                    w = int(mm.group(1)) * (1000 if mm.group(2) == "x" else 1)
            if w > bw:
                best, bw = bits[0], w
        if best:
            cands.insert(0, best)
    for u in cands:
        full = urllib.parse.urljoin(base, u.strip())
        if S.looks_like_photo(full):
            return full
    return None


def cat_links(dom, base_url):
    host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()

    def add(raw):
        if not raw or raw.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            return
        u = urllib.parse.urljoin(base_url, raw).split("#")[0].replace("&amp;", "&")
        if urllib.parse.urlparse(u).netloc != host or u in seen:
            return
        if not re.search(r"(menu|categor|product|goods|메뉴|카테고리)", u, re.I):
            return
        if re.search(r"\.(png|jpe?g|gif|svg|webp|css|js|ico|woff2?)$", u, re.I):
            return
        seen.add(u)
        out.append(u)

    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\']', dom):
        add(m.group(1))
    for m in RX_PATHISH.finditer(dom):
        add(m.group(1))
    return out


def text_around(dom, pos, span=1400):
    """img 태그 주변의 **글자**. 카드형 목록은 사진 바로 옆에 메뉴명이 있다."""
    s = dom[max(0, pos - span):pos + span]
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", "", s).lower()


def scan(dom, page_url, names):
    """이 페이지에서 (메뉴명, 사진주소, 판정, 점수, alt) 목록을 뽑는다."""
    hits = []
    for m in RX_IMG.finditer(dom):
        a = attrs_of(m.group(0))
        url = best_src(a, page_url)
        if not url:
            continue
        alt = (a.get("alt") or a.get("title") or "").strip()
        nalt = S.norm_name(alt)
        fname = S.norm_name(urllib.parse.unquote(url.rsplit("/", 1)[-1].rsplit(".", 1)[0]))
        near = None                    # 주변 글자는 필요할 때만 만든다(비싸다)
        for nm, nkey in names:
            if nkey and nalt and (nkey == nalt or (len(nkey) >= 3 and nkey in nalt)):
                hits.append((nm, url, "alt", 100, alt))
                break
            if nkey and len(nkey) >= 3 and nkey in fname:
                hits.append((nm, url, "file", 30, alt))
                break
        else:
            if near is None:
                near = text_around(dom, m.start())
            # 주변에 이름이 있는 것 중 **가장 긴 이름** 하나만 — 짧은 이름은 아무 데나 걸린다
            cand = [nm for nm, nkey in names if nkey and len(nkey) >= 3 and nkey in near]
            if cand:
                hits.append((max(cand, key=len), url, "near", 60, alt))
    return hits


def do_brand(b):
    try:
        return _do(b)
    except Exception as e:
        print("  ✗ %-16s 실패: %s" % (b["name"][:16], str(e)[:70]), flush=True)
        return 0


def _do(b):
    c = S.connect()
    cur = c.cursor()
    names = [(r["name"], S.norm_name(r["name"])) for r in cur.execute(
        "SELECT DISTINCT name FROM brand_menu_official WHERE brand_id=?", (b["id"],))]
    if not names:
        print("  – %-16s 공식 메뉴가 없다 (먼저 brand_menu_list)" % b["name"][:16], flush=True)
        return 0
    url = b["u"]
    dom = render(url)
    if not dom:
        print("  ✗ %-16s 홈 렌더 실패" % b["name"][:16], flush=True)
        return 0
    root = "%s://%s/" % urllib.parse.urlparse(url)[:2]
    queue = cat_links(dom, url) + [urllib.parse.urljoin(root, g) for g in GUESS]
    queue = list(dict.fromkeys(queue))
    seen, got = {url}, 0
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")

    def take(d, u):
        n = 0
        for nm, src, how, sc, alt in scan(d, u, names):
            S.add(cur, b["id"], nm, src, src_page=u, alt_raw=alt or None,
                  match_how=how, score=sc, now=now)
            n += 1
        # 🔴 **쪽마다 커밋한다** (2026-07-28 `database is locked`).
        #    브랜드 하나를 다 훑고 커밋하면 그 몇 분 동안 쓰기 잠금을 붙들고 있어서
        #    다른 스크립트(내려받기)가 통째로 죽는다. 끊겨도 여기까지는 남는다.
        c.commit()
        return n

    got += take(dom, url)
    pages = 1
    while queue and pages < MAX_PAGES and len(seen) < MAX_PAGES * 2:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        d2 = render(u)
        if not d2:
            continue
        n = take(d2, u)
        if n:
            pages += 1
            for u3 in cat_links(d2, u):
                if u3 not in seen and len(queue) < MAX_PAGES * 2:
                    queue.append(u3)
        got += n
    c.commit()
    # 메뉴마다 대표컷 하나
    for nm, _ in names:
        S.pick_best(cur, b["id"], nm)
    c.commit()
    nm_cnt = cur.execute("""SELECT COUNT(DISTINCT menu_name) n FROM menu_image
                            WHERE brand_id=?""", (b["id"],)).fetchone()["n"]
    print("  %-16s 사진 %4d장 · 메뉴 %3d/%d개%s"
          % (b["name"][:16], got, nm_cnt, len(names),
             "  ⚠️ 0장" if not got else ""), flush=True)
    c.close()
    return got


def main():
    c = S.connect()
    need = "--need" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    cat = sys.argv[sys.argv.index("--cat") + 1] if "--cat" in sys.argv else None
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 100
    q = """SELECT b.id, b.name, b.homepage_url u, c.name cn
           FROM brands b LEFT JOIN categories c ON c.id=b.category_id
           WHERE b.published=1 AND COALESCE(b.homepage_url,'') <> ''
             AND EXISTS(SELECT 1 FROM brand_menu_official o WHERE o.brand_id=b.id)"""
    if need:
        q += " AND NOT EXISTS(SELECT 1 FROM menu_image i WHERE i.brand_id=b.id)"
    q += " ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?"
    rows = [dict(r) for r in c.execute(q, (top,))]
    if only:
        rows = [r for r in rows if only in r["name"]]
    if cat:
        rows = [r for r in rows if cat in (r.get("cn") or "")]
    c.close()
    print("브랜드 %d곳 · 공식 페이지에서 메뉴 사진 주소 수집\n" % len(rows), flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    print("\n끝. 사진 후보 %d장" % sum(res), flush=True)


if __name__ == "__main__":
    main()
