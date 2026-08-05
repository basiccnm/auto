# -*- coding: utf-8 -*-
"""맥도날드 메뉴판 — **JSON 전용** 수집기. 2026-07-28 재작성

    python scripts/brand_mcdonalds.py

→ data/brand_menu_list/mcdonalds.json 하나만 만든다. **DB 는 건드리지 않는다.**

🔴 맥도날드는 **가격을 어디에도 공개하지 않는다.** `price` 는 전부 null 이고 그게 정상이다.
   **가격이 없다고 메뉴를 빼지 않는다** — 이름·카테고리·순서만으로도 메뉴판은 선다.

## 🔎 가격을 어디까지 뒤졌나 (2026-07-28 — 버거킹 `dineInprc` 사례 뒤 재확인)
같은 짓을 또 하지 말라고 남긴다. **여기까지는 전부 «없음» 이 확인된 길이다.**

| 어디 | 결과 |
|---|---|
| `/api/v1/kor/product/product/list` · `/menu/detail/{seq}` · `/product/recommend/list` | 응답 **전체 키 88개**를 다 뽑아 `price·amt·prc·won·sell·dineIn·eatIn·takeOut·delivery` 로 부분문자열 재귀검색 → **0건.** 영양(calorie·weight·volume)만 있고 `weight` 조차 전부 빈 문자열 |
| `/_nuxt/*.js` 7개 청크(전체 351KB) | `price` 는 **영문 홍보문구**(“at a special price!”)뿐. 주문·결제·가격 관련 라우트·엔드포인트 **자체가 없다** |
| 「주문하기」 버튼 (`dg95h.app.goo.gl/M7zy`) | **앱 전용 딥링크.** 데스크톱은 `mcdonaldsapps.com/page-not-found` 로 떨어진다 — 웹 주문 화면이 없다 |
| `mcdelivery.co.kr` (옛 맥딜리버리 웹) | **DNS 자체가 죽었다.** 앱으로 통합됨 |
| `m.mcdonalds.co.kr` | 같은 Nuxt 앱. 가격 없음 |
| `/api/v1/kor/promotion/list` | 배너 이미지 목록. 「1000원 할인」 같은 **제목 문구**뿐, 메뉴 가격표가 아니다 |
| 폰에 깔린 APK `com.mcdonalds.mobileapp` (205MB, adb pull 로 파일만 열람) | 아래 참조 |

### APK 에서 나온 것 — 가격은 있지만 **우리가 부를 수 없다**
- 메뉴 주소는 `{ME_BASE_URL}/exp/v1/menu/gmal/restaurants/{매장ID}` (+ `/dayparts/` · `/details`).
  🔴 **전국 공통 가격표가 아니라 «매장별» 메뉴다**
- 가격 모델은 있다 — `basePrice` · `MEAL_PRICE`, 채널이 `eatInChannelName` · `takeOutChannelName` ·
  `deliveryChannelName` 로 갈린다(홀/포장/배달)
- 그런데 **호스트와 열쇠가 APK 안에 없다.** `ME1_BASE_URL` · `ME2_BASE_URL` · `C3_BASE_URL` ·
  `mopBff_baseUrl` 과 `connectors_marketEngine_*_androidKey` 는 전부 **Firebase Remote Config 키 이름만**
  들어 있고 값은 실행 시 받아온다(APK 전체 URL 318개를 뽑았는데 맥도날드 API 호스트는 **0개**)
- 필수 헤더도 확인됨 — `mcd-marketid`(없으면 «Missing required header: mcd-marketid») · `mcd-clientid` ·
  `mcd-clientsecret` · `mcd-uuid` · `mcd-correlation-id` + 로그인 토큰
- ⛔ 남은 길은 **앱 실행·로그인 또는 코드값 추측**뿐이라 여기서 멈춘다

**→ 결론: 가격은 네이버 플레이스(에뮬)로 채운다.** 홀 매장가 기준.

## 어느 길로 뚫었나 (주소를 조합한 게 아니라 화면이 실제로 부른 것)
`/kor/menu/burger` 는 Nuxt SPA 라 HTML 에 메뉴가 없다(`__NUXT__` 의 `allMenus-burger` = null).
브라우저로 열어 `performance.getEntriesByType('resource')` 로 잡은 실제 호출:

    /api/v1/kor/category/list                                       ← 상위 탭 7개
    /api/v1/kor/product/product/list?page=&view_rows=&mainCategory=&subCategory=&searchWord
                                                                    ← 하위 칩 + 상품 목록
    /api/v1/kor/menu/detail/{seq}?product_rnum=&subCategory=&exposure   ← 상세(가격 없음)
    /api/v1/kor/product/original                                    ← 원산지표지판 (브랜드 공통 1장)

⚠️ 옛 버전은 HTML 을 크롬 헤드리스로 긁어 «한 쪽 13개» 페이징을 따라다녔다.
   API 는 `view_rows` 로 한 번에 다 준다 — **페이징이 필요 없다**(그래도 안전하게 200 으로 요청하고
   totalCount 와 대조한다).
⚠️ `subCategory=0` 은 상품을 0개 준다. 하위 seq 를 반드시 넣어야 한다.
⚠️ 상위 카테고리 순서는 배열 순서가 아니라 `sortingNo` 다(화면에서 확인함).
   하위는 `sortingNo` 가 0 인 곳이 있어 **API 배열 순서**를 쓴다(화면 칩 순서와 일치 확인함).
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "맥도날드"
SLUG = "mcdonalds"
HOST = "https://www.mcdonalds.co.kr"
API = HOST + "/api/v1/kor"
LIST = API + "/product/product/list?page=1&view_rows=200&mainCategory=%d&subCategory=%d&searchWord"
CATS = API + "/category/list"
ORIGIN = API + "/product/original"
DETAIL = HOST + "/kor/menu/detail/%d/%d/%d"

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "brand_menu_list", SLUG + ".json")
GAP = 2.0
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": HOST + "/kor/menu/burger",
      "Accept": "application/json"}

RX_TAG = re.compile(r"<[^>]+>")
RX_COMMENT = re.compile(r"<!--.*?-->", re.S)
RX_BADGE = re.compile(r"^(신제품|신메뉴|NEW|BEST|추천|인기|한정)\s*", re.I)
# 🔴 alt 에 「제품 이미지」·「제품 사진」이 붙는다 — 메뉴명도 구성도 아니다.
#    끝에만 붙는 게 아니라 이름과 구성 **사이**에도 낀다
#    (「… 상하이 버거 세트 사진_후렌치 후라이M …」)
RX_TAIL = re.compile(r"\s*(제품\s*이미지|제품\s*사진|사진|이미지)\s*$")
RX_LEAD = re.compile(r"^(제품\s*이미지|제품\s*사진|사진|이미지)\s*[_\-]?\s*")
RX_SENT_END = re.compile(r"[.!?…]$")

ENT = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'",
       "&nbsp;": " ", "&reg;": "®", "&trade;": "™"}


def clean(s):
    """HTML 주석 → 태그 → 엔티티 → 공백 정리. 글자(®·™)는 살린다."""
    if not s:
        return ""
    s = RX_COMMENT.sub("", s)
    s = s.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    s = RX_TAG.sub("", s)
    for k, v in ENT.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


def key(s):
    """이름 대조용 — 상표기호·공백만 지운다. 저장하는 값은 절대 이걸로 바꾸지 않는다."""
    return re.sub(r"[\s®™©·]", "", s or "")


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                raise
            print("   재시도(%d) %s — %s" % (i + 1, url[-60:], e), flush=True)
            time.sleep(GAP * 2)


def origin_table():
    """원산지표지판 — 브랜드 공통 1장. 원문 그대로 보관 + 메뉴명 완전일치만 개별 배정."""
    try:
        rows = get(ORIGIN)["resultObject"]["list"]
    except Exception as e:
        print("⚠️ 원산지 페이지 실패: %s" % e)
        return None, {}
    lines, table = [], {}
    for r in rows:
        raw = clean(r.get("originalInfo"))
        if not raw:
            continue
        lines.append(raw)
        # 「메뉴 / 메뉴 - 부위_고기 : 원산지」 → 첫 ':' 앞의 마지막 '-' 에서 자른다
        c = raw.find(":")
        d = raw.rfind("-", 0, c if c > 0 else len(raw))
        if d < 0:
            continue
        names, info = raw[:d], raw[d + 1:].strip()
        if not info:
            continue
        for nm in names.split("/"):
            k = key(nm)
            if k:
                table.setdefault(k, info)      # 먼저 나온 줄이 이긴다
    return ("\n".join(lines) or None), table


def compose_of(alt, name):
    """세트 구성 — `alt` 에서 **메뉴명 접두사만** 떼어낸 나머지. 원문 그대로.
    접두사가 안 맞으면 비운다(문장을 지어내지 않는다)."""
    a = RX_TAIL.sub("", clean(alt))
    a = RX_BADGE.sub("", a).strip()
    if not a:
        return None
    ka, kn = key(a), key(name)
    if not kn or not ka.startswith(kn):
        return None
    # 원문에서 이름에 해당하는 글자 수만큼 앞을 잘라낸다
    cnt, i = 0, 0
    while i < len(a) and cnt < len(kn):
        if not re.match(r"[\s®™©·]", a[i]):
            cnt += 1
        i += 1
    # ⚠️ 자른 자리가 **낱말 경계가 아니면** 버린다.
    #    「맥너겟 4조각과 소스 제공」에서 이름 「맥너겟 4조각」을 떼면 «과 소스 제공» 이라는
    #    말이 안 되는 토막이 남는다 — 그건 세트 구성이 아니다.
    if i < len(a) and not re.match(r"[\s_\-,·]", a[i]):
        return None
    rest = RX_LEAD.sub("", a[i:].strip(" _-,·").strip()).strip(" _-,·").strip()
    return rest or None


def main():
    origin_note, otab = origin_table()
    time.sleep(GAP)

    cats_raw = get(CATS)["resultObject"]["list"]
    cats_raw.sort(key=lambda c: (c.get("sortingNo") or 0, c["seq"]))
    time.sleep(GAP)

    cats, menus, order = [], {}, []          # order: 이름 등장 순서
    dropped, longnames = [], []
    catnames = set()

    for c in cats_raw:
        top = clean(c["korName"])
        catnames.add(key(top))
        cats.append({"name": top, "parent": None, "ext_id": c.get("slug") or str(c["seq"])})
        head = get(LIST % (c["seq"], 0))["resultObject"]
        subs = head.get("subCategory") or []
        time.sleep(GAP)
        seen_top = []                        # 탭 전체 목록 (하위를 순서대로 이어붙인 것)
        for s in subs:
            sub = clean(s["korName"])
            catnames.add(key(sub))
            path = "%s/%s" % (top, sub)
            cats.append({"name": sub, "parent": top, "ext_id": str(s["seq"])})
            o = get(LIST % (c["seq"], s["seq"]))["resultObject"]
            rows = o.get("list") or []
            if len(rows) != o.get("totalCount"):
                print("⚠️ %s — totalCount %s 인데 %d개만 왔다" % (path, o.get("totalCount"), len(rows)))
            print("  %-22s %d개" % (path, len(rows)), flush=True)
            for i, p in enumerate(rows):
                nm = clean(p.get("korName"))
                if not nm:
                    continue
                if RX_SENT_END.search(nm) or key(nm) in catnames:
                    dropped.append((nm, path, "문장부호로 끝남" if RX_SENT_END.search(nm)
                                    else "카테고리 이름과 같음"))
                    continue
                if len(nm) >= 18:
                    longnames.append((nm, path))
                m = menus.get(nm)
                if not m:
                    img = p.get("pcImageUrl") or p.get("moImageUrl") or ""
                    m = {"name": nm, "price": None, "price_source": None, "price_note": None,
                         "compose_raw": compose_of(p.get("pcKorAlt"), nm),
                         "weight_raw": (p.get("weight") or "").strip() or None,
                         "origin_raw": None,
                         "allergy_raw": None,
                         "detail_url": DETAIL % (p["seq"], p.get("rnum") or i + 1, s["seq"]),
                         "image_url": (HOST + img) if img else None,
                         "ext_id": str(p["seq"]),
                         "cats": []}
                    k = key(nm)
                    for cand in (k, re.sub(r"(세트|단품|콤보)$", "", k)):
                        if cand in otab:
                            m["origin_raw"] = otab[cand]
                            break
                    menus[nm] = m
                    order.append(nm)
                m["cats"].append([path, i])
                if nm not in seen_top:
                    seen_top.append(nm)
            time.sleep(GAP)
        for i, nm in enumerate(seen_top):    # 상위 탭에도 «탭 전체» 순서로 붙인다
            menus[nm]["cats"].append([top, i])

    # 메뉴의 cats 를 «화면의 카테고리 순서» 로 정렬한다 (상위 → 그 하위)
    rank = {(c["parent"] + "/" + c["name"] if c["parent"] else c["name"]): i
            for i, c in enumerate(cats)}
    for m in menus.values():
        m["cats"].sort(key=lambda t: rank.get(t[0], 9999))

    if not cats:
        print("🔴 카테고리 0개 — 저장하지 않는다")
        return
    if dropped:
        print("\n● 버린 줄 %d개" % len(dropped))
        for nm, path, why in dropped:
            print("   ✂ %-34s %-18s %s" % (nm[:34], path, why))
    if longnames:
        print("\n● 18자 이상이라 검토 대상이지만 **살렸다**(세트 이름이 원래 길다) %d개" % len(longnames))
        for nm, path in longnames[:10]:
            print("   ・%s (%s)" % (nm, path))
        if len(longnames) > 10:
            print("   … 외 %d개" % (len(longnames) - 10))

    doc = {"brand": BRAND, "slug": SLUG,
           "source": API + "/product/product/list (+ /category/list, /product/original)",
           "collected_at": time.strftime("%Y-%m-%d"),
           "origin_note": origin_note,
           "cats": cats,
           "menus": [menus[n] for n in order]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    sub = sum(1 for c in cats if c["parent"])
    print("\n● 저장 %s" % os.path.normpath(OUT))
    print("  카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개 · 구성 %d개 · 원산지 %d개"
          % (len(cats), sub, len(order),
             sum(1 for n in order if menus[n]["price"] is not None),
             sum(1 for n in order if menus[n]["compose_raw"]),
             sum(1 for n in order if menus[n]["origin_raw"])))


if __name__ == "__main__":
    main()
