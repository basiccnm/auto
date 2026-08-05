# -*- coding: utf-8 -*-
"""피자스쿨(pizzaschool) 메뉴판 수집 — JSON 한 개만 만든다. 2026-07-28

    python scripts/brand_pizzaschool.py            # 캐시 있으면 캐시로
    python scripts/brand_pizzaschool.py --refresh  # 다시 받아온다

만드는 것: data/brand_menu_list/pizzaschool.json      (DB 는 건드리지 않는다)

────────────────────────────────────────────────────────────
어떻게 뚫었나
────────────────────────────────────────────────────────────
* 사이트는 **워드프레스(Enfold 테마)** 다. `WebFetch` 는 인증서가 self-signed 라 죽는다.
  → `urllib` + `ssl.CERT_NONE` + 브라우저 UA 로 그냥 열린다. **브라우저 도구는 필요 없었다.**
* 목록 `http://pizzaschool.net/menu/` 한 장에 **63개가 전부** 들어 있다(isotope 그리드).
  **페이징 없음** — `all_sort` 카운트(63)와 실제 타일 수(63)가 일치한다.
* 카테고리는 필터 버튼(`data-filter="<hex>_sort"`)이고, 각 타일의 class 에 같은 토큰이 박혀 있다.
  `<hex>` 는 카테고리 이름의 **UTF-8 바이트 hex** 다 → `unhexlify` 로 되돌린다.
  ⚠️ 타일에는 필터 바에 **없는** 토큰 `메인대표상품`(19건)도 섞여 있다.
     화면에 탭으로 안 보이므로 **카테고리로 쓰지 않는다**(원본이 보여주는 그대로 원칙).
* 상세는 목록에 적힌 링크만 따라간다(한글 URL 이 percent-encoding 된 형태).

────────────────────────────────────────────────────────────
상세 페이지 구조 (실측)
────────────────────────────────────────────────────────────
  <div class='av-special-heading …'><h1 …>치킨타코피자</h1>
      <div class='av-subheading…'><p>Chicken Taco Pizza l 설명…</p></div></div>
  <div class='av-special-heading …'><h3 …>오리지널 : 15,900원</h3>
      <div class='av-subheading…'><p>치즈크러스트 : 18,900원</p></div></div>
  <ul class='avia-icon-list'> … 설명 / 주요토핑 / 원산지 / 맵기정도 …
  <p class='toggler'>영양성분</p>        → 표 (총중량 = 오리지널 | 크러스트 추가)
  <p class='toggler'>알레르기 유발 물질</p> → 표 (재료별)

🔴 **가격 제목의 태그 레벨이 제각각이다.** `h1` 인 페이지도 있다(치즈토핑 `<h1>가격: 3,000원</h1>`).
   `h3` 만 찾으면 5건이 «가격 없음» 으로 샌다. → 태그 레벨을 안 보고 **문서 순서**로 첫 블록=이름,
   나머지 블록=가격으로 읽는다.

🔴 **한 메뉴에 가격이 둘이면 두 줄로 낸다.** 피자 27종이 `오리지널`/`치즈크러스트` 두 값을 나란히 준다.
   한쪽만 저장하면 피자 브랜드가 통째로 «공식에 없다» 로 오탐난다(2026-07-27 사고).
   이름은 **사이트 표기 그대로** 뒤에 붙인다 → `콤비네이션피자 오리지널` / `콤비네이션피자 치즈크러스트`.
   영양성분 표의 총중량도 열이 둘이라 **변형별로 따로** 잡아준다(734g / 814g).

🔴 `가격 :` `가격:` `가격(4조각):` 는 **UI 라벨**이지 변형이 아니다 → 이름에 붙이지 않는다.
   `치킨스틱&윙 : 6,900원` 처럼 라벨이 **메뉴 이름 자신**인 경우도 붙이지 않는다.
"""
import argparse
import binascii
import html as HTMLLIB
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "_cache", "pizzaschool")
OUT = os.path.join(ROOT, "data", "brand_menu_list", "pizzaschool.json")

