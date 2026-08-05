# -*- coding: utf-8 -*-
"""브랜드 **메뉴 목록 페이지**를 읽어 메뉴명·가격·중량을 뽑는다. 2026-07-27

🔴 두 번 실패하고 찾은 정답 (대표: *"직접 다 읽기로 했잖아?? 근데 왜 긁어만 와??"*)
   ① `brand_menu_detail.py` — **상세페이지 본문**에서 이름을 추측 → BBQ 에서 `양념` `구이` `세트`
      `음료 선택` 같은 **옵션 라벨**이 잡혀 우리 DB 연결률 2%.
   ② 링크 글자로 잡기 — 사이트마다 상세 링크가 없어 절반이 빈다.

   ✅ **목록 페이지는 구조가 깔끔하다.** 실제로 읽어보니 블록이 규칙적으로 반복된다:
        황금올리브치킨™                          ← 메뉴명
        겉은 바삭 육즙 가득한 …                    ← 설명(긴 문장)
        23,000원                              ← 가격
        * 조리전 중량 : 10호(951~1050g) 이상       ← 중량
   그래서 **가격 줄을 기준으로** 위=이름, 아래=중량을 읽는다. 상세페이지는 볼 필요가 없다.

   이 방식으로 BBQ 우리 DB 4개가 가격까지 전부 맞았고,
   자메이카 통다리구이의 "통다리(장각) 4조각" 도 공식 문구로 확인됐다.

⛔ 중량이 g 으로 안 적혀 있으면 **원문만 담고 g 은 비운다**("통다리(장각) 4조각" 같은 것).
   업태 기본중량으로 채우지 않는다 — 그건 검수에서 사람이 한다(`ingredients-evidence-only`).

    python scripts/brand_menu_list.py --only BBQ
    python scripts/brand_menu_list.py --top 100
    python scripts/brand_menu_list.py --only-empty
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# 🔴 출력 인코딩을 박아둔다 (2026-07-28).
#    Bash 로 돌리면 stdout 이 cp949 라 «⚠️·✗» 한 글자에서 `UnicodeEncodeError` 가 나고,
#    그게 스레드 예외 → 전체 run 이 통째로 죽는다. 치킨 14곳이 이렇게 한 건도 못 모았다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "brand_menu_list")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "11000"
WORKERS = 4
MAX_PAGES = 14           # 목록·카테고리 페이지 상한

JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")
LISTWORD = ("메뉴", "menu", "product", "goods", "카테고리", "categor", "제품")
GUESS = ("menu/", "menu", "menu.html", "html/menu.html", "sub/menu.html",
         "product", "products", "menu/index.php")

RX_PRICE = re.compile(r"^([\d,]{3,9})\s*원\s*$")
RX_WEIGHT = re.compile(r"중량\s*[:：]\s*(.+)$")
RX_G = re.compile(r"([\d,]+)\s*~\s*([\d,]+)\s*g|([\d,.]+)\s*(kg|g)\b", re.I)
RX_TAG = re.compile(r"^\s*[\[(【]\s*[^\])】]{1,12}\s*[\])】]\s*")

# 메뉴명이 아닌 줄
NAV = ("메뉴", "전체", "더보기", "다음", "이전", "닫기", "검색", "로그인", "회원가입",
       "장바구니", "주문", "주문하기", "매장 찾기", "매장찾기", "이벤트", "쿠폰", "공지사항",
       "고객센터", "브랜드", "회사소개", "채용", "창업", "창업문의", "가맹문의", "이용안내",
       "전화주문", "마이 페이지", "배달", "포장", "추천", "세트", "사이드", "음료", "신메뉴",
       "베스트", "인기", "홈", "PICK", "DELIVERY", "PACKAGING", "MENU", "HOME", "ALL")
RX_SENT = re.compile(r"(하세요|합니다|입니다|바랍니다|드립니다|있습니다|없습니다|가능합니다)$")


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


def to_lines(dom):
    s = JUNK_TAG.sub(" ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd|strong|em)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&#8482;", "™")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    out = [l.strip() for l in s.split("\n") if l.strip()]

    # 🔴 «23,000» 과 «원» 이 두 줄로 쪼개져 오는 사이트가 있다 (2026-07-27).
    #    가격을 `<span>23,000</span><span>원</span>` 처럼 감싸면 태그가 줄바꿈이 되어 갈라진다.
    #    `RX_PRICE` 는 한 줄에 «숫자+원» 이 다 있어야 인식하므로 그런 사이트가 통째로 0건이 됐다
    #    (네네치킨·도미노피자 등). 여기서 다시 붙인다.
    merged = []
    i = 0
    while i < len(out):
        cur = out[i]
        if (i + 1 < len(out) and out[i + 1] == "원"
                and re.match(r"^\d{1,3}(?:,\d{3})+$|^\d{3,6}$", cur)):
            merged.append(cur + "원")
            i += 2
            continue
        merged.append(cur)
        i += 1
    return merged


def is_name(l):
    """메뉴명일 수 있는 줄인가. 꼬리표([NEW] 등)는 남겨둔다 — 공식 표기 그대로 쓴다."""
    t = l.strip()
    if not (2 <= len(t) <= 40):
        return False
    if RX_PRICE.match(t) or t.startswith(("*", "＊", "(", "·", "-", "//")):
        return False
    if RX_SENT.search(t):
        return False
    bare = RX_TAG.sub("", t).strip()
    if bare in NAV or t in NAV or bare.upper() in NAV:
        return False
    if not re.search(r"[가-힣A-Za-z]", t):
        return False
    if len(t) > 24 and re.search(r"[,。]", t):    # 설명문
        return False
    return True


def parse_list(lines):
    """가격 줄을 기준으로 블록을 읽는다. 한 페이지의 메뉴 목록."""
    out = []
    for i, l in enumerate(lines):
        m = RX_PRICE.match(l)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        if not (500 <= price <= 300000):
            continue
        # ① 위로 올라가며 이름 — 설명·프로모션 문구를 건너뛴다
        #    🔴 «가장 가까운 후보» 로 잡으면 **설명문이 이름이 된다** (2026-07-27).
        #       네네치킨에서 실제로 그랬다:
        #           오리엔탈파닭                                   ← 진짜 이름
        #           새콤달콤 짭조름한 오리엔탈 소스에 신선한 파가 듬뿍   ← 이게 잡혔다
        #           23,000원
        #       메뉴명은 **짧고 띄어쓰기가 적고**, 설명문은 그 반대다.
        #       그래서 창 안의 후보를 다 모은 뒤 «띄어쓰기 적은 순 → 짧은 순» 으로 고른다.
        cands = [lines[j] for j in range(i - 1, max(-1, i - 7), -1) if is_name(lines[j])]
        if not cands:
            continue
        name = min(cands, key=lambda t: (t.count(" "), len(t)))
        # ② 아래에서 중량 (보통 가격 바로 다음 줄)
        wraw = wg = None
        for j in range(i + 1, min(len(lines), i + 4)):
            mm = RX_WEIGHT.search(lines[j])
            if mm:
                wraw = mm.group(1).strip()[:60]
                g = RX_G.search(wraw)
                if g:
                    if g.group(1):
                        wg = round((int(g.group(1).replace(",", ""))
                                    + int(g.group(2).replace(",", ""))) / 2.0)
                    else:
                        v = float(g.group(3).replace(",", ""))
                        wg = round(v * 1000 if g.group(4).lower() == "kg" else v)
                break
        out.append({"name": name, "price": price, "weight_raw": wraw, "weight_g": wg})
    return out


def anchor_labels(dom, base_url):
    """메뉴 페이지의 링크 글자들.
    🔴 왜 필요한가(2026-07-27): **대부분의 브랜드 홈페이지는 메뉴 목록에 가격을 안 적는다**
       (가격은 배달앱에만 있다). 그래서 가격 줄을 기준으로 읽는 방식이 87곳에서 0개가 됐다.
       가격이 없어도 **메뉴명만이라도** 가져와야 한다 — 이름이 있으면 대조가 되고,
       가격·중량은 비워둔다(`ingredients-evidence-only`: 빈칸이 가짜보다 낫다)."""
    host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', dom):
        href = m.group(1)
        if href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        u = urllib.parse.urljoin(base_url, href).split("#")[0]
        if urllib.parse.urlparse(u).netloc != host:
            continue
        t = re.sub(r"<[^>]+>", " ", m.group(2))
        t = re.sub(r"&[a-z]+;|&#\d+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t and t not in seen and is_name(t):
            seen.add(t)
            out.append(t)
    # 링크가 아닌 카드형 목록도 있다 — alt 글자를 본다
    for m in re.finditer(r'(?is)<img[^>]+alt=["\']([^"\']{2,40})["\']', dom):
        t = re.sub(r"\s+", " ", m.group(1)).strip()
        if t and t not in seen and is_name(t):
            seen.add(t)
            out.append(t)
    return out


# 🔴 `<a href>` 만 보면 놓친다(2026-07-27): 신전떡볶이는 `javascript:GoPage('menu01')` 로 이동해
#    링크가 하나도 안 잡혔다. 실제 경로 `/doc/menu01.php`~`menu06.php` 는 **DOM 본문 안에** 있었다.
#    그래서 DOM 전체에서 메뉴처럼 보이는 경로 문자열도 같이 긁는다.
RX_PATHISH = re.compile(
    r"""["'(]\s*(/?[\w/\.\-]{0,60}(?:menu|categor|product|goods)[\w/\.\-]{0,40}"""
    r"""(?:\.(?:php|html?|asp|jsp)|/)?)\s*["')]""", re.I)


