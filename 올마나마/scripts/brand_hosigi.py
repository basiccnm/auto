# -*- coding: utf-8 -*-
"""호식이두마리치킨(slug 9292) 메뉴판 수집 — 카테고리·메뉴·순서·원산지. 2026-07-28

    python scripts/brand_hosigi.py
    → data/brand_menu_list/9292.json  (DB 는 건드리지 않는다)

사이트 실측 (2026-07-28)
------------------------
🔴 **DB 의 홈페이지 주소 `http://www.9292.co.kr/` 는 죽었다**(480바이트 빈 페이지).
   살아 있는 공식 사이트는 **`https://www.9922.co.kr`** (imweb). DB 주소는 여기서 고치지 않는다.

메뉴 탭(`.sub-menu li.depth-01 > a`) — 화면 순서 그대로:

    /menu                   전체 메뉴          32개
    /chicken                치킨 메뉴          14개
    /parts                  부위별 메뉴         6개
    /side                   사이드 메뉴        15개
    /allergenic-component   알레르기 성분정보   ← 메뉴 아님(표)
    /199                    조리 전 중량        ← 메뉴 아님(이미지 1장)

🔴 **imweb 이지만 SPA 가 아니다.** gallery2 위젯이 **서버에서 다 렌더돼 온다.**
   「더보기」 버튼은 AJAX 가 아니라 **이미 DOM 에 있는 항목을 보여주기만** 한다
   (브라우저로 끝까지 눌러 확인 — 32개에서 더 늘지 않았다).
   그래서 순수 HTTP 로 충분하고, 이 스크립트는 브라우저를 쓰지 않는다.

🔴 **메뉴 카드 블록 안에서만** 이름을 집는다(`div[id^=caption_] > h4`).
   페이지 전체 텍스트를 훑으면 `알림`·`뒤로`·`Alarm`·`나눔 활동` 같은 화면 글자 68개가 메뉴로 들어간다
   (이 브랜드에서 실제로 낸 사고다).
   ⚠️ 갤러리에는 **캡션이 없는 빈 `_item`** 이 섞여 있다(치킨 2 · 부위별 2 · 사이드 1). 이름이 없으면 버린다.

🔴 **가격은 사이트 어디에도 없다.** 4개 목록 + 상세 36장을 통째로 훑어 `숫자+원` 패턴 **0건**.
   그래서 전부 `price: null` 이다. 짐작해 넣지 않는다.

🔴 **원산지는 상세페이지에 있다** — `원산지 : 국내산` (본문 텍스트).
   그런데 **브랜드가 링크를 잘못 걸어둔 상세페이지가 5장** 있다
   (`/152`·`/157`·`/182`·`/184`·`/185` → 전부 「타코마요 치킨」 옛 페이지가 뜬다).
   그래서 상세페이지 제목이 목록 이름과 맞을 때만 원산지를 가져온다(`_same_item`).
   안 맞으면 `origin_raw = None` 으로 비운다.

⚠️ 「전체 메뉴」 탭은 나머지 세 탭의 합집합이지만 **철자가 다른 항목이 5개** 있고
   (`레몬크림탕슈(안심 순살)` / `날개+다리` / `똥집미니튀김` / `허니갈릭치즈볼(6개)` / `트리플 치즈볼(6개)`),
   쉬림프 2종·치킨무가 빠져 있다. **다듬지 않고 원문 그대로** 담는다(브랜드가 그렇게 걸어놨다).

⚠️ 조리 전 중량은 **이미지 1장**이라 판독해서 `WEIGHT_NOTE` 에 옮겼다.
   표가 이름을 직접 부르는 3개(플라윙·날개와 다리·다리만)만 `weight_raw` 에 넣는다.
"""
import io
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "호식이지두마리치킨"          # DB brands.name (slug 9292)
SLUG = "9292"
BASE = "https://www.9922.co.kr"
COLLECTED = "2026-07-28"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", SLUG + ".json")
# 내려받은 HTML 은 프로젝트가 아니라 OS 임시폴더에 둔다(하루 지나면 다시 받는다)
CACHE = os.path.join(tempfile.gettempdir(), "olmanama_hosigi")

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
GAP = 0.8
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 화면 순서 그대로. ext_id 는 imweb 메뉴코드(nav 의 data-code)
TABS = [
    ("전체 메뉴", "/menu", "m20200120cb9fda8df295b"),
    ("치킨 메뉴", "/chicken", "m20200120e3f6f99affd71"),
    ("부위별 메뉴", "/parts", "m202001209840d038a43c0"),
    ("사이드 메뉴", "/side", "m2020012039a65acfb4f71"),
]

ALLERGY_PATH = "/allergenic-component"

