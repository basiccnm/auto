# -*- coding: utf-8 -*-
"""피자헛 메뉴판 — 사이즈별로 전부. 2026-07-28

    python scripts/brand_pizzahut.py

만드는 것: data/brand_menu_list/pizzahut.json  (JSON 한 장. DB 는 건드리지 않는다)

────────────────────────────────────────────────────────────────────
경로 (브라우저로 확인한 실제 호출 — 추측 아님)
    GET  https://www.pizzahut.co.kr/api/menu/{매장코드}/list/{카테고리}
    POST https://www.pizzahut.co.kr/api/menu/nutritions   body = ["PPZ02131", ...]

매장코드 **0996** = 사이트가 로그인·주소설정 없이 기본으로 쓰는 매장.
`/api/store/findStoreCount/S020/0996` · `/api/menu/0996/list/best/VISIT` 로 확인했다.

카테고리는 `best`·`premium` 두 개가 아니다. 화면 탭을 하나씩 눌러
`performance.getEntriesByType('resource')` 로 잡은 **16개**가 아래 CATS 다.
(`/VISIT` 이 붙는 것과 안 붙는 것이 섞여 있다 — 화면이 그렇게 부른다)

🔴 홀 매장가 = `price` / `hhPrice`.
   `memberDlv`(배달) · `memberPack`(포장) 은 **회원 온라인 할인가**라 쓰지 않는다.
   실제로 쓰리스타 시그니처(L) 은 price 37,900 / memberDlv 29,900 / memberPack 27,900 이다.

🔴 사이즈는 합치지 않는다.
   API 는 «대표메뉴(rpst) → items[]» 구조고 items 하나가 사이즈 하나다.
   `수퍼슈프림(M) 28,500` 과 `수퍼슈프림(L) 33,900` 은 **각각 한 줄**로 나간다.
   ⚠️ 피자 탭 화면은 「한근/반근」을 한 장의 카드로 묶어 «L 30,900원 ~» 처럼 보여주지만
   그건 UI 묶음이다. API 가 주는 상품명(한근 치즈 콤비네이션(L) 35,900 /
   반근 치즈 콤비네이션(L) 30,900)이 실제 상품이라 그대로 쓴다.

🔴 구성·중량·원산지
   - `compose_raw` = 대표메뉴의 `rpstDesc` **원문 그대로** (없으면 null)
   - `origin_raw` · `allergy_raw` · `weight_raw` = `/api/menu/nutritions` 응답 원문
     (화면 「원산지정보」 버튼이 실제로 이 API 를 POST 로 부른다 — 영양성분표가 아니라
      진짜 원산지가 들어 있다: `페페로니(미국산 돼지고기)` 같은 원문)
   - 중량은 도우·엣지마다 달라서(오리지널 489g / 리치골드 715g) **전부 이어 적는다.**
     한 값만 나오면 그것만 적는다. 엣지는 옵션이지 메뉴가 아니라 메뉴로 만들지 않는다.
"""
import json
import os
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

STORE = "0996"
BASE = "https://www.pizzahut.co.kr/api/menu/%s/list/" % STORE
NUTRI = "https://www.pizzahut.co.kr/api/menu/nutritions"
GAP = 2.2
TODAY = "2026-07-28"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "data", "brand_menu_list", "pizzahut.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "ko-KR,ko;q=0.9",
      "Content-Type": "application/json",
      "Referer": "https://www.pizzahut.co.kr/menu/pizza/best"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 화면 탭 순서 그대로. name = 화면에 보이는 글자, ext_id = API 카테고리,
