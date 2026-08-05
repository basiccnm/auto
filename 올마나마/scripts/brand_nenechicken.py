# -*- coding: utf-8 -*-
"""네네치킨 메뉴판 — 공식 홈페이지에서 카테고리·메뉴를 긁어 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_nenechicken.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/nenechicken.json` 뿐이다.
   `brand_menu_store` 를 import 하지 않는다(수집 세션이 DB 에 쓰면 `database is locked`).

사이트 실측 (2026-07-28)
------------------------
서버 렌더 ASP. 헤드리스 불필요, `urllib` 로 읽힌다. SSL 검증은 끈다.

🔴 `home_menu.asp` 의 `<div class="MList">` 는 **비어 있다.** 메뉴는 AJAX 로 들어온다.
   호출 주소는 그 페이지가 부르는 `/js/Form_Module.js` 안의 `Menu_Load()` 에 적혀 있다 —
   `POST /process/home_menu_list.fuse` · `SUBID=<카테고리>&GUBUN=MENU&CUST_CODE=`
   (추측한 주소가 아니라 **사이트가 실제로 쓰는 주소**다)

🔴 카테고리 = `MENUCATEGORY('N')` 의 N. 목록 페이지의 **첫 번째 `CategoryWrap`** 만 화면에 보인다.
   두 번째(`CategoryWrap Cgwrap`)는 `display:none` 인 사본이고 「펩시세트」·피자 하위탭이 빠져 있다.
   하위탭은 `SUBCBOX<상위>` 안의 `SUBCATEGORY_MOVE('M')`.
   ⚠️ 하위 ext_id 가 상위와 겹친다(치킨=2, 그 아래 시그니처도 2). 상위 먼저 보고 판정한다.

🔴 상위 한 번 호출로 **하위가 전부** 온다 — `<div class="MenuInner" id="SUBDIV_2">` 가 여럿.
   그래서 하위탭마다 다시 부르지 않는다(같은 상품을 두 번 세게 된다).

🔴 가격은 목록 응답 안에 있다(`<span class="Price">`). 상세를 열 필요가 없다.
   상세 안내문 그대로 — *"**권장 소비자 가격**으로 가맹점 상황에 따라 가격이 상이할 수 있습니다"*
   → 배달앱 가격이 아니라 **본사 권장가(홀 기준)** 다.
   ⚠️ 상세의 `부위 선택`(순살 +2,000 · 닭다리/윙봉/콤보 +3,000)·`핫스파이스 +1,000` 은 **옵션**이다.
      목록 가격은 옵션 없는 기본가라 그대로 쓴다.

🔴 원산지·알레르기·중량은 **메뉴마다 다른 게 아니다.** 상세의 「원산지」 버튼이 부르는
   `POST /process/origin_detail.asp` 는 **인자가 없는 브랜드 공통 한 장**이다(메뉴 파라미터 없음).
   그 안이 3탭 × 3브랜드(네네치킨·네네피자·봉구스밥버거) 표다.
   → 표 전체는 `origin_note` · `weight_note` 에 **원문 그대로** 담고,
     메뉴별 `origin_raw`·`allergy_raw` 는 **이름이 정확히 맞을 때만** 채운다.
   ⚠️ 봉구스밥버거 표는 **쓰지 않는다.** 거기에도 `양념치킨` 이 있어서 네네 메뉴에 잘못 붙는다.
   ⚠️ 「치킨메뉴 일체 / 닭고기 / 국내산」 은 사이트가 스스로 범위를 적어둔 줄이다 →
      **치킨 카테고리 메뉴에만** 적용한다(추측이 아니라 표에 적힌 범위).

이름은 **다듬지 않는다.** `(3개)`·`1.25L`·`MAXX` 를 지우면 검증이 안 된다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "nenechicken.json")

BRAND = "네네치킨"
SLUG = "nenechicken"
ROOT = "https://nenechicken.com"
SOURCE = ROOT + "/home_menu.asp"
LIST_API = ROOT + "/process/home_menu_list.fuse"        # Form_Module.js 의 Menu_Load()
ORIGIN_API = ROOT + "/process/origin_detail.asp"        # 상세의 ORIGINPOP()
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
POST_HDR = dict(UA, **{"Content-Type": "application/x-www-form-urlencoded",
                       "Referer": SOURCE, "X-Requested-With": "XMLHttpRequest"})
GAP = 1.5

CHICKEN_CAT = "치킨"          # 「치킨메뉴 일체」 원산지 줄이 걸리는 상위 카테고리

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_TAB = re.compile(r"(?s)MENUCATEGORY\('(\d+)'\).*?<span class=\"Title\">(.*?)</span>")
RX_SUBBOX = re.compile(r"(?s)id=\"SUBCBOX(\d+)\"(.*?)</div>")
RX_SUB = re.compile(r"subcategory(\d+)\"[^>]*>([^<]*)<")
RX_SUBDIV = re.compile(r"(?s)<div class=\"MenuInner\"[^>]*id=\"SUBDIV_(\d+)\"")
RX_MTITLE = re.compile(r"(?s)<div class=\"MTitle\">(.*?)</div>")
RX_DETAIL = re.compile(r"home_menu_detail\.asp\?no=(\d+)&subid=(\d+)&GUBUN=MENU")
RX_MTITLE_BOX = re.compile(r"(?s)<div class=\"MenuTitle[^\"]*\">(.*?)</div>\s*<div class=\"Menuprice\"")
RX_MOICON = re.compile(r"(?s)<div class=\"moiconWrap[^\"]*\">.*?</div>")
RX_PRICE = re.compile(r"<span class=\"Price\">\s*([\d,]+)\s*</span>")
RX_OPRICE = re.compile(r"<span class=\"OPrice\">\s*([\d,]+)\s*</span>")
RX_IMG = re.compile(r"<img src=\"(/images/goods/[^\"]+)\"")
RX_SUBCON = re.compile(r"(?s)<div id=\"([A-Z0-9]+)\" class=\"Subcon\"[^>]*>(.*?)</table>")
RX_TR = re.compile(r"(?s)<tr>(.*?)</tr>")
RX_TD = re.compile(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>")
RX_WEIGHT_NOTE = re.compile(r"(전 메뉴 조리전 중량[^<]*)")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def _decode(raw):
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return RX_COMMENT.sub("", _decode(urllib.request.urlopen(req, timeout=30, context=CTX).read()))


def post(url, data):
    req = urllib.request.Request(url, data=data.encode(), headers=POST_HDR)
    return RX_COMMENT.sub("", _decode(urllib.request.urlopen(req, timeout=30, context=CTX).read()))


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    return re.sub(r"\s+", "", s or "")


def blank(v):
    """사이트가 «없음» 을 `-` 로 적는다. 값이 아니라 빈칸이다."""
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—") else v


# ─────────────────────────────── 카테고리 ───────────────────────────────
def read_cats(html):
    """(상위 [(ext_id,이름)], 하위 {상위ext: [(ext_id,이름)]}) — **첫 CategoryWrap** 만 본다.

    두 번째 `CategoryWrap Cgwrap` 은 `display:none` 사본이라 화면 순서가 아니다.
    """
    i = html.find('class="CategoryWrap"')
    j = html.find('class="MoCategoryWrap"')
    if i < 0 or j < 0:
        return [], {}
    blk = html[i:j]
    tops = [(c, strip(n)) for c, n in RX_TAB.findall(blk)]
    tops = [(c, n) for c, n in tops if c and n]
    subs = {}
    for parent, body in RX_SUBBOX.findall(blk):
        seen, got = set(), []
        for code, nm in RX_SUB.findall(body):
            nm = strip(nm)
            if code and nm and code not in seen:
                seen.add(code)
                got.append((code, nm))
        if got:
            subs[parent] = got
    return tops, subs


# ─────────────────────────────── 메뉴 목록 ───────────────────────────────
def parse_boxes(chunk):
    """`MenuBox` 블록 → [{ext_id,name,price,...}] · 버린 줄"""
    rows, dropped = [], []
    parts = re.split(r"(?s)<div class=\"MenuBox\b", chunk)[1:]
    for p in parts:
        d = RX_DETAIL.search(p)
        if not d:
            dropped.append(("(상세링크 없음)", "home_menu_detail 링크가 없다"))
            continue
        t = RX_MTITLE_BOX.search(p)
        name = strip(RX_MOICON.sub("", t.group(1))) if t else ""
        if not name:
            dropped.append(("(이름 없음) no=%s" % d.group(1), "MenuTitle 이 비었다"))
            continue
        pr = RX_PRICE.search(p)
        op = RX_OPRICE.search(p)
        img = RX_IMG.search(p)
        rows.append({
            "ext_id": d.group(1),
            "subid": d.group(2),
            "name": name,
            "price": int(pr.group(1).replace(",", "")) if pr else None,
            "oprice": int(op.group(1).replace(",", "")) if op else None,
            "detail_url": "%s/home_menu_detail.asp?no=%s&subid=%s&GUBUN=MENU"
                          % (ROOT, d.group(1), d.group(2)),
            "image_url": ROOT + img.group(1).split("?")[0] if img else None,
        })
    return rows, dropped


def split_sections(html):
    """[(SUBDIV_id 또는 None, 그 구역 HTML)] — 상위 한 번에 하위가 전부 온다."""
    hits = list(RX_SUBDIV.finditer(html))
    if not hits:
        return [(None, html)]
    out = []
    for n, m in enumerate(hits):
        end = hits[n + 1].start() if n + 1 < len(hits) else len(html)
        out.append((m.group(1), html[m.start():end]))
    return out


# ─────────────────── 원산지 · 알레르기 · 중량 (브랜드 공통 한 장) ───────────────────
def table_rows(html, key):
    m = re.search(r"(?s)<div id=\"%s\" class=\"Subcon\"[^>]*>(.*?)</table>" % key, html)
    if not m:
        return []
    return [[strip(c) for c in RX_TD.findall(tr)] for tr in RX_TR.findall(m.group(1))]


def origin_map(rows, ncol):
    """제품명 → «재료(원료): 원산지» — rowspan 으로 셀이 줄어든 줄은 앞 제품에 이어붙인다.

    ⚠️ 줄어드는 칸이 **한 개가 아니다.** 네네피자 표는 제품명·재료가 같이 rowspan 이라
       `미트소스스파게티|볼레네제소스|쇠고기|뉴질랜드산` 다음 줄이 `돼지고기|국내산`(2칸)으로 온다.
       `ncol-1` 만 이어붙이면 그 줄을 통째로 잃는다.
    """
    out, cur = {}, None
    for r in rows:
        if not r or r[0] in ("제품명",):
            continue
        if len(r) == ncol:
            cur, body = r[0], r[1:]
        elif cur and 2 <= len(r) < ncol:
            body = r
        else:
            continue
        head = body[0] if len(body) == 2 else "%s(%s)" % (body[0], " ".join(body[1:-1]))
        txt = "%s: %s" % (head, body[-1])
        got = out.setdefault(cur, [])
        if txt not in got:
            got.append(txt)
    return {k: " / ".join(v) for k, v in out.items()}


def allergy_map(rows):
    """제품명 → 성분. `구분` 칸(rowspan)이 있어 셀이 3개/2개로 섞인다.

    `후라이드,닭다리,닭날개,윙봉` 처럼 한 줄에 여러 제품이 적힌 곳은 쉼표로 쪼갠다.
    괄호가 든 이름(`소이크런치(윙봉,콤보)`)은 쪼개지 않는다 — 괄호 안 쉼표는 구분자가 아니다.
    """
    out = {}
    for r in rows:
        if len(r) < 2 or r[0] in ("구분", "제품명", "메뉴명"):
            continue
        name, ing = r[-2], r[-1]
        if not name or not ing:
            continue
        names = [name] if "(" in name else [x.strip() for x in name.split(",")]
        for nm in [name] + names:
            if nm:
                out.setdefault(norm(nm), ing.rstrip(","))
    return out


# ─────────────────────────────── 본체 ───────────────────────────────
def main():
    home = get(SOURCE)
    tops, subs = read_cats(home)
    if not tops:
        print("🔴 카테고리 0개 — **화면 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return
    print("  카테고리 %d개: %s" % (len(tops), " · ".join(n for _, n in tops)))
    for p, kids in subs.items():
        print("    › SUBCBOX%s: %s" % (p, " · ".join(n for _, n in kids)))

    cats = []
    for code, name in tops:
        cats.append({"name": name, "parent": None, "ext_id": code})
        for scode, sname in subs.get(code, []):
            cats.append({"name": sname, "parent": name, "ext_id": scode})

    # ① 카테고리별 메뉴
    placements, order, dropped_all, oprice_diff = {}, [], [], []

    def take(path, rows):
        for i, r in enumerate(rows):
            it = placements.get(r["ext_id"])
            if it is None:
                it = {"name": r["name"], "ext_id": r["ext_id"], "price": r["price"],
                      "price_source": "official" if r["price"] is not None else None,
                      "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                      "detail_url": r["detail_url"], "image_url": r["image_url"],
                      "cats": []}
                placements[r["ext_id"]] = it
                order.append(r["ext_id"])
            if r["oprice"] is not None and r["price"] is not None and r["oprice"] != r["price"]:
                oprice_diff.append((r["name"], r["oprice"], r["price"]))
            it["cats"].append([path, i])

    for code, name in tops:
        html = post(LIST_API, "SUBID=%s&GUBUN=MENU&CUST_CODE=" % code)
        kids = dict(subs.get(code, []))
        for sid, chunk in split_sections(html):
            path = name if (sid is None or sid not in kids) else "%s/%s" % (name, kids[sid])
            rows, drop = parse_boxes(chunk)
            dropped_all += [(path, nm, why) for nm, why in drop]
            take(path, rows)
            head = strip(RX_MTITLE.search(chunk).group(1)) if RX_MTITLE.search(chunk) else ""
            print("  %-18s %3d개%s%s" % (path, len(rows),
                                         "  (표제 %s)" % head if head and head != path.split("/")[-1] else "",
                                         "  ⛔버림 %d" % len(drop) if drop else ""), flush=True)
        time.sleep(GAP)

    if not order:
        print("🔴 메뉴 0건 — **화면 구조가 바뀌었다.** 조용히 빈 JSON 을 쓰지 않는다")
        return

    # ② 원산지·알레르기·중량 — 브랜드 공통 한 장
    org = post(ORIGIN_API, "")
    o_nene = origin_map(table_rows(org, "NENE"), 3)          # 네네치킨
    o_pizza = origin_map(table_rows(org, "PIZAA"), 4)        # 네네피자
    a_nene = allergy_map(table_rows(org, "NENE2"))
    a_pizza = allergy_map(table_rows(org, "PIZAA2"))
    # ⚠️ BONG/BONG2(봉구스밥버거)는 쓰지 않는다 — 거기 `양념치킨` 이 네네 메뉴에 잘못 붙는다
    wm = RX_WEIGHT_NOTE.search(org)
    weight_note = strip(wm.group(1)) if wm else None

    o_all = dict(o_pizza)
    o_all.update(o_nene)
    o_by_norm = {norm(k): v for k, v in o_all.items()}
    a_by_norm = dict(a_pizza)
    a_by_norm.update(a_nene)

    origin_note_rows = []
    for label, key, ncol in (("네네치킨", "NENE", 3), ("네네피자", "PIZAA", 4)):
        for r in table_rows(org, key):
            if r:
                origin_note_rows.append("[%s] %s" % (label, " | ".join(r)))
    origin_note = "\n".join(origin_note_rows) or None

    def variant_origin(name):
        """표가 `불고기피자(씬피자R/L)` 처럼 **도우·사이즈까지 붙여** 적어 이름이 안 맞을 때.

        `<메뉴명>(…)` 로 시작하는 줄만 모은다. 접두어 아무거나가 아니라
        **메뉴명 + 여는 괄호** 라서 다른 메뉴를 끌어오지 않는다(불고기피자 ↛ 불고기피자스페셜).
        """
        key = norm(name) + "("
        got = []
        for k, v in o_by_norm.items():
            if k.startswith(key):
                for part in v.split(" / "):
                    if part not in got:
                        got.append(part)
        return " / ".join(got) or None

    chicken_blanket = o_by_norm.get(norm("치킨메뉴 일체"))
    n_exact, n_blanket, n_variant, n_set = 0, 0, 0, 0
    for k in order:
        it = placements[k]
        nm = norm(it["name"])
        hit = o_by_norm.get(nm)
        var = None if hit else variant_origin(it["name"])
        if hit:
            it["origin_raw"] = blank(hit)
            n_exact += 1
        elif var:
            it["origin_raw"] = blank(var)
            n_variant += 1
        elif chicken_blanket and any(c[0] == CHICKEN_CAT or c[0].startswith(CHICKEN_CAT + "/")
                                     for c in it["cats"]):
            it["origin_raw"] = blank(chicken_blanket)     # 표에 적힌 범위(「치킨메뉴 일체」)
            n_blanket += 1
        it["allergy_raw"] = blank(a_by_norm.get(nm))

    # 세트(`치즈스노윙+펩시콜라1.25L`)는 **앞부분이 그대로 다른 메뉴 이름**이다 → 그 메뉴 것을 물려받는다.
    # 이름 비슷한 걸 갖다 붙이는 게 아니라 «완전 일치하는 메뉴가 이 목록에 있을 때만» 이다.
    by_name = {norm(placements[x]["name"]): placements[x] for x in order}
    for k in order:
        it = placements[k]
        if it["origin_raw"] or "+" not in it["name"]:
            continue
        base = by_name.get(norm(it["name"].split("+")[0]))
        if base and base["origin_raw"]:
            it["origin_raw"] = base["origin_raw"]
            it["allergy_raw"] = it["allergy_raw"] or base["allergy_raw"]
            n_set += 1

    # ③ 저장 — 길이 규칙에 걸린 줄은 **지우기 전에 목록으로 출력**한다
    suspicious = []
    cat_names = {c["name"] for c in cats}
    kept = []
    for k in order:
        it = placements[k]
        nm = it["name"]
        why = None
        if nm in cat_names:
            why = "카테고리 이름과 같다"
        elif re.search(r"[.!?~]$", nm):
            why = "문장부호로 끝난다"
        elif len(nm) >= 18:
            why = "18자 이상"
        if why:
            suspicious.append((nm, why))
        kept.append(it)

    menus = [{"name": it["name"], "price": it["price"], "price_source": it["price_source"],
              "weight_raw": it["weight_raw"], "origin_raw": it["origin_raw"],
              "allergy_raw": it["allergy_raw"], "detail_url": it["detail_url"],
              "image_url": it["image_url"], "ext_id": it["ext_id"], "cats": it["cats"]}
             for it in kept]

    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "origin_note": origin_note, "weight_note": weight_note,
           "cats": cats, "menus": menus}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # ④ 요약 — **만든 파일을 다시 읽어서** 센다
    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    n_o = sum(1 for m in chk["menus"] if m.get("origin_raw"))
    n_a = sum(1 for m in chk["menus"] if m.get("allergy_raw"))
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  원산지 %d = 이름일치 %d · 도우변형(`메뉴명(…)`) %d · 「치킨메뉴 일체」 %d · 세트물림 %d"
          % (n_o, n_exact, n_variant, n_blanket, n_set))
    print("  알레르기 %d · 중량 0 (메뉴별 표기가 없다 — `weight_note` 에 공통 문구만)" % n_a)
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  💰 가격 = 공식 «권장 소비자 가격» (배달앱 아님). 옵션(순살/부위/핫스파이스)은 뺀 기본가")
    if oprice_diff:
        print("  ⚠️ 정가≠판매가 %d건:" % len(oprice_diff))
        for nm, o, p in oprice_diff[:10]:
            print("     · %-24s %s → %s" % (nm[:24], o, p))
    if suspicious:
        print("  ⚠️ 길이·형태 규칙에 걸린 이름 %d개 — **지우지 않고 남겼다.** 눈으로 볼 것:" % len(suspicious))
        for nm, why in suspicious:
            print("     · %-40s %s" % (nm[:40], why))
    if dropped_all:
        print("  ⛔ 버린 줄 %d개:" % len(dropped_all))
        for where, nm, why in dropped_all[:20]:
            print("     · [%s] %s — %s" % (where, nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
