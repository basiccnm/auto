# -*- coding: utf-8 -*-
"""소매(쿠팡) 최저가를 재료 전체에 채운다. 2026-07-26 — 대표 방침 변경

대표 지시 (그대로)
  *"소매부터 다 채워 와 쿠팡으로 최저가로 이상한거 찾지 말고 그리고 DB싹넣어 최저가야
    소매 이름이랑 같은걸로 / 제품명을 이름에 넣지 마 용량이 나오면 용량 저장하고"*
  *"로켓 배송이 1순위고 / 로켓 배송 없으면 일단 그건 넘겨"*

규칙
  ① **로켓배송만** 채택. 로켓이 없으면 `skip` 으로 두고 넘어간다
  ② 그중 **가격 최저** — 용량 조건 없음, 상한 없음
     (집에서 1~2인분 쓰니 단가가 비싸도 적게 나가는 게 낫다)
  ③ 검색어는 **품목명만**. 재료명에 붙은 브랜드·제품명·용량은 뗀다
     "참마시 쏘드레 치킨양념소스 10kg" → "치킨양념소스"
  ④ 상품명에 용량이 있으면 저장, 없으면 비워 둔다(대표가 화면에서 채운다)
  ⑤ 결과는 `ingredient_retail` 에 status='pending' 으로 **즉시 저장**한다.
     관리자 화면이 실시간으로 읽어 대표가 통과시킨다.

🔴 사람이 확정한 것(`decided_at` 있음)은 건드리지 않는다.
🔴 먹는 게 아닌 것(포장재)은 소매가가 의미 없으니 건너뛴다.

    python scripts/retail_fill.py                 # 전체
    python scripts/retail_fill.py --budget=50      # API 50회까지
    python scripts/retail_fill.py --only=양파       # 이름에 포함된 것만
"""
import io
import json
import os
import re
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CACHE = os.path.join(BASE, "data", "research", "coupang_ing")
SLEEP = 2.0                  # 분당 30회. 쿠팡 API 정지되면 복구가 어렵다

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI   # noqa: E402
from mealkit_run import load_env  # noqa: E402

_UNIT = {"kg": 1000.0, "g": 1.0, "l": 1000.0, "ml": 1.0}   # 🔴 DB는 g으로만 저장한다
# ⚠️ 배수 표기를 반영한다("75g x 4" = 300g). 이걸 안 해서 식봄 캐시 3,260행이 틀렸다.
_MULT = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*xX×]\s*(\d+)", re.I)
_MULT2 = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*,?\s*(\d+)\s*(?:개입|개|입|팩|봉|매|장)", re.I)
_ONE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)(?![a-z가-힣])", re.I)
JUNK = re.compile(r"미니어처|장난감|DIY|테이블|포차|노점|인덕션|냄비|용기|그릇|받침|트레이|"
                  r"주방|식기|도마|장바구니|보관함|원줄|낚시|공예|만들기|"
                  # 🔴 화장품·잡화 (2026-07-26: '파우더' 검색에 화장품이 4종 붙었다
                  #    — 미팩토리 파우더 팩트 · 폴메디슨 비비드 프라이머 피니쉬 파우더)
                  r"팩트|쿠션|파운데이션|프라이머|피니쉬|립스틱|립밤|아이섀도|섀도|마스카라|"
                  r"아이라이너|컨실러|하이라이터|블러셔|단일\s*색상|색상[,)]|호수|"
                  r"클렌징|샴푸|바디워시|치약|세럼|토너|로션|크림팩|마스크팩|"
                  r"영양제|비타민제|유산균|정제|캡슐|타블렛|"
                  r"사료|간식용품|반려|강아지|고양이|배변", re.I)
# 🔴 쿠팡이 주는 categoryName 으로 먹는 것만 남긴다 — 이름으로 막는 건 끝이 없다.
#    '파우더' 검색에 화장품(미팩토리 파우더 팩트 · 폴메디슨 프라이머 · 이니스프리 노세범)이
#    계속 올라왔다(2026-07-26). 이름 필터를 세 번 고쳐도 새 브랜드가 또 나왔다.
#    실제 카테고리 분포: 식품 3407 · 로켓프레시 763 · 헬스/건강식품 254 · 뷰티 43 · 주방용품 35 …
FOOD_CATS = ("식품", "로켓프레시", "헬스/건강식품")


def is_food(p):
    """먹는 것인가. categoryName 이 비어 있으면 통과시킨다(옛 캐시에 없는 경우)."""
    cn = (p.get("categoryName") or "").strip()
    return (not cn) or cn in FOOD_CATS


# 마지막 토큰이 이런 일반명이면 그것만으로는 검색이 안 된다 → 앞 토큰을 붙인다
TAIL_GENERIC = ("분말", "가루", "소스", "양념", "세트", "믹스", "육수", "베이스", "파우더",
                "시즈닝", "오일", "기름", "장", "즙", "액", "정육", "생육", "믹")


