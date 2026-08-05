# -*- coding: utf-8 -*-
"""교촌치킨 메뉴판 — 공식 홈페이지에서 카테고리·메뉴·상세를 긁어 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_kyochon.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/kyochon.json` 뿐이다.
   적재는 `brand_menu_import.py` 가 따로 한다(수집 세션이 DB 에 쓰면 `database is locked` 가 난다).

   (2026-07-28 이 파일의 옛 판은 `brand_menu_store` 로 **DB 에 직접 적재**했고
    하위 카테고리·상세정보가 없었다. JSON 전용으로 갈아엎었다.)

사이트 실측 (2026-07-28)
------------------------
서버 렌더 ASP. 헤드리스 불필요, `urllib` 로 그냥 읽힌다. SSL 검증은 끈다.

🔴 하위탭에 `<span>` 이 **없다.** href 도 `/menu/` 로 시작한다 —
   `<a href="/menu/chicken.asp?code=21">신메뉴</a>`
   `href="chicken.asp?code=N"` 로 찾으면 **0건**이다.
🔴 `<!-- -->` 주석 안에 화면에 없는 탭이 숨어 있다(블랙시리즈·점보윙 등).
   **주석부터 걷어낸다.** 걷어내면 탭은 10개(+`전체메뉴`).
🔴 `<li class="depth3">` 블록이 4개 있는데 **첫 번째에만** 탭이 들어 있다.
🔴 `code=` 가 빈 「전체메뉴」는 카테고리가 아니다 — cats 에 넣지 않는다.
   대신 그 쪽(`chicken.asp`)의 진열 순서가 「치킨」 카테고리의 순서다.
⚠️ `code=8|3`(반반시리즈)처럼 `|` 가 들어간다. 인코딩하지 말고 그대로 쓴다.
⚠️ 버거(`burger.asp`)는 `menuProduct` 가 비어 있다(0개). 카테고리는 넣는다.
⚠️ 문베어·은하수는 가격이 없다 → `price: null` 로 **메뉴는 살린다.**
⚠️ 쪽 안에 **숨은 «지난 주문내역» 견본**이 있어 `15,000원` 이 박혀 있다.
   그래서 가격은 반드시 `ul.menuProduct` **안에서만** 읽는다.

🔴 알레르기 — 상세페이지의 표는 **그 메뉴 것이 아니다.**
   사이트 전체 66행 목록이 모든 상세페이지에 똑같이 박혀 있고, 표의 제품명 체계가
   메뉴판과 다르다(표 `교촌오리지날` ↔ 메뉴 `간장한마리`).
   → **이름이 정확히 일치할 때만** 채운다. 나머지는 null.
      「교촌」 접두어를 떼면 10건으로 늘지만 **하지 않는다** — 근거 없는 매핑이다.
      빈칸이 가짜보다 낫다.

이름은 **다듬지 않는다.** `20PCS`·`[S]`·`(3ea)`·`(500ml CAN)` 를 지우면 검증이 안 된다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "kyochon.json")

BRAND = "교촌치킨"
SLUG = "kyochon"
ROOT = "https://www.kyochon.com/menu/"
SOURCE = ROOT + "chicken.asp"
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
GAP_LIST = 1.0
GAP_VIEW = 1.5

# 상단 네비 순서 그대로 — (이름, asp 파일)
TOPS = [("신메뉴", "newmenu.asp"), ("치킨", "chicken.asp"), ("버거", "burger.asp"),
        ("사이드", "side.asp"), ("문베어 수제맥주", "liquor.asp"), ("은하수 막걸리", "drink.asp")]
CHICKEN = "치킨"

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_DEPTH3 = re.compile(r'(?s)<li class="depth3">(.*?)</li>')
RX_TAB = re.compile(r'(?s)<a[^>]+href="(?:/menu/)?chicken\.asp\?code=([^"]*)"[^>]*>(.*?)</a>')
RX_UL = re.compile(r'(?s)<ul[^>]*class="[^"]*menuProduct[^"]*"[^>]*>(.*?)</ul>')
RX_LI = re.compile(r"(?s)<li[^>]*>(.*?)</li>")
RX_VIEW = re.compile(r'href="((?:/menu/)?view\.asp\?id=(\d+)[^"]*)"')
RX_DT = re.compile(r"(?s)<dt>(.*?)</dt>")
RX_MONEY = re.compile(r'(?s)class="money".*?<strong>\s*([\d,]+)')
RX_IMG = re.compile(r'(?s)<p class="img">.*?<img[^>]+src="([^"]+)"')
RX_ORIGIN = re.compile(r'(?s)<p class="origin">(.*?)</p>')
RX_WEIGHT = re.compile(r"(?s)중량\s*:\s*(.*?)<br")
RX_ALLERGY = re.compile(r"(?s)주요 알레르기 성분</th>.*?<tbody>(.*?)</tbody>")
RX_TR = re.compile(r"(?s)<tr>(.*?)</tr>")
RX_TD = re.compile(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30, context=CTX).read()
    for enc in ("utf-8", "cp949"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = raw.decode("utf-8", "replace")
    return RX_COMMENT.sub("", html)          # 🔴 주석부터 걷어낸다


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    return re.sub(r"\s+", "", s or "")


# ─────────────────────────────── 목록 ───────────────────────────────
def sub_cats(html):
    """치킨 하위탭 [(code, 이름)] — 첫 depth3 블록에서만. `전체메뉴`(code 없음)는 뺀다."""
    for block in RX_DEPTH3.findall(html):
        tabs = [(code, strip(txt)) for code, txt in RX_TAB.findall(block)]
        tabs = [(c, n) for c, n in tabs if c and n]
        if tabs:
            return tabs
    return []


def parse_list(html):
    """메뉴 행 + 버린 줄. `view.asp?id=` 가 있는 `<li>` 만 메뉴로 친다(← `총 주문금액` 방어)."""
    rows, dropped = [], []
    for ul in RX_UL.findall(html):
        for li in RX_LI.findall(ul):
            dt = RX_DT.search(li)
            nm = strip(dt.group(1)) if dt else ""
            v = RX_VIEW.search(li)
            if not v:
                dropped.append((nm or "(이름 없음)", "view.asp 링크가 없다"))
                continue
            if not nm:
                dropped.append(("(dt 없음) id=%s" % v.group(2), "메뉴명이 없다"))
                continue
            money = RX_MONEY.search(li)
            img = RX_IMG.search(li)
            rows.append({
                "ext_id": v.group(2),
                "name": nm,
                "price": int(money.group(1).replace(",", "")) if money else None,
                "detail_url": urljoin(ROOT, v.group(1).replace("&amp;", "&")),
                "image_url": urljoin(ROOT, img.group(1)) if img else None,
            })
    return rows, dropped


# ─────────────────────────────── 상세 ───────────────────────────────
def parse_allergy_table(html):
    """사이트 공통 알레르기 표 → {정규화 제품명: 성분}. 모든 상세페이지에 같은 표가 박혀 있다."""
    m = RX_ALLERGY.search(html)
    if not m:
        return {}
    out = {}
    for tr in RX_TR.findall(m.group(1)):
        cells = [strip(c) for c in RX_TD.findall(tr)]
        if len(cells) < 2:                       # `※ 알레르기 유발물질을…` 안내행
            continue
        name, ing = cells[-2], cells[-1]         # rowspan 탓에 셀이 3개/2개로 섞인다
        if not name or name.startswith("※"):
            continue
        out[norm(name)] = ing
    return out


def blank(v):
    """사이트가 «없음» 을 `-` 로 적는다(중량 27건·원산지 1건). 값이 아니라 빈칸이다.

    `-` 를 그대로 두면 다음 단계에서 **중량이 있는 것처럼** 보인다. 빈칸이 가짜보다 낫다.
    """
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—") else v


def parse_detail(html):
    """(원산지, 중량) — 라벨은 떼고 값만. 값 자체는 원문 그대로."""
    o = RX_ORIGIN.search(html)
    origin = blank(re.sub(r"^원산지\s*:\s*", "", strip(o.group(1)))) if o else None
    w = RX_WEIGHT.search(html)
    weight = blank(strip(w.group(1))) if w else None
    return origin, weight


# ─────────────────────────────── 본체 ───────────────────────────────
def main():
    cats, placements, order, dropped_all = [], {}, [], []

    def take(cat_path, rows):
        for i, r in enumerate(rows):
            it = placements.get(r["ext_id"])
            if it is None:
                it = dict(r)
                it["price_source"] = "official" if r["price"] is not None else None
                it["weight_raw"] = it["origin_raw"] = it["allergy_raw"] = None
                it["cats"] = []
                placements[r["ext_id"]] = it
                order.append(r["ext_id"])
            it["cats"].append([cat_path, i])

    # ① 상위 6개 — 네비 순서 그대로
    pages = {}
    for name, asp in TOPS:
        html = get(ROOT + asp)
        pages[asp] = html
        rows, drop = parse_list(html)
        dropped_all += [(name, nm, why) for nm, why in drop]
        cats.append({"name": name, "parent": None, "ext_id": asp.replace(".asp", "")})
        take(name, rows)
        print("  %-14s %3d개%s" % (name, len(rows),
                                   "  ⛔버림 %d" % len(drop) if drop else ""), flush=True)
        time.sleep(GAP_LIST)

    # ② 치킨 하위탭
    subs = sub_cats(pages["chicken.asp"])
    if not subs:
        print("🔴 치킨 하위탭 0개 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    for code, name in subs:
        cats.append({"name": name, "parent": CHICKEN, "ext_id": code})
    print("\n  치킨 하위탭 %d개: %s" % (len(subs), " · ".join(n for _, n in subs)))

    for code, name in subs:
        path = "%s/%s" % (CHICKEN, name)
        rows, drop = parse_list(get(ROOT + "chicken.asp?code=" + code))   # `8|3` 그대로
        dropped_all += [(path, nm, why) for nm, why in drop]
        take(path, rows)
        print("    › %-12s %3d개%s" % (name, len(rows),
                                       "  ⛔버림 %d" % len(drop) if drop else ""), flush=True)
        time.sleep(GAP_LIST)

    if not order:
        print("🔴 메뉴 0건 — **화면 구조가 바뀌었다.** 조용히 빈 JSON 을 쓰지 않는다")
        return

    # ③ 상세 — 같은 id 는 한 번만
    print("\n  상세 %d건 (간격 %.1f초)" % (len(order), GAP_VIEW), flush=True)
    allergy, failed = None, []
    for n, key in enumerate(order, 1):
        it = placements[key]
        try:
            d = get(it["detail_url"])
        except Exception as e:
            failed.append((it["name"], str(e)[:50]))
            time.sleep(GAP_VIEW)
            continue
        if allergy is None:
            allergy = parse_allergy_table(d)
            print("    (사이트 공통 알레르기 표 %d행 — 메뉴별로 갈리지 않는다)" % len(allergy),
                  flush=True)
        it["origin_raw"], it["weight_raw"] = parse_detail(d)
        it["allergy_raw"] = allergy.get(norm(it["name"]))      # 정확히 일치할 때만
        if n % 20 == 0:
            print("    … %d/%d" % (n, len(order)), flush=True)
        time.sleep(GAP_VIEW)

    # ④ 저장
    menus = [{"name": placements[k]["name"], "ext_id": placements[k]["ext_id"],
              "price": placements[k]["price"], "price_source": placements[k]["price_source"],
              "weight_raw": placements[k]["weight_raw"],
              "origin_raw": placements[k]["origin_raw"],
              "allergy_raw": placements[k]["allergy_raw"],
              "detail_url": placements[k]["detail_url"],
              "image_url": placements[k]["image_url"],
              "cats": placements[k]["cats"]} for k in order]
    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "cats": cats, "menus": menus}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # ⑤ 요약 — **만든 파일을 다시 읽어서** 센다
    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    n_w = sum(1 for m in chk["menus"] if m.get("weight_raw"))
    n_o = sum(1 for m in chk["menus"] if m.get("origin_raw"))
    n_a = sum(1 for m in chk["menus"] if m.get("allergy_raw"))
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  중량 %d · 원산지 %d · 알레르기 %d · 카테고리 배치 %d자리" % (n_w, n_o, n_a, links))
    print("  ⚠️ 알레르기는 사이트 공통표라 메뉴별로 못 가른다 — 이름이 정확히 맞는 것만 채웠다")
    if failed:
        print("  ⚠️ 상세 실패 %d건:" % len(failed))
        for nm, why in failed[:10]:
            print("     · %-30s %s" % (nm[:30], why))
    if dropped_all:
        print("  ⛔ 버린 줄 %d개:" % len(dropped_all))
        for where, nm, why in dropped_all[:10]:
            print("     · [%s] %s — %s" % (where, nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
