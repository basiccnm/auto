# -*- coding: utf-8 -*-
"""피자나라치킨공주(피나치공) 메뉴판 수집 → data/brand_menu_list/pncg.json  (2026-07-28)

    python scripts/brand_pncg.py

구조 (실측)
-----------------------------------------------------------------------------
1) 탭 목록은 페이지가 직접 불러오는 컴포넌트 JS 안에 박혀 있다 (주소 조합 아님)
       /public/assets/build/components/menuTabs-OWOHX4GB.js
       MENU_TABS = [new 신메뉴, set 세트 메뉴, pizza 피자 메뉴,
                    chicken 치킨 메뉴, side 사이드 메뉴]
2) 각 탭 페이지는 SSR 이고, 메뉴가 통째로 인라인 JSON 으로 들어있다
       <script id="menu-json" type="application/json"> [ {...}, ... ] </script>
   → 헤드리스/브라우저 필요 없음. 페이징 없음(배열 하나가 전부).
3) 🔴 가격은 **사이즈 배열**이다 — `prices:[{size:"M",value:"17,900원"},
   {size:"L",value:"21,900원"}]`. 한쪽만 담으면 안 되므로 **사이즈마다 한 줄**을 만든다.
   이름 뒤에 사이트 표기 그대로 사이즈를 붙인다 (`콤비네이션 피자 M`).
4) 토핑(구성)·원산지·알레르기·중량은 목록에 없고 **자체 API** 에 있다
       https://api.pncg.co.kr/api/menu-nutrition/menu/{id}?menuType={gubun}
   - gubun 2=피자 3=치킨 4=사이드 (→ `menuNutrition`)
   - gubun 1=세트 (→ `pizzaMenuNutrition` + `chickenMenuNutrition` 둘 다)
     세트는 피자·치킨 원산지가 다르므로 **둘을 이어붙인다**
   - `menu-topping/menu/{id}` 는 «추가 토핑 옵션»(치즈크러스트 등)이라
     기본 구성이 아니다 → compose_raw 에 넣지 않는다
5) 신메뉴(new) 탭은 배너 이미지 2장뿐 — menu-json 이 없다. 카테고리만 남긴다.

DB 는 건드리지 않는다(읽지도 않는다). 메뉴가 0개면 파일을 저장하지 않는다.
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "pncg.json")

HOST = "https://pncg.co.kr"
API = "https://api.pncg.co.kr"
TABS = [                                   # menuTabs-OWOHX4GB.js 의 MENU_TABS 순서 그대로
    ("new", "신메뉴"),
    ("set", "세트 메뉴"),
    ("pizza", "피자 메뉴"),
    ("chicken", "치킨 메뉴"),
    ("side", "사이드 메뉴"),
]
COLLECTED = "2026-07-28"
GAP = 0.7

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9", "Referer": HOST + "/"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_JSON = re.compile(r'(?is)<script id="menu-json"[^>]*>(.*?)</script>')
RX_WON = re.compile(r"([0-9][0-9,.]*)\s*원")


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, context=ctx, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:                                    # noqa: BLE001
            print("   ! %s (%s/%s) %s" % (url, i + 1, tries, e))
            time.sleep(2)
    return ""


def clean(v):
    """빈 문자열·'-'·None 을 전부 None 으로."""
    if v is None:
        return None
    s = str(v).replace("\r\n", "\n").strip()
    if s in ("", "-", "--"):
        return None
    return s


def won(value):
    """'13,900원' → 13900 · '1개: 700원' → 700 · '20.900원' → 20900(사이트 오타)."""
    m = RX_WON.search(value or "")
    if not m:
        return None
    d = re.sub(r"[^0-9]", "", m.group(1))
    return int(d) if d else None


# ---------------------------------------------------------------- 목록(탭)
def fetch_tab(key):
    url = "%s/public/menu/%s/index" % (HOST, key)
    html = get(url)
    if not html:
        return url, []
    raw_hits = len(RX_JSON.findall(html))
    html = RX_COMMENT.sub("", html)                 # 죽은 메뉴·숨은 탭 제거
    hits = RX_JSON.findall(html)
    if raw_hits != len(hits):
        print("   * 주석 안에 있던 menu-json %d개 버림" % (raw_hits - len(hits)))
    if not hits:
        return url, []
    out = []
    for blob in hits:
        try:
            data = json.loads(blob)
        except Exception as e:                                    # noqa: BLE001
            print("   ! menu-json 파싱 실패: %s" % e)
            continue
        if isinstance(data, list):
            out.extend(data)
    return url, out


# ---------------------------------------------------------------- 상세(API)
_cache = {}


def fetch_detail(mid, gubun):
    k = (str(mid), str(gubun))
    if k in _cache:
        return _cache[k]
    url = "%s/api/menu-nutrition/menu/%s?menuType=%s" % (API, mid, gubun)
    txt = get(url)
    blocks = []
    if txt:
        try:
            j = json.loads(txt)
        except Exception:                                         # noqa: BLE001
            j = {}
        if str(gubun) == "1":                       # 세트 = 피자 + 치킨
            for key in ("pizzaMenuNutrition", "chickenMenuNutrition",
                        "sideMenu1Nutrition", "sideMenu2Nutrition"):
                if isinstance(j.get(key), dict):
                    blocks.append(j[key])
        elif isinstance(j.get("menuNutrition"), dict):
            blocks.append(j["menuNutrition"])
    _cache[k] = blocks
    time.sleep(GAP)
    return blocks


def join_field(blocks, field, multi):
    """원문 그대로 이어붙인다. 여러 구성품이면 «구성품명: 값» 으로 구분."""
    parts = []
    for b in blocks:
        v = clean(b.get(field))
        if not v:
            continue
        nm = clean(b.get("menuName"))
        parts.append("%s: %s" % (nm, v) if (multi and nm) else v)
    return " / ".join(parts) or None


def weight_of(blocks, size, is_set):
    """중량 원문. 세트가 아니면 그 사이즈 줄만, 세트면 구성품별로 전부."""
    parts = []
    for b in blocks:
        v = clean(b.get("numberPieces")) or clean(b.get("oneServingCapacity"))
        if not v:
            continue
        nm = clean(b.get("menuName"))
        if not is_set and size:
            lines = [ln.strip() for ln in v.split("\n") if ln.strip()]
            hit = [ln for ln in lines if ln.upper().startswith(size.upper() + ":")
                   or ln.upper().startswith(size.upper() + " :")]
            if hit:
                v = " ".join(hit)
        v = v.replace("\n", " ")
        parts.append("%s: %s" % (nm, v) if (is_set and nm) else v)
    return " / ".join(parts) or None


# ---------------------------------------------------------------- UI 문자열 검사
def looks_like_ui(name, cat_names):
    if name in cat_names:
        return "카테고리 이름과 같음"
    if re.search(r"[.!?~…]$", name):
        return "문장부호로 끝남"
    if len(name) >= 18:
        return "18자 이상"
    return None


def main():
    cats, menus, dropped = [], [], []
    seen = {}                                        # 이름 → menus 인덱스 (같은 이름 합침)
    cat_names = {label for _, label in TABS}
    used = []

    for key, label in TABS:
        cats.append({"name": label, "parent": None, "ext_id": key})
        url, items = fetch_tab(key)
        used.append(url)
        print("[%s] %s — 목록 %d건" % (key, label, len(items)))
        if not items:
            print("   (menu-json 없음 — 배너 이미지 페이지)")
            continue

        pos = 0
        for it in items:
            mid = str(it.get("id") or "").strip()
            gubun = str(it.get("gubun") or "").strip()
            base = clean(it.get("name"))
            if not base:
                dropped.append(("(이름 없음) id=%s" % mid, "name 이 비었다"))
                continue

            blocks = fetch_detail(mid, gubun) if mid else []
            is_set = (gubun == "1")
            multi = len(blocks) > 1

            # 구성 — summary + 부가설명(가격 아닌 것) + 토핑
            comp = []
            s = clean(it.get("summary"))
            if s:
                comp.append(s.replace("\r\n", " ").replace("\n", " ").strip())
            price_notes = []
            for f in ("sub_info", "sub_info2"):
                v = clean(it.get(f))
                if not v:
                    continue
                (price_notes if "원" in v else comp).append(v)
            for b in blocks:
                t = clean(b.get("topping"))
                if not t:
                    continue
                nm = clean(b.get("menuName"))
                comp.append("[%s] 토핑: %s" % (nm, t) if nm else "토핑: %s" % t)
            compose_raw = " / ".join(comp) or None

            origin_raw = join_field(blocks, "countryOrigin", multi)
            allergy_raw = join_field(blocks, "allergy", multi)

            img = clean(it.get("image"))
            if img and img.startswith("/"):
                img = HOST + img

            prices = it.get("prices") or [{"size": "", "value": ""}]
            for p in prices:
                size = clean(p.get("size")) or ""
                value = clean(p.get("value")) or ""
                name = ("%s %s" % (base, size)).strip() if size else base

                why = looks_like_ui(name, cat_names)
                if why:
                    dropped.append((name, why))
                    continue

                pn = list(price_notes)
                price = won(value)
                if value and price is not None and re.sub(r"[^0-9]", "", value) != str(price):
                    pn.insert(0, value)              # '1개: 700원' 처럼 값에 조건이 붙은 경우
                elif value and "." in value:
                    pn.insert(0, "사이트 표기 %s" % value)

                if name in seen:                     # 같은 이름은 한 줄로 (카테고리만 추가)
                    m = menus[seen[name]]
                    if [label, pos] not in m["cats"]:
                        m["cats"].append([label, pos])
                    pos += 1
                    continue

                seen[name] = len(menus)
                menus.append({
                    "name": name,
                    "price": price,
                    "price_source": "official",
                    "price_note": " / ".join(pn) or None,
                    "compose_raw": compose_raw,
                    "weight_raw": weight_of(blocks, size, is_set),
                    "origin_raw": origin_raw,
                    "allergy_raw": allergy_raw,
                    "detail_url": None,              # 별도 상세 URL 없음 (모달)
                    "image_url": img,
                    "ext_id": ("%s-%s" % (mid, size)) if size else (mid or None),
                    "cats": [[label, pos]],
                })
                pos += 1
        print("   → 누적 메뉴 %d줄" % len(menus))

    if dropped:
        print("\n버린 줄 %d개:" % len(dropped))
        for n, w in dropped:
            print("   - %s  (%s)" % (n, w))
    else:
        print("\n버린 줄 없음")

    if not menus:
        print("메뉴 0건 — 저장하지 않는다")
        return 1

    doc = {
        "brand": "피자나라치킨공주",
        "slug": "pncg",
        "source": " , ".join(used) + " , " + API + "/api/menu-nutrition/menu/{id}?menuType={gubun}",
        "collected_at": COLLECTED,
        "origin_note": None,                         # 브랜드 공통 원산지 표기 없음 (메뉴별)
        "cats": cats,
        "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("\n저장: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
