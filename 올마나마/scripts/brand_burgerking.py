# -*- coding: utf-8 -*-
"""버거킹 메뉴판을 **JSON 한 장으로만** 받는다. 2026-07-28 (JSON 전용으로 재작성)

    python scripts/brand_burgerking.py
        → data/brand_menu_list/burgerking.json

⛔ **DB 를 import 하지 않는다.** 적재는 별도 단계(`brand_menu_store.replace_brand`)에서 한다.
   옛 버전은 여기서 바로 `brand_menu_official` 에 INSERT 했고 **카테고리를 아예 안 담았다**.

────────────────────────────────────────────────────────────
어느 길로 뚫었나 — 버거킹 자체 API (`www.burgerking.co.kr/burgerking/BKR****.json`)
────────────────────────────────────────────────────────────
`/menu/main` 은 5.5KB 껍데기(SPA)다. 헤드리스로 렌더하면 `.menu_card` 219장이 마크업에
다 들어있지만(`innerText` 로 보면 61자라 «메뉴 없음» 으로 오판한다), 그 마크업에는
**가격·중량·알레르기·원산지가 없다.** 화면을 그리는 원본 데이터를 그대로 받는 편이 낫다.

브라우저 network 탭에서 확인한 실제 호출 3개 (주소를 조합해 찌른 것이 아니다):

| trcode | body | 주는 것 |
|---|---|---|
| `BKR0632` | `{}` | 카테고리 8개(`menuCategoryNm`·`Cd`·`Seq`) + 그 안의 메뉴 진열 순서 |
| `BKR0634` | `{"menuCd": "..."}` | **`dineInprc` = 매장(홀) 판매가** · `menuCalorie` · `menuDesc` |
| `BKR0347` | `{}` | 브랜드 공통 **원산지** · 영양성분(중량) · 알레르기 — 상세페이지의 «원산지,영양성분,알레르기유발성분» 팝업 |

호출 규약(브라우저가 보내는 것 그대로):
    POST /burgerking/<trcode>.json
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    message={"header":{...,"trcode":"<trcode>","cd_call_chnn":"01"},"body":{...}}

🔴 **가격은 화면에 없지만 API 에는 있다.**
   `/menu/main` · `/menu/detail/*` DOM 전체에 「원」 이 0건인 건 사실이다. 그런데 상세 API 가
   `dineInprc` 를 준다. 검증: 펜타치즈와퍼 **9,700** / 펜타치즈와퍼 세트 **11,900** —
   대표가 앱 화면에서 읽어둔 값과 일치했다. **계산해서 채운 값이 아니라 API 가 준 값이다.**

⛔ 단품과 세트는 **다른 메뉴**다. `menuNm` 을 그대로 쓴다(`세트`·`라지세트` 표기 유지).
⛔ 이름을 다듬지 않는다. 원산지는 브랜드 공통 한 장이라 최상위 `origin_note` 에 원문 그대로.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "burgerking.json")

BRAND = "버거킹"
SLUG = "burgerking"
SITE = "https://www.burgerking.co.kr"
API = SITE + "/burgerking/%s.json"
LIST_URL = SITE + "/menu/main"
DETAIL_URL = SITE + "/menu/detail/%s"
COLLECTED_AT = "2026-07-28"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")


def call(trcode, body, tries=3):
    """버거킹 자체 API 한 번. 실패하면 예외를 올린다(조용히 넘기지 않는다)."""
    msg = {"header": {"result": True, "error_code": "", "error_text": "",
                      "info_text": "", "message_version": "", "login_session_id": "",
                      "trcode": trcode, "cd_call_chnn": "01"},
           "body": body}
    data = urllib.parse.urlencode({"message": json.dumps(msg, ensure_ascii=False)}).encode("utf-8")
    req = urllib.request.Request(API % trcode, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept-Language": "ko-KR", "User-Agent": UA,
        "Referer": LIST_URL, "Origin": SITE})
    last = None
    for i in range(tries):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
            if not r.get("header", {}).get("result"):
                raise RuntimeError("%s: %s" % (trcode, r.get("header")))
            return r["body"]
        except Exception as e:            # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# ── 메뉴가 아닌 줄 걸러내기 (지우기 전에 반드시 출력한다) ────────────────
def looks_wrong(name, cat_names):
    why = []
    if name.rstrip().endswith((".", "!", "?", "~")):
        why.append("문장부호로 끝남")
    if len(name) >= 18:
        why.append("18자 이상")
    if name in cat_names:
        why.append("카테고리 이름과 같음")
    return why


def main():
    # ① 카테고리 + 진열 순서
    groups = call("BKR0632", {})["allMenuList"]
    groups.sort(key=lambda g: int(g.get("menuCategorySeq") or 0))
    cat_names = [g["menuCategoryNm"] for g in groups]
    cats = [{"name": g["menuCategoryNm"], "parent": None, "ext_id": g.get("menuCategoryCd")}
            for g in groups]
    print("● 카테고리 %d개 (하위 0) — %s" % (len(cats), " · ".join(cat_names)))

    # ② 브랜드 공통 원산지 · 영양성분(중량) · 알레르기
    info = call("BKR0347", {})
    origin_note = "\n".join(
        "%s: %s" % (o.get("pattiDivNm", ""), (o.get("pattiNote") or "").strip())
        for o in info.get("originInfoList", []))
    # 키는 «띄어쓰기만 무시»한다 — 같은 글자를 같은 것으로 볼 뿐 유사매칭이 아니다
    # (공통표 «콰트로치즈 와퍼» ↔ 메뉴 «콰트로치즈와퍼»)
    key = lambda s: (s or "").replace(" ", "").replace("　", "").strip()   # noqa: E731
    weight_of, allergy_of = {}, {}
    for n in info.get("allNutrientList", []):
        w = (n.get("weight") or "").strip()
        if w and w != "0":
            # 공통표의 열 이름이 «중량(g/ml)» 이다 — 숫자만 남기면 음료(ml)를 g 으로 오독한다.
            # 열 이름을 그대로 붙여둔다(단위를 내가 정하지 않는다)
            weight_of[key(n["menuNm"])] = "중량(g/ml) %s" % w
    for a in info.get("allAllergyList", []):
        v = (a.get("allergyNm") or "").strip()
        if v:
            allergy_of[key(a["menuNm"])] = v
    print("● 공통표 — 원산지 %d줄 · 영양성분 %d개 · 알레르기 %d개"
          % (len(info.get("originInfoList", [])), len(weight_of), len(allergy_of)))

    # ③ 메뉴 — 이름으로 합친다(같은 이름에 menuCd 가 둘인 경우가 있다)
    order, by_name, dup_in_cat, name_codes = [], {}, [], {}
    for g in groups:
        cn = g["menuCategoryNm"]
        seen, pos = set(), 0
        for m in g.get("menuInfo", []):
            nm = (m.get("menuNm") or "").strip()
            cd = m.get("menuCd")
            if not nm:
                continue
            if cd in seen:                       # 같은 탭에 같은 메뉴가 두 번 진열
                dup_in_cat.append((cn, nm))
                continue
            seen.add(cd)
            name_codes.setdefault(nm, []).append((cd, cn))
            if nm not in by_name:
                order.append(nm)
                by_name[nm] = {
                    "name": nm, "price": None, "price_source": None, "price_note": None,
                    "compose_raw": (m.get("menuComponents") or "").strip() or None,
                    "weight_raw": weight_of.get(key(nm)),
                    "origin_raw": None,
                    "allergy_raw": allergy_of.get(key(nm)),
                    "detail_url": DETAIL_URL % cd if cd else None,
                    "image_url": m.get("menuImgPath") or None,
                    "ext_id": cd, "cats": []}
            it = by_name[nm]
            if it["compose_raw"] == nm:          # 구성이 이름과 똑같으면 구성이 아니다
                it["compose_raw"] = None
            it["cats"].append([cn, pos])
            pos += 1

    # ④ 가격 — 메뉴 하나씩 상세 API (`dineInprc` = 매장 판매가)
    codes = sorted({c for v in name_codes.values() for c, _ in v})
    print("● 가격 조회 %d건 (menuCd 기준)" % len(codes))
    price_of, failed = {}, []
    for i, cd in enumerate(codes, 1):
        try:
            b = call("BKR0634", {"menuCd": cd})
            p = (b.get("dineInprc") or "").strip()
            price_of[cd] = int(p) if p.isdigit() and int(p) > 0 else None
        except Exception as e:                   # noqa: BLE001
            failed.append((cd, str(e)[:60]))
            price_of[cd] = None
        if i % 40 == 0:
            print("   …%d/%d" % (i, len(codes)))
        time.sleep(0.25)

    # 같은 이름에 menuCd 가 둘인 경우가 있다(탭마다 코드도 값도 다르다).
    # ⛔ 고르지 않는다 — **화면에서 먼저 나온 자리**의 값을 쓰고, 나머지는 price_note 에 사실대로 적는다.
    price_conflict = []
    for nm, pairs in name_codes.items():
        first_cd, _ = pairs[0]
        by_name[nm]["price"] = price_of.get(first_cd)
        by_name[nm]["price_source"] = "official" if price_of.get(first_cd) else None
        extra = ["%s 탭 menuCd %s · %s원" % (cn, cd, price_of.get(cd))
                 for cd, cn in pairs[1:] if price_of.get(cd) != price_of.get(first_cd)]
        if extra:
            price_conflict.append((nm, price_of.get(first_cd), extra))
            by_name[nm]["price_note"] = "같은 이름이 다른 코드로도 진열됨 — " + " / ".join(extra)

    menus = [by_name[n] for n in order]

    # ⑤ 메뉴 아닌 것 검사 — **지우지 않고 출력만** 한다
    flagged = [(m["name"], looks_wrong(m["name"], cat_names)) for m in menus]
    flagged = [(n, w) for n, w in flagged if w]
    if flagged:
        print("\n⚠️ «메뉴 아님» 규칙에 걸린 %d개 — API `menuNm` 이라 **버리지 않았다**:" % len(flagged))
        for n, w in flagged:
            print("   %-34s %s" % (n, ",".join(w)))
    if dup_in_cat:
        print("\n⚠️ 같은 탭에 두 번 진열된 %d건 — 첫 자리만 남겼다:" % len(dup_in_cat))
        for cn, nm in dup_in_cat:
            print("   %s / %s" % (cn, nm))
    if price_conflict:
        print("\n⚠️ 같은 이름인데 menuCd·값이 둘인 %d건 — 화면에서 먼저 나온 자리를 price 로:"
              % len(price_conflict))
        for nm, first, extra in price_conflict:
            print("   %-28s %s원  (그 밖에 %s)" % (nm, first, " / ".join(extra)))
    if failed:
        print("\n🔴 가격 조회 실패 %d건: %s" % (len(failed), failed[:5]))

    doc = {"brand": BRAND, "slug": SLUG,
           "source": "%s (자체 API BKR0632/BKR0634/BKR0347)" % LIST_URL,
           "collected_at": COLLECTED_AT,
           "origin_note": origin_note or None,
           "cats": cats, "menus": menus}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))

    have = lambda k: sum(1 for m in menus if m.get(k))          # noqa: E731
    print("\n✅ %s" % OUT)
    print("   카테고리 %d개(하위 0) · 메뉴 %d개 · 가격 있는 것 %d개 · 구성 %d개 · 원산지 %s"
          % (len(cats), len(menus), have("price"), have("compose_raw"),
             "공통 %d줄" % len(info.get("originInfoList", []))))
    print("   중량 %d개 · 알레르기 %d개 · 연결 %d건"
          % (have("weight_raw"), have("allergy_raw"), sum(len(m["cats"]) for m in menus)))


if __name__ == "__main__":
    main()