def cat_links(dom, base_url):
    """메뉴 카테고리 탭 주소들 (치킨·사이드·음료 …)."""
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


def do_brand(b):
    try:
        return _do(b)
    except Exception as e:
        print("  ✗ %-16s 실패: %s" % (b["name"][:16], str(e)[:60]), flush=True)
        return {"brand": b["name"], "slug": b["slug"], "menus": [], "pages": [],
                "error": str(e)[:120]}


def _do(b):
    url = b["u"]
    dom = render(url)
    rec = {"brand": b["name"], "slug": b["slug"], "url": url, "pages": [], "menus": []}
    if not dom:
        print("  ✗ %-16s 홈 렌더 실패" % b["name"][:16], flush=True)
        return rec
    root = "%s://%s/" % urllib.parse.urlparse(url)[:2]
    queue = cat_links(dom, url) + [urllib.parse.urljoin(root, g) for g in GUESS]
    queue = list(dict.fromkeys(queue))
    seen, byname = {url}, {}
    lab_pages = []           # 가격이 없는 사이트용 — 쪽별 링크 글자

    # 🔴 홈페이지 자체를 파싱한다 (2026-07-27).
    #    전에는 홈을 렌더만 해놓고 `seen` 에 넣은 뒤 **다른 페이지만** 훑었다.
    #    그래서 **메뉴가 홈에 있는 사이트가 통째로 0쪽**이 됐다 —
    #    네네치킨(오리엔탈파닭 23,000 …)·도미노피자(치즈 L 23,900 …) 둘 다 홈에 메뉴가 다 있는데
    #    «0쪽 · 메뉴 0개» 로 나왔고, 그걸 «사이트가 막혔다» 로 오판했다.
    #    헤드리스 크롬은 멀쩡했다(실측: 네네 홈 DOM 185KB, 가격 7건).
    _home = parse_list(to_lines(dom))
    _labs = anchor_labels(dom, url)
    if _home or _labs:
        rec["pages"].append(url)
    for g in _home:
        k = re.sub(r"\s+", "", g["name"])
        if k not in byname:
            g["src"] = url
            byname[k] = g
    if _labs:
        lab_pages.append({"url": url, "labels": _labs})
    while queue and len(seen) < MAX_PAGES * 2:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        d2 = render(u)
        if not d2:
            continue
        got = parse_list(to_lines(d2))
        labs = anchor_labels(d2, u)
        if got or labs:
            rec["pages"].append(u)
        for g in got:
            k = re.sub(r"\s+", "", g["name"])
            if k not in byname:
                g["src"] = u
                byname[k] = g
        if labs:
            lab_pages.append({"url": u, "labels": labs})
        if got or labs:
            for u3 in cat_links(d2, u):
                if u3 not in seen and len(queue) < MAX_PAGES * 2:
                    queue.append(u3)
        if len(rec["pages"]) >= MAX_PAGES:
            break

    # 가격 블록으로 못 잡은 메뉴는 **링크 글자**에서 채운다.
    # 내비게이션은 모든 쪽에 나오므로 절반 넘게 반복되는 글자는 버린다.
    if lab_pages:
        from collections import Counter
        freq = Counter()
        for p in lab_pages:
            freq.update(set(p["labels"]))
        cut = max(2, len(lab_pages) // 2) if len(lab_pages) >= 3 else len(lab_pages) + 1
        for p in lab_pages:
            for t in p["labels"]:
                if freq[t] > cut:
                    continue
                k = re.sub(r"\s+", "", t)
                if k not in byname:
                    byname[k] = {"name": t, "price": None, "weight_raw": None,
                                 "weight_g": None, "src": p["url"]}
    rec["menus"] = list(byname.values())
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "%s.json" % (b["slug"] or b["name"])), "w",
            encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
    nw = sum(1 for m in rec["menus"] if m["weight_raw"])
    print("  %-16s %2d쪽 · 메뉴 %3d개 · 중량 %2d개%s" % (
        b["name"][:16], len(rec["pages"]), len(rec["menus"]), nw,
        "  ⚠️ 0개" if not rec["menus"] else ""), flush=True)
    return rec


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 100
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    # 🔴 카테고리로 나눠 **여러 프로세스를 동시에** 돌린다(2026-07-27 대표 지시:
    #    *"데이터 없는거는 백그라운드 돌리면서 데이터 모으는데 카테고리로 나눠서 몇개 작업 시키면 빠르겠지"*).
    #    같은 업종끼리 묶이니 뒤이어 하는 재료 작업도 수월하다.
    #    `--cats` 로 카테고리 목록만 볼 수 있다.
    cat = sys.argv[sys.argv.index("--cat") + 1] if "--cat" in sys.argv else None
    # 공식 메뉴 **판매가가 하나도 없는** 브랜드만 (이미 모은 곳을 또 긁지 않는다)
    need_only = "--need" in sys.argv
    cond = "= 0" if "--only-empty" in sys.argv else (
        ">= 0" if "--include-empty" in sys.argv else "> 0")
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    if "--cats" in sys.argv:
        print("카테고리별 — 공개 브랜드 / 공식 판매가 있는 곳")
        for r in c.execute("""
            SELECT c.name cn, COUNT(*) n,
                   SUM((SELECT COUNT(*) FROM brand_menu_official o
                        WHERE o.brand_id=b.id AND o.price>0) > 0) has
            FROM brands b JOIN categories c ON c.id=b.category_id
            WHERE b.published=1 GROUP BY c.id ORDER BY n DESC"""):
            print("  %-14s %2d곳  (판매가 확보 %d곳 · 남은 %d곳)"
                  % (r["cn"], r["n"], r["has"] or 0, r["n"] - (r["has"] or 0)))
        return

    q = """
        SELECT b.name, b.slug, b.homepage_url u, c.name cn
        FROM brands b LEFT JOIN categories c ON c.id=b.category_id
        WHERE b.published=1 AND COALESCE(b.homepage_url,'') <> ''
          AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) %s""" % cond
    if need_only:
        q += """ AND (SELECT COUNT(*) FROM brand_menu_official o
                       WHERE o.brand_id=b.id AND o.price>0) = 0"""
    q += " ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?"
    rows = [dict(r) for r in c.execute(q, (top,))]
    if only:
        rows = [r for r in rows if only in r["name"]]
    if cat:
        rows = [r for r in rows if cat in (r.get("cn") or "")]
    print("브랜드 %d곳 · 메뉴 목록 페이지에서 이름·가격·중량 읽기" % len(rows), flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    tot = sum(len(r["menus"]) for r in res)
    zero = [r["brand"] for r in res if not r["menus"]]
    print("", flush=True)
    print("끝. 메뉴 %d개 · 0개인 브랜드 %d곳 → data/brand_menu_list/" % (tot, len(zero)), flush=True)
    if zero:
        print("   0개: %s" % ", ".join(zero), flush=True)


if __name__ == "__main__":
    main()