BRAND = "피자스쿨"
SLUG = "pizzaschool"
LIST_URL = "http://pizzaschool.net/menu/"
COLLECTED_AT = "2026-07-28"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36")}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE           # 🔴 인증서가 self-signed 다

# 필터 바에 보이지 않는 숨은 토큰 — 카테고리로 쓰지 않는다
HIDDEN_CATS = {"메인대표상품"}
# 「전체메뉴」는 카테고리가 아니라 «전부 보기» 버튼이다
ALL_TOKEN = "all_sort"

# 가격 제목에서 라벨을 변형 이름으로 쓰지 않을 것들
LABEL_NOT_VARIANT = re.compile(r"^가격")


# ───────────────────────────── 가져오기 ─────────────────────────────
def fetch(url, key, refresh=False):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key + ".html")
    if not refresh and os.path.exists(p) and os.path.getsize(p) > 1000:
        return open(p, encoding="utf-8").read()
    req = urllib.request.Request(url, headers=UA)
    d = urllib.request.urlopen(req, context=CTX, timeout=40).read().decode("utf-8", "replace")
    open(p, "w", encoding="utf-8").write(d)
    time.sleep(1.0)
    return d


def strip_comments(h):
    """🔴 HTML 주석부터 걷어낸다 — 죽은 메뉴·숨은 탭이 섞여 있다."""
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|li|div)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = HTMLLIB.unescape(s).replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def won(s):
    m = re.search(r"([\d,]{3,})\s*원", s)
    return int(m.group(1).replace(",", "")) if m else None


# ───────────────────────────── 목록 ─────────────────────────────
CAT_BTN = re.compile(
    r'data-filter="([a-z0-9_]+)"[^>]*>.*?<span>([^<]*)</span>'
    r'<small class="av-cat-count">\s*(\d+)\s*</small>', re.S)
ENTRY = re.compile(r"<div data-ajax-id='(\d+)' class='([^']*)'>(.*?)</article></div>", re.S)
TITLE = re.compile(r"<h3 class='grid-entry-title entry-title '[^>]*><a href='([^']*)'[^>]*>(.*?)</a>", re.S)
IMG = re.compile(r'<a href="[^"]*"[^>]*class=\'grid-image avia-hover-fx\'>.*?data-src="([^"]+)"', re.S)


def tok_name(tok):
    """`ec8ba0eba994eb89b4_sort` → `신메뉴`"""
    try:
        return binascii.unhexlify(tok[:-5]).decode("utf-8")
    except Exception:
        return None


def parse_list(h):
    h = strip_comments(h)
    cats = []                                   # 화면 순서 그대로
    for tok, name, cnt in CAT_BTN.findall(h):
        if tok == ALL_TOKEN:
            continue
        cats.append({"token": tok, "name": txt(name), "count": int(cnt)})

    items = []
    for aid, cls, body in ENTRY.findall(h):
        t = TITLE.search(body)
        if not t:
            continue
        toks = [c for c in cls.split() if c.endswith("_sort") and c != ALL_TOKEN]
        im = IMG.search(body)
        items.append({
            "ext_id": aid,
            "url": HTMLLIB.unescape(t.group(1)),
            "name": txt(t.group(2)),
            "tokens": toks,
            "image_url": HTMLLIB.unescape(im.group(1)) if im else None,
            "list_price": won(body[body.find('<strong class="price">'):]) if '<strong class="price">' in body else None,
        })
    return cats, items


# ───────────────────────────── 상세 ─────────────────────────────
HEAD_BLK = re.compile(
    r"<div  class='av-special-heading [^']*'>"
    r"<h[1-6] class='av-special-heading-tag'[^>]*>(.*?)</h[1-6]>"
    r"(?:<div class='av-subheading[^']*'>(.*?)</div>)?", re.S)
ICON = re.compile(
    r"<h4 class='av_iconlist_title iconlist_title  '[^>]*>(.*?)</h4>\s*</header>"
    r"<div class='iconlist_content '[^>]*>(.*?)</div>", re.S)