def pack_g(name):
    n = (name or "").replace(",", "")
    for rx in (_MULT, _MULT2):
        m = rx.search(n)
        if m:
            return float(m.group(1)) * _UNIT[m.group(2).lower()] * int(m.group(3))
    m = _ONE.search(n)
    if m:
        return float(m.group(1)) * _UNIT[m.group(2).lower()]
    return None


# 재료명에서 품목명을 못 뽑는 예외만 손으로 적는다.
#  "샐러드용 채소"→"채소" 처럼 너무 일반적이거나, "김밥용 세트"→"세트" 처럼 뜻이 사라지는 경우.
KWMAP = {}
if os.path.exists(CI.KWMAP_PATH):
    KWMAP = {k: v for k, v in json.load(io.open(CI.KWMAP_PATH, encoding="utf-8")).items()
             if not k.startswith("_")}


def keyword(name):
    """재료명에서 브랜드·제품명·용량을 떼고 **품목명만** 남긴다."""
    if name in KWMAP:
        return KWMAP[name]
    s = re.sub(r"\([^)]*\)", " ", name or "")
    s = re.sub(r"\d+(\.\d+)?\s*(kg|g|l|ml|개입|개|매|장|봉|팩|인분)", " ", s, flags=re.I)
    s = re.sub(r"[·/]", " ", s)
    toks = [t for t in s.split() if len(t) >= 2]
    if not toks:
        return (name or "").strip()
    last = toks[-1]
    if last in TAIL_GENERIC and len(toks) >= 2:
        return "%s %s" % (toks[-2], last)
    return last


def cores(kw):
    """상품명 검증용 핵심어 — 검색어의 각 토큰이 상품명에 들어있어야 한다."""
    return [t for t in kw.split() if len(t) >= 2]


def kw_list(name):
    """검색어를 넓은 순서로 여러 개 만든다 — 첫 번째에서 로켓이 안 나오면 다음으로 넘어간다.

    🔴 왜 필요한가: 품목명 하나로만 찾으니 105종이 "로켓 없음"으로 넘어갔다(2026-07-26).
       `순대 볶음양념` 은 두 단어가 다 들어간 상품명이 거의 없고,
       `단과자생지` 는 쿠팡에 그런 말로 파는 상품이 없다(실제로는 "단과자빵 생지").
       그래서 좁은 것 → 넓은 것 순으로 2~3번 찾는다.
    """
    out = [keyword(name)]
    toks = keyword(name).split()
    if len(toks) > 1:
        out.append(toks[-1])          # 마지막 토큰만 (순대 볶음양념 → 볶음양념)
        out.append(toks[0])           # 첫 토큰만  (순대 볶음양념 → 순대)
    # 재료명에서 용량·괄호만 뗀 것 — 브랜드가 남지만 그 브랜드 상품이 있으면 정확히 걸린다
    full = re.sub(r"\([^)]*\)", " ", name or "")
    full = re.sub(r"\d+(\.\d+)?\s*(kg|g|l|ml|개입|개|매|장|봉|팩|인분)", " ", full, flags=re.I)
    full = re.sub(r"\s+", " ", full).strip()
    if full and full not in out:
        out.append(full)
    return list(dict.fromkeys(x for x in out if x))


def cpath(kw):
    return os.path.join(CACHE, re.sub(r"[^0-9A-Za-z가-힣]+", "_", kw)[:60] + ".json")