# /199 「조리 전 중량」 이미지 판독 (2026-07-28)
WEIGHT_IMG = "https://cdn.imweb.me/thumbnail/20251211/99970701c09fc.jpg"
WEIGHT_NOTE = (
    "조리 전 중량 (*전 메뉴 동일하게 적용) — "
    "두 마리 : 원료육 851g~950g(9호) x 2 / 한 마리 : 원료육 851g~950g(9호) x 1 "
    "(*원료육의 기름기 등 제거, 절단에 따라 중량의 차이가 있을 수 있습니다.) / "
    "순살 1개 : 500g / 순살 2개 : 1,000g / "
    "플라윙(윙+봉) : 1,000g [윙 500g + 봉 500g] / "
    "날개와 다리 : 1,000g [윙(날개) 500g + 북채(다리) 500g] / "
    "다리만 : 북채(다리) 1,000g"
    " [메뉴 이미지 판독: " + WEIGHT_IMG + "]"
)
# 표가 이름을 직접 부르는 것만 (정규화 이름 -> 원문 줄)
WEIGHT_BY_NAME = {
    "플라윙세트윙+봉": "플라윙(윙+봉) : 1,000g [윙 500g + 봉 500g]",
    "윙+다리": "날개와 다리 : 1,000g [윙(날개) 500g + 북채(다리) 500g]",
    "날개+다리": "날개와 다리 : 1,000g [윙(날개) 500g + 북채(다리) 500g]",
    "다리스틱": "다리만 : 북채(다리) 1,000g",
}

RX_ITEM_SPLIT = '<div class="_item item_gallary'
RX_CAP = re.compile(r'(?s)<div id="caption_(\d+)"[^>]*>\s*(.*?)\s*</div>')
RX_H4 = re.compile(r"(?s)<h4>(.*?)</h4>")
RX_SPAN = re.compile(r"(?s)<span[^>]*>(.*?)</span>")
RX_HREF = re.compile(r'class="item_container _item_container[^"]*"\s*href="([^"]*)"')
RX_IMG = re.compile(r'data-src="([^"]+)"')
RX_MAIN = re.compile(r"(?s)<main>(.*?)</main>")
RX_ORIGIN = re.compile(r"원산지\s*:\s*[^\n<]+")


def fetch(path):
    fn = os.path.join(CACHE, re.sub(r"[^0-9A-Za-z_.-]", "_", path.strip("/") or "root") + ".html")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < 86400:
        return io.open(fn, encoding="utf-8").read()
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(BASE + path, headers=HDRS)
    html = urllib.request.urlopen(req, timeout=45, context=CTX).read().decode("utf-8", "replace")
    io.open(fn, "w", encoding="utf-8").write(html)
    time.sleep(GAP)
    return html


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).replace("&nbsp;", " ").strip()


def norm(s):
    """비교용 이름 정규화 — 공백·괄호·하이픈·가운뎃점 제거"""
    return re.sub(r"[\s()\[\]\-–—·,.]", "", s or "")


def text_lines(html):
    body = re.sub(r"(?s)<script.*?</script>", " ", html)
    body = re.sub(r"(?s)<style.*?</style>", " ", body)
    mains = RX_MAIN.findall(body)
    txt = re.sub(r"<[^>]+>", "\n", mains[0] if mains else "").replace("&nbsp;", " ")
    return [x.strip() for x in txt.split("\n") if x.strip()]


# ── 메뉴 아닌 줄 걸러내기 ────────────────────────────────────────────────
def reject_reason(name, cat_names):
    if not name:
        return "이름 없음(빈 갤러리 칸)"
    if re.search(r"[.!?]$", name):
        return "문장부호로 끝남"
    if len(name) >= 18:
        return "18자 이상"
    if name in cat_names:
        return "카테고리 이름과 같음"
    return None


def parse_tab(html):
    """메뉴 카드 블록 안에서만 집는다"""
    out = []
    for blk in html.split(RX_ITEM_SPLIT)[1:]:
        blk = blk[:8000]
        cap = RX_CAP.search(blk)
        name = sub = desc = None
        if cap:
            h4 = RX_H4.search(cap.group(2))
            if h4:
                raw = h4.group(1)
                sp = RX_SPAN.search(raw)
                sub = strip_tags(sp.group(1)) if sp else None
                name = strip_tags(re.sub(r"(?s)<span[^>]*>.*?</span>", " ", raw))
            p = re.search(r"(?s)<p>(.*?)</p>", cap.group(2))
            desc = strip_tags(p.group(1)) if p else None
        href = RX_HREF.search(blk)
        img = RX_IMG.search(blk)
        out.append({"name": name, "sub": sub, "desc": desc,
                    "href": href.group(1) if href and href.group(1) else None,
                    "img": img.group(1) if img else None})
    return out


def _same_item(list_name, detail_title):
    """상세페이지가 이 메뉴의 것인지 — 3글자 이상 겹치면 인정"""
    a, b = norm(list_name), norm(detail_title)
    if not a or not b:
        return False
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    for i in range(len(a) - 2):
        if a[i:i + 3] in b:
            return True
    return False


def detail_info(path, list_name):
    """상세페이지 → (원산지원문, 제목, 맞는지)"""
    try:
        html = fetch(path)
    except Exception as e:
        print(f"    ⚠️ 상세 실패 {path}: {e}")
        return None, None, False
    lines = text_lines(html)
    title = lines[1] if len(lines) > 1 else None
    ok = _same_item(list_name, title or "")
    origin = None
    if ok:
        for ln in lines:
            m = RX_ORIGIN.search(ln)
            if m:
                origin = m.group(0).strip()
                break
    return origin, title, ok