TOGGLE = re.compile(
    r"class='toggler[^']*'[^>]*>(.*?)<span class=\"toggle_icon\".*?"
    r"<div class='toggle_content invers-color '[^>]*>(.*?)</div></div>", re.S)
TABLE = re.compile(r'<table class="tbl_type01".*?</table>', re.S)


def rows_of(tbl):
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", tbl, re.S):
        out.append([txt(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)])
    return out


def parse_detail(h):
    h = strip_comments(h)
    i = h.find("entry-content-wrapper")
    j = h.find("togglecontainer")
    body = h[i:j] if j > i > 0 else h[i:] if i > 0 else h

    blocks = [(txt(a), txt(b)) for a, b in HEAD_BLK.findall(body)]
    name = blocks[0][0] if blocks else None
    desc = blocks[0][1] if blocks else None

    # 가격 줄: 첫 블록 이후의 제목·부제목을 순서대로 편다
    price_lines = []
    for head, sub in blocks[1:]:
        for line in [head] + ([sub] if sub else []):
            for ln in line.split("\n"):
                ln = ln.strip()
                if ln:
                    price_lines.append(ln)

    icons = {}
    for t, c in ICON.findall(h):
        icons.setdefault(txt(t), txt(c))

    weight_cols, allergy, origin_tbl = None, None, None
    for t, c in TOGGLE.findall(h):
        t = txt(t)
        tb = TABLE.search(c)
        if not tb:
            # 🔴 표가 아니라 그냥 <p> 인 곳이 있다 (오지치즈그라탕 원산지).
            #    표만 찾으면 「고기가 들었는데 원산지 없음」으로 샌다.
            plain = txt(c)
            if plain and "원산지" in t and not origin_tbl:
                origin_tbl = plain
            elif plain and "알레르기" in t and not allergy:
                allergy = plain
            continue
        rr = rows_of(tb.group(0))
        if "영양" in t:
            hdr = rr[0] if rr else []
            wrow = next((r for r in rr if r and "총중량" in r[0]), None)
            if wrow:
                weight_cols = (hdr, wrow)
        elif "알레르기" in t:
            allergy = " | ".join("%s:%s" % (r[0], r[1]) for r in rr
                                 if len(r) >= 2 and r[0] and r[1])
        elif "원산지" in t:
            origin_tbl = " | ".join(":".join(x for x in r if x) for r in rr if any(r))

    return {"name": name, "desc": desc, "price_lines": price_lines,
            "topping": icons.get("주요토핑"),
            "origin": icons.get("원산지") or origin_tbl,
            "weight_cols": weight_cols, "allergy": allergy}


def weight_for(weight_cols, variant):
    """총중량 행에서 변형에 맞는 열을 고른다. 열 머리글: ['', '오리지널', '크러스트 추가']"""
    if not weight_cols:
        return None
    hdr, wrow = weight_cols
    vals = wrow[1:]
    if not vals:
        return None
    if variant and len(vals) > 1:
        heads = hdr[1:] if len(hdr) > 1 else []
        key = "크러스트" if "크러스트" in variant else variant
        for k, hv in enumerate(heads):
            if k < len(vals) and key and key in hv:
                return vals[k]
    return vals[0]


