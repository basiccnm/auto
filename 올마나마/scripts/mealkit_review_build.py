# -*- coding: utf-8 -*-
"""밀키트 검수용 후보 목록 생성 (API 호출 0 — 기존 쿠팡 캐시만 사용). 2026-07-25

자동매칭이 50% 중복(한 상품이 최대 14개 메뉴에 붙음)이라 폐기하고,
**메뉴 하나씩 사람이 고르는** 방식으로 전환한다. 이 스크립트는 그 후보를 만든다.

메뉴별로 캐시된 검색결과에서 비조리·이상가격을 걸러 상위 후보 N개를 뽑아
_review/mealkit_review.json 으로 저장한다. 검수 화면(mealkit_review.html)이 이걸 읽는다.
"""
import json, io, os, re, sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "data", "research")
CACHE = os.path.join(RES, "coupang")
PLAN = os.path.join(RES, "mealkit_kw_plan_v2.json")
OUT = os.path.join(RES, "mealkit_review.json")
TOPN = 6

# mealkit_run.py 의 EXCLUDE 와 같은 취지(비조리·굿즈·원재료 제외)
EXCLUDE = re.compile(
    r"(교환권|상품권|기프트|기프티|쿠폰|바우처|"
    r"소스\b|양념장|시즈닝|분말|파우더|다시다|"
    r"과자|스낵|칩스|젤리|사탕|캔디|초콜릿|"
    r"음료|콜라|사이다|주스|쥬스|커피믹스|캡슐커피|"
    r"사료|간식캔|장난감|굿즈|티셔츠|의류|양말|"
    r"강아지|반려견|반려묘|애견|애묘|반려동물|고양이|펫\b|"
    r"영양제|비타민|유산균|콜라겐|프로틴바|생수|"
    r"식용유|참기름|들기름|올리브유|설탕|소금\b|밀가루|전분|"
    r"세제|비누|섬유유연제|밀폐용기|그릇|접시|수세미|"
    # 2026-07-25 검수화면 1차 확인에서 섞여 들어온 것들
    r"포카칩|포테토칩|감자칩|새우칩|프링글스|도리토스|"      # 스낵(치킨맛 과자 등)
    r"금액권|상품권|기프티콘|교환권|이용권|"                  # 금액권
    r"소프트콘|아이스크림|콘\)|빙수|"                          # 디저트
    r"Wipe-Clean|스티커|색칠|퍼즐|블록|도서|책\b|문제집|"      # 완전 무관 상품
    r"비빔장|쌈장|고추장|간장\b|식초|드레싱\b|"                 # 조미료 단품
    # 비식품 — 검색어가 짧으면 쿠팡이 엉뚱한 카테고리를 섞어준다(욕실화·훈연칩 등)
    r"욕실화|슬리퍼|실내화|장갑|수건|타올|매트|쿠션|베개|이불|"
    r"훈연칩|우드칩|톱밥|스모크칩|숯\b|화로|그릴\b|불판|후라이팬|냄비|"
    r"충전기|케이블|이어폰|마우스|키보드|필름|케이스|거치대|"
    r"화장품|샴푸|린스|바디워시|치약|칫솔|마스크팩|기저귀|물티슈)")


def cpath(kw):
    safe = re.sub(r'[\\/:*?"<>|]', "_", kw)
    return os.path.join(CACHE, safe + ".json")


# ── 경쟁 브랜드 제외 ────────────────────────────────────────────
#  BBQ 메뉴에 굽네·BHC 제품이 뜨면 안 된다(2026-07-25 지적).
#  DB의 브랜드명에서 접미사를 떼고 핵심어를 만들어, 내 브랜드가 아닌 것이 상품명에 있으면 버린다.
_SUFFIX = re.compile(r"(치킨|피자|버거|분식|떡볶이|샐러드|김밥|설렁탕|국밥|본가|프랜차이즈)$")


def brand_core(b):
    return _SUFFIX.sub("", (b or "").replace(" ", ""))


def load_brand_cores():
    db = os.path.join(BASE, "data", "eolmanama.db")
    con = sqlite3.connect(db)
    cores = set()
    for (nm,) in con.execute("SELECT DISTINCT name FROM brands"):
        c = brand_core(nm)
        if len(c) >= 2:
            cores.add(c)
    con.close()
    return cores


def main():
    plan = json.load(io.open(PLAN, encoding="utf-8"))
    brand_cores = load_brand_cores()
    out = []
    n_have = n_none = 0
    n_rival = 0
    for p in plan:
        if p.get("skip"):
            continue
        anchors = p.get("anchors") or []
        own = brand_core(p.get("brand"))
        rivals = {c for c in brand_cores if c != own}
        seen_ids = set()
        cands = []
        for kw in p["keywords"]:
            fp = cpath(kw)
            if not os.path.exists(fp):
                continue
            try:
                d = json.load(io.open(fp, encoding="utf-8"))
            except Exception:
                continue
            for it in d.get("items", []):
                nm = it.get("name") or ""
                pid = it.get("id")
                if not nm or not it.get("url") or not it.get("image"):
                    continue
                if pid in seen_ids or EXCLUDE.search(nm):
                    continue
                # 경쟁 프랜차이즈 제품 배제 (내 브랜드 제품은 통과 = 정품)
                nmn = nm.replace(" ", "")
                if any(rv in nmn for rv in rivals):
                    n_rival += 1
                    continue
                try:
                    pr = float(it.get("price"))
                except (TypeError, ValueError):
                    continue
                if pr <= 0 or pr > 150000:
                    continue
                seen_ids.add(pid)
                # 앵커(카테고리 핵심어) 일치 여부로 정렬 우선순위
                anchored = 1 if (anchors and any(a in nm for a in anchors)) else 0
                cands.append({
                    "id": pid, "name": nm, "price": pr,
                    "rocket": bool(it.get("rocket")),
                    "image": it.get("image"), "url": it.get("url"),
                    "kw": kw, "anchored": anchored,
                })
        cands.sort(key=lambda c: (-c["anchored"], -int(c["rocket"]), c["price"]))
        cands = cands[:TOPN]
        if cands:
            n_have += 1
        else:
            n_none += 1
        out.append({
            "menu_id": p["menu_id"], "brand": p.get("brand"), "menu": p.get("menu"),
            "category": p.get("category"), "candidates": cands,
        })
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("검수 대상 %d개 메뉴 (후보 있음 %d · 없음 %d) · 경쟁브랜드 제외 %d건"
          % (len(out), n_have, n_none, n_rival))
    print("→ %s" % OUT)


main()