def parse_allergy():
    """알레르기 성분정보 표(PC 위젯) → {정규화이름: 원문}"""
    html = fetch(ALLERGY_PATH)
    body = re.sub(r"(?s)<script.*?</script>", " ", html)
    mains = RX_MAIN.findall(body)
    best = {}
    for seg in mains:
        rows = re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", seg)
        for r in rows:
            cells = [strip_tags(c) for c in re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", r)]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            nm, al = cells[-2], cells[-1]
            if "알레르기" in al or "메뉴명" in nm:
                continue
            best.setdefault(norm(nm), al)
    return best


def allergy_of(name, table):
    """완전일치 → 앞자락일치 → 포함(단 하나일 때만). 여럿 걸리면 비운다"""
    n = norm(name)
    if n in table:
        return table[n]
    for pred in (lambda k: k.startswith(n) or n.startswith(k),
                 lambda k: k in n):                       # 안심텐더 ⊂ 호식이안심텐더
        hits = [v for k, v in table.items() if pred(k)]
        if len(hits) == 1:
            return hits[0]
    return None


def main():
    cat_names = [t[0] for t in TABS]
    cats = [{"name": n, "parent": None, "ext_id": e} for n, _, e in TABS]

    allergy = parse_allergy()
    print(f"알레르기 표 {len(allergy)}행")

    menus = {}            # 이름 -> dict
    order = []            # 이름 등장 순서
    dropped = []
    for cname, path, _ in TABS:
        html = fetch(path)
        items = parse_tab(html)
        kept = 0
        for idx, it in enumerate(items):
            why = reject_reason(it["name"], cat_names)
            if why:
                dropped.append((cname, idx, it["name"], why))
                continue
            nm = it["name"]
            if nm not in menus:
                menus[nm] = {"name": nm, "cands": [], "img": it["img"], "sub": it["sub"]}
                order.append(nm)
            if it["href"]:
                menus[nm]["cands"].append(it["href"])
            if not menus[nm]["img"] and it["img"]:
                menus[nm]["img"] = it["img"]
            menus[nm].setdefault("cats", []).append([cname, kept])
            kept += 1
        print(f"{cname:<8} {path:<8} 항목 {len(items):>2} → 메뉴 {kept}")

    # 상세페이지 → 원산지
    print("\n상세페이지 원산지 확인")
    for nm in order:
        m = menus[nm]
        m["origin"] = None
        m["detail"] = None
        for href in dict.fromkeys(m["cands"]):
            origin, title, ok = detail_info(href, nm)
            if ok:
                m["origin"] = origin
                m["detail"] = href
                break
            print(f"    ✗ {nm} → {href} 은(는) 「{title}」 페이지다 — 원산지 안 씀")
        if m["detail"] is None and m["cands"]:
            m["detail"] = m["cands"][0]

    out_menus = []
    for nm in order:
        m = menus[nm]
        ext = m["detail"].strip("/") if m["detail"] else None
        out_menus.append({
            "name": nm,
            "price": None,
            "price_source": "official",
            "price_note": None,
            "weight_raw": WEIGHT_BY_NAME.get(norm(nm)),
            "origin_raw": m["origin"],
            "allergy_raw": allergy_of(nm, allergy),
            "detail_url": (BASE + m["detail"]) if m["detail"] else None,
            "image_url": m["img"],
            "ext_id": ext,
            "option_raw": m["sub"],
            "cats": m["cats"],
        })

    if not out_menus:
        print("❌ 메뉴 0개 — 저장하지 않는다")
        return 1

    data = {
        "brand": BRAND,
        "slug": SLUG,
        "source": BASE + "/menu",
        "collected_at": COLLECTED,
        "origin_note": "메뉴 상세페이지에 「원산지 : 국내산」 표기 (감자볼튀김만 「원산지 : 벨기에산」). "
                       "출처: " + BASE + "/<메뉴상세>",
        "price_note_all": "공식 홈페이지에 판매가가 공개돼 있지 않다 — 목록 4쪽·상세 36쪽에서 「숫자+원」 0건",
        "weight_note": WEIGHT_NOTE,
        "cats": cats,
        "menus": out_menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))

    print("\n버린 줄 %d개" % len(dropped))
    for c, i, n, why in dropped:
        print(f"    - [{c} #{i}] {n!r} — {why}")
    npar = sum(1 for c in cats if c["parent"])
    npr = sum(1 for m in out_menus if m["price"] is not None)
    nor = sum(1 for m in out_menus if m["origin_raw"])
    nal = sum(1 for m in out_menus if m["allergy_raw"])
    print(f"\n✅ {OUT}")
    print(f"   카테고리 {len(cats)}개(하위 {npar}) · 메뉴 {len(out_menus)}개 · "
          f"가격 있는 것 {npr}개 · 원산지 {nor}개 · 알레르기 {nal}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