# ───────────────────────────── 조립 ─────────────────────────────
def build(refresh=False):
    lst = fetch(LIST_URL, "_list", refresh)
    cats, items = parse_list(lst)

    cat_names, dropped_cats = [], []
    for c in cats:
        nm = tok_name(c["token"]) or c["name"]
        if nm in HIDDEN_CATS:
            dropped_cats.append((nm, "필터 바에 안 보이는 숨은 토큰"))
            continue
        cat_names.append({"token": c["token"], "name": c["name"], "count": c["count"]})

    seen_tok = {c["token"] for c in cat_names}

    rows, dropped, notes = [], [], []
    pos = {c["name"]: 0 for c in cat_names}      # 카테고리별 다음 자리

    for it in items:
        d = parse_detail(fetch(it["url"], it["ext_id"], refresh))
        name = d["name"] or it["name"]

        # ── 메뉴가 아닌 것 걸러내기 (지우기 전에 목록으로 남긴다)
        bad = None
        if not name:
            bad = "이름 없음"
        elif name.endswith((".", "!", "?")):
            bad = "문장부호로 끝남"
        elif len(name) >= 18:
            bad = "18자 이상"
        elif name in {c["name"] for c in cat_names} or name == "전체메뉴":
            bad = "카테고리 이름과 같음"
        if bad:
            dropped.append((it["ext_id"], name, bad))
            continue

        # ── 가격 줄 → 변형 목록
        variants = []                            # (변형이름 or None, 가격, 비고)
        extra_note = []
        for ln in d["price_lines"]:
            p = won(ln)
            if p is None:
                extra_note.append(ln)            # 「칠리소스가 함께 제공됩니다.」 같은 안내
                continue
            label = ln.split(":")[0].strip() if ":" in ln else ""
            if (not label or LABEL_NOT_VARIANT.match(label)
                    or label.replace(" ", "") == name.replace(" ", "")):
                variants.append((None, p, ln if label and label != "가격" else None))
            else:
                variants.append((label, p, None))
        if not variants:
            # 🔴 소스·시즈닝 11종은 **상세 페이지에 가격 제목이 아예 없다.**
            #    목록 타일의 <strong class="price"> 에는 있다(핫소스 100원 · 오이피클 500원).
            #    상세만 보면 11건이 통째로 «가격 없음» 이 된다.
            variants = [(None, it["list_price"], None)]   # 가격이 없어도 메뉴는 넣는다

        if len(variants) > 1 and any(v[0] for v in variants):
            notes.append((name, [v[0] for v in variants]))

        for variant, price, raw in variants:
            note = []
            if raw:
                note.append(raw)
            note += extra_note
            rows.append({
                "name": ("%s %s" % (name, variant)) if variant else name,
                "price": price,
                "price_source": "official" if price is not None else None,
                "price_note": " / ".join(note) or None,
                "compose_raw": ("주요토핑: " + d["topping"]) if d["topping"] else None,
                "weight_raw": weight_for(d["weight_cols"], variant),
                "origin_raw": d["origin"] or None,
                "allergy_raw": d["allergy"] or None,
                "detail_url": it["url"],
                "image_url": it["image_url"],
                "ext_id": it["ext_id"],
                "_tokens": [t for t in it["tokens"] if t in seen_tok],
            })

    # ── 카테고리 자리 매기기 (화면 순서 그대로, 행 순서로 0부터)
    for r in rows:
        r["cats"] = []
        for tok in r.pop("_tokens"):
            nm = next(c["name"] for c in cat_names if c["token"] == tok)
            r["cats"].append([nm, pos[nm]])
            pos[nm] += 1

    doc = {
        "brand": BRAND, "slug": SLUG, "source": LIST_URL, "collected_at": COLLECTED_AT,
        "origin_note": None,
        "cats": [{"name": c["name"], "parent": None, "ext_id": c["token"]} for c in cat_names],
        "menus": rows,
    }
    return doc, dropped, dropped_cats, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    doc, dropped, dropped_cats, notes = build(a.refresh)

    if not doc["menus"]:
        print("❌ 메뉴 0건 — 저장하지 않는다")
        return 1

    if dropped_cats:
        print("― 버린 카테고리")
        for nm, why in dropped_cats:
            print("   ✂ %s — %s" % (nm, why))
    print("― 버린 줄 (%d)" % len(dropped))
    for eid, nm, why in dropped:
        print("   ✂ [%s] %s — %s" % (eid, nm, why))
    print("― 두 줄로 쪼갠 메뉴 (%d)" % len(notes))
    for nm, vs in notes[:5]:
        print("   ⇉ %s → %s" % (nm, " / ".join(vs)))
    if len(notes) > 5:
        print("   … 외 %d개" % (len(notes) - 5))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("\n✅ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