def main():
    budget = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--budget=")), 400)
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")
    if not ak:
        print("❌ .env 에 COUPANG_ACCESS_KEY 가 없다")
        return 1

    retry = "--retry" in sys.argv     # 'skip'(로켓 없음)만 다시 찾는다
    keep = {r[0] for r in c.execute(
        "SELECT ingredient_key FROM ingredient_retail WHERE decided_at IS NOT NULL")}
    if not retry:
        keep |= {r[0] for r in c.execute(
            "SELECT ingredient_key FROM ingredient_retail WHERE status='pending'")}
    else:
        skipped = {r[0] for r in c.execute(
            "SELECT ingredient_key FROM ingredient_retail WHERE status='skip'")}
    # 🔴 **레시피가 쓰는 재료도 대상이다** (2026-08-03).
    #    전에는 `menu_ingredients` 만 봐서 «메뉴에 안 쓰이는» 재료 200여 종이 통째로 빠졌다.
    #    우리의식탁 레시피 매칭 결과(`ing_map_auto.json`)를 함께 본다.
    import collections
    rec = collections.Counter()
    try:
        _m = json.load(io.open(os.path.join(BASE, "data/wtable/ing_map_auto.json"), encoding="utf-8"))
        for _n, _v in _m.items():
            if _v.get("key"):
                rec[_v["key"]] += _v.get("count", 0)
    except Exception:
        pass
    rows = [dict(r) for r in c.execute("""
        SELECT i.ingredient_key k, i.name,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) uses
        FROM ingredients i""")]
    for r in rows:
        r["rec"] = rec.get(r["k"], 0)
    rows = [r for r in rows if r["uses"] or r["rec"]]
    rows.sort(key=lambda r: -(r["uses"] * 100 + r["rec"]))     # 많이 쓰는 것부터
    todo = [r for r in rows if r["k"] not in keep
            and not CI.NOT_FOOD.search(r["name"] or "")]
    if retry:
        todo = [r for r in todo if r["k"] in skipped]
    if only:
        todo = [r for r in todo if only in r["name"]]
    print("전체 %d종 · 확정 유지 %d종 · 먹는 게 아닌 것 제외 · 대상 %d종"
          % (len(rows), len(keep), len(todo)))
    print("기준: 로켓배송만 · 가격 최저 · 용량 무관 · 로켓 없으면 skip")
    print("", flush=True)

    cur = c.cursor()
    used = ok = skip = 0
    for r in todo:
        if used >= budget:
            print("예산 %d회 소진 — 중단" % budget, flush=True)
            break
        # 검색어를 넓은 순서로 시도한다. 로켓 후보가 나오면 거기서 멈춘다.
        cands, used_kw = [], None
        for kw in (kw_list(r["name"]) if retry else [keyword(r["name"])]):
            items = None
            fp = cpath(kw)
            if os.path.exists(fp):
                try:
                    items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
                except Exception:
                    items = None
            if items is None:
                if used >= budget:
                    break
                try:
                    d = CI.api_search(kw, ak, sk)
                except Exception as e:
                    print("  ! %-22s 호출실패 %s" % (r["name"][:22], str(e)[:40]), flush=True)
                    used += 1
                    time.sleep(SLEEP)
                    continue
                if d.get("rCode") not in (0, "0"):
                    print("  !! rCode=%s — 즉시 중단(쿠팡 한도 보호)" % d.get("rCode"), flush=True)
                    return 1
                items = (d.get("data") or {}).get("productData") or []
                io.open(fp, "w", encoding="utf-8").write(
                    json.dumps({"keyword": kw, "items": items}, ensure_ascii=False))
                used += 1
                time.sleep(SLEEP)

            cw = cores(kw)
            for p in items:
                pn, price = p.get("productName") or "", p.get("productPrice")
                if not price or not p.get("isRocket"):    # ① 로켓만
                    continue
                if not is_food(p) or JUNK.search(pn):     # 먹는 것만
                    continue
                flat = re.sub(r"\s+", "", pn)
                # 검색어가 여러 토큰이면 **하나 이상** 맞으면 후보로 올린다.
                #  다 맞아야 한다고 하면 후보가 0이 되어 화면에 아무것도 안 뜬다(대표 "나오게 해").
                #  틀린 건 화면에서 반려하면 되니, 우선 올리는 쪽이 맞다.
                if not any(w in flat for w in cw):
                    continue
                if [b for b in CI.PROCESSED if re.search(b, pn) and not re.search(b, r["name"])]:
                    continue
                # 토큰이 다 맞으면 우선순위를 높인다(정확도 순)
                exact = 0 if all(w in flat for w in cw) else 1
                cands.append((exact, 1 if CI.PREMIUM.search(pn) else 0, price, p))
            if cands:
                used_kw = kw
                break
        # 정확도 → 프리미엄 후순위 → ② 가격 최저
        cands.sort(key=lambda x: (x[0], x[1], x[2]))

        if not cands:
            cur.execute("""INSERT OR REPLACE INTO ingredient_retail
                (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
                VALUES(?,NULL,?,NULL,NULL,0,NULL,NULL,'skip',NULL)""", (r["k"], "로켓배송 없음: " + kw))
            c.commit()
            skip += 1
            print("  ⏭ %-22s (%s) 로켓 없음" % (r["name"][:22], kw), flush=True)
            continue

        _, _, price, p = cands[0]
        gv = pack_g(p["productName"])
        cur.execute("""INSERT OR REPLACE INTO ingredient_retail
            (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
            VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                    (r["k"], p.get("productId"), p["productName"], price, gv,
                     p.get("productImage"), p.get("productUrl")))
        c.commit()
        ok += 1
        print("  ✅ %-22s %8s원 %7s  %s" % (
            r["name"][:22], format(price, ","),
            ("%gg" % gv) if gv else "용량?", p["productName"][:40]), flush=True)

    print("", flush=True)
    print("끝. 채움 %d종 · 로켓없어 넘김 %d종 · API %d회" % (ok, skip, used), flush=True)
    c.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