# eps = 그 탭이 실제로 부르는 목록 엔드포인트(화면에 먼저 깔리는 것부터)
CATS = [
    {"name": "피자", "parent": None, "ext_id": None, "eps": []},
    {"name": "인기메뉴", "parent": "피자", "ext_id": "best", "eps": ["best/VISIT"]},
    {"name": "3x 치즈페스타", "parent": "피자", "ext_id": "cheesefesta", "eps": ["cheesefesta/VISIT"]},
    {"name": "프리미엄", "parent": "피자", "ext_id": "premium", "eps": ["premium/VISIT"]},
    {"name": "US 오리진 (오리지널, 팬, 씬)", "parent": "피자", "ext_id": "usoriginal",
     "eps": ["usoriginal/VISIT"]},
    {"name": "하프앤하프", "parent": "피자", "ext_id": "halfnhalf", "eps": ["halfnhalf"]},

    {"name": "핫딜", "parent": None, "ext_id": None, "eps": []},
    {"name": "평일반값", "parent": "핫딜", "ext_id": "weekdays/half", "eps": ["weekdays/half/VISIT"]},
    {"name": "주말1+1", "parent": "핫딜", "ext_id": "weekends/pack", "eps": ["weekends/pack/VISIT"]},

    {"name": "1인메뉴", "parent": None, "ext_id": None, "eps": []},
    {"name": "인기메뉴", "parent": "1인메뉴", "ext_id": "flatzzbest", "eps": ["flatzzbest/VISIT"]},
    {"name": "5!타임세일⏰", "parent": "1인메뉴", "ext_id": "timesale", "eps": ["timesale/VISIT"]},
    {"name": "플래츠", "parent": "1인메뉴", "ext_id": "flatzz", "eps": ["flatzz/VISIT"]},
    {"name": "파스타헛", "parent": "1인메뉴", "ext_id": "pastahut", "eps": ["pastahut/VISIT"]},

    {"name": "사이드&음료", "parent": None, "ext_id": None, "eps": []},
    {"name": "인기메뉴", "parent": "사이드&음료", "ext_id": "sideAndDrinkBest",
     "eps": ["sideAndDrinkBest"]},
    {"name": "파스타&사이드", "parent": "사이드&음료", "ext_id": "pastaAndSide",
     "eps": ["dcSide", "pastaAndSide"]},
    {"name": "치킨", "parent": "사이드&음료", "ext_id": "chicken", "eps": ["dcChicken", "chicken"]},
    {"name": "음료&기타", "parent": "사이드&음료", "ext_id": "drinkAndEtc",
     "eps": ["dcBeverage", "drinkAndEtc"]},

    {"name": "SKT VIP 세트", "parent": None, "ext_id": "set", "eps": ["set"]},
]

# 「인기메뉴」 탭 = 다른 탭 상품을 골라 담은 사본. 값이 낡아 있는 줄이 있어 값 다툼에서 진다
CURATED = {"best", "flatzzbest", "sideAndDrinkBest"}


def path_of(c):
    return (c["parent"] + "/" + c["name"]) if c["parent"] else c["name"]


def get(url, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=UA,
                                 method="POST" if data else "GET")
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=40, context=ctx)
                              .read().decode("utf-8"))
        except Exception as e:
            print("   ! %s  %s" % (url.rsplit("/list/", 1)[-1], e), flush=True)
            time.sleep(GAP)
    return None


def txt(v):
    v = (v or "").strip()
    return v or None


def rows_of(payload):
    """엔드포인트 응답 → (대표메뉴 dict, 사이즈 item dict) 목록.

    두 가지 모양이 온다:
      ① 피자·세트  : [{rpstName, rpstDesc, items:[{name, price, ...}]}]  ← items 가 사이즈
      ② 사이드·음료 : [{name, price, ...}]                                ← 그 자체가 한 줄
      ③ 할인목록    : {"menus": [...], "count": n}                        ← ② 를 감싼 것
    """
    if payload is None:
        return []
    if isinstance(payload, dict):
        payload = payload.get("menus") or []
    out = []
    for g in payload:
        if not isinstance(g, dict):
            continue
        items = g.get("items")
        if isinstance(items, list) and items:
            for it in items:
                out.append((g, it))
        else:
            out.append((g, g))
    # order 가 순서 필드다. 배열 순서보다 우선(같으면 나온 순서)
    out = [(i, g, it) for i, (g, it) in enumerate(out)]
    out.sort(key=lambda t: (t[2].get("order") if isinstance(t[2].get("order"), int) else 10 ** 9,
                            t[0]))
    return [(g, it) for _, g, it in out]


def weight_text(rows):
    seen, pairs = set(), []
    for r in rows:
        w = txt(str(r.get("totalWeight") or ""))
        if not w or w == "None":
            continue
        edge = txt(r.get("edgeName")) or ""
        if (edge, w) in seen:
            continue
        seen.add((edge, w))
        pairs.append((edge, w))
    if not pairs:
        return None
    names = {r.get("menuName") for r in rows}
    if len(pairs) == 1:
        e, w = pairs[0]
        if e in names or not e:
            return "총 중량 %sg" % w
        return "총 중량 %s %sg" % (e, w)
    pairs.sort(key=lambda p: (int(p[1]) if p[1].isdigit() else 10 ** 9, p[0]))
    return "총 중량 " + " / ".join("%s %sg" % (e, w) for e, w in pairs)


def main():
    print("피자헛 · 매장코드 %s · %s" % (STORE, TODAY))
    cats_out, menus, by_name = [], [], {}
    dropped, flagged, conflicts = [], [], []
    cat_names = {c["name"] for c in CATS}
    got_any = False

    for c in CATS:
        p = path_of(c)
        cats_out.append({"name": c["name"], "parent": c["parent"], "ext_id": c["ext_id"]})
        if not c["eps"]:
            print("  [탭] %s" % p)
            continue
        pos, seen_cd, seen_nm = 0, set(), set()
        for ep in c["eps"]:
            payload = get(BASE + ep)
            time.sleep(GAP)
            if payload is None:
                continue
            got_any = True
            rows = rows_of(payload)
            # 같은 목록에 «이름은 같은데 0원» 인 사본이 있다(세트 구성용). 화면에도 안 나온다
            priced = {txt(it.get("name")) for _, it in rows if it.get("price")}
            for g, it in rows:
                name = txt(it.get("name"))
                if not name:
                    continue
                if not it.get("price") and name in priced:
                    dropped.append((p, name, "동명 0원 사본(정상가 줄이 따로 있다)"))
                    continue
                cd = it.get("menuCd")
                price = it.get("price")
                hh = it.get("hhPrice")
                # 같은 탭 안 중복 진열(할인목록 + 본목록에 같은 상품) → 앞자리만
                if cd and cd in seen_cd:
                    dropped.append((p, name, "같은 탭 중복(menuCd %s)" % cd))
                    continue
                # 이름이 같은데 값이 0 인 줄 = 세트 구성용 0원 사본. 화면에도 안 나온다
                if name in seen_nm and not price:
                    dropped.append((p, name, "같은 탭에 동명 0원 사본"))
                    continue
                if cd:
                    seen_cd.add(cd)
                seen_nm.add(name)

                # UI 문자열 걸러내기 — 지우지 않고 목록만 남긴다(피자는 이름이 길다)
                if name.endswith((".", "!", "?", "~")) or len(name) >= 18 or name in cat_names:
                    flagged.append((p, name))

                key = name
                if key in by_name:
                    m = by_name[key]
                    if price and m["price"] and price != m["price"]:
                        # 「인기메뉴」 탭은 골라 담은 사본이라 값이 낡는다.
                        # 실측: [세트]페페로니 미트 파스타 가 flatzzbest 응답엔 17,500 인데
                        # 화면은 두 탭 모두 17,300 을 그린다(파스타헛 응답값). 그래서 원탭이 이긴다
                        if c["ext_id"] in CURATED or by_name[key]["_from"] not in CURATED:
                            conflicts.append((name, m["price"], price, m["_from"], c["ext_id"],
                                              "그대로 둠"))
                        else:
                            conflicts.append((name, m["price"], price, m["_from"], c["ext_id"],
                                              "새 값으로 교체"))
                            m["price"] = price
                            m["_from"] = c["ext_id"]
                    m["cats"].append([p, pos])
                    pos += 1
                    continue

                m = {
                    "name": name,
                    "price": price if price else None,
                    "price_source": "official",
                    "price_note": None if (price == hh or not price)
                                  else "price %s / hhPrice %s" % (price, hh),
                    "compose_raw": txt(g.get("rpstDesc")),
                    "weight_raw": None,
                    "origin_raw": None,
                    "allergy_raw": None,
                    "detail_url": None,
                    "image_url": None,
                    "ext_id": cd,
                    "cats": [[p, pos]],
                    "_size": it.get("size"),
                    "_from": c["ext_id"],
                }
                by_name[key] = m
                menus.append(m)
                pos += 1
        print("  [%s] %s → %d줄" % (",".join(c["eps"]), p, pos))

    if not got_any:
        print("카테고리를 하나도 못 받았다 — 파일을 쓰지 않는다.")
        return 1

    # ── 원산지 · 알레르기 · 중량 ────────────────────────────────
    cds = [m["ext_id"] for m in menus if m["ext_id"]]
    nut = {}
    for i in range(0, len(cds), 60):
        chunk = cds[i:i + 60]
        d = get(NUTRI, chunk)
        time.sleep(GAP)
        for r in (d or []):
            nut.setdefault(r.get("menuCd"), []).append(r)
    for m in menus:
        rows = nut.get(m["ext_id"]) or []
        if not rows:
            continue
        ori = list(dict.fromkeys([txt(r.get("origin")) for r in rows if txt(r.get("origin"))]))
        alg = list(dict.fromkeys([txt(r.get("allergy")) for r in rows if txt(r.get("allergy"))]))
        m["origin_raw"] = " / ".join(ori) or None
        m["allergy_raw"] = " / ".join(alg) or None
        m["weight_raw"] = weight_text(rows)

    sizes = {}
    for m in menus:
        s = m.pop("_size", None) or "-"
        m.pop("_from", None)
        sizes[s] = sizes.get(s, 0) + 1

    doc = {
        "brand": "피자헛", "slug": "pizzahut",
        "source": "https://www.pizzahut.co.kr/api/menu/%s/list/{카테고리}"
                  " + POST https://www.pizzahut.co.kr/api/menu/nutritions"
                  " (매장코드 %s · 홀 매장가 price/hhPrice)" % (STORE, STORE),
        "collected_at": TODAY,
        "origin_note": None,
        "cats": cats_out,
        "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print()
    print("카테고리 %d개(상위 %d · 하위 %d) · 메뉴 %d개 · 가격 %d개 · 구성 %d개 · 원산지 %d개"
          % (len(cats_out), sum(1 for c in cats_out if not c["parent"]),
             sum(1 for c in cats_out if c["parent"]), len(menus),
             sum(1 for m in menus if m["price"]),
             sum(1 for m in menus if m["compose_raw"]),
             sum(1 for m in menus if m["origin_raw"])))
    print("사이즈 표기: " + " · ".join("%s %d줄" % (k, v) for k, v in sorted(sizes.items())))
    if flagged:
        print("\n⚠️ UI 문자열 검사에 걸린 이름 %d개 — **지우지 않았다**(전부 실제 상품):" % len(flagged))
        for p, n in flagged:
            print("   %-22s %s" % (p, n))
    if dropped:
        print("\n버린 줄 %d개:" % len(dropped))
        for p, n, why in dropped:
            print("   %-22s %-28s %s" % (p, n, why))
    if conflicts:
        print("\n같은 이름 다른 값 %d건:" % len(conflicts))
        for n, a, b, fa, fb, how in conflicts:
            print("   %-28s %s(%s) vs %s(%s) → %s" % (n, a, fa, b, fb, how))
    print("\n→ %s" % os.path.normpath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
