# -*- coding: utf-8 -*-
"""build.py — 식자재 폭등 경보기. 하루 한 번 돌면 사이트가 갱신된다.

무엇을 하나
    ① KAMIS 도매시세를 오늘·전주 두 날짜로 받아 **상승률**을 낸다
    ② 20% 이상 오른 품목을 골라
    ③ 쿠팡에서 그 품목의 **대용량·업소용·냉동 대체재**를 찾아
    ④ site/index.html 과 site/data.json 을 새로 쓴다

왜 이 순서인가
    자영업자가 아픈 건 "오늘 뭐가 올랐나"가 아니라 **"그래서 뭘 대신 사나"** 다.
    시세만 보여주는 사이트는 이미 많다. 대체재를 같이 붙이는 게 이 물건의 값어치다.

돈이 어디서 나오나
    쿠팡 파트너스 제휴 수수료. 검색 결과의 productUrl 이 **이미 제휴링크**라
    (link.coupang.com/re/AFFSDP?lptag=...) 별도 deeplink 변환이 필요 없다.
    ⚠️ 평범한 상품 주소를 그냥 걸면 수수료가 0 이다. 반드시 검색이 준 URL 을 쓸 것.

주의
    - 제목·설명·도메인에 「쿠팡」·「로켓배송」을 쓰지 않는다 (상표 제한).
      본문의 사실 서술과 파트너스 고지문은 가능하다.
    - KAMIS 는 주말·공휴일 데이터가 없다. 없으면 하루씩 뒤로 물러 찾는다.
"""
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from publicdata import catalog, kamis          # noqa: E402
from coupang import coupang_api as cp          # noqa: E402

SITE = os.path.join(ROOT, "site")
SURGE_PCT = 20.0          # 이 이상 오르면 경보
MAX_ITEMS = 12            # 페이지에 올릴 품목 수
CATS = [kamis.CAT_GRAIN, kamis.CAT_VEGETABLE, kamis.CAT_SPECIAL, kamis.CAT_FRUIT]

NAME = {(it[3], it[4]): it[1] for it in catalog.KAMIS_ITEMS}

# 품목별 (검색어, 상품명에 반드시 들어가야 할 낱말).
#
# ⚠️ 검색 결과를 그대로 믿으면 안 된다 (2026-08-02 실측 사고).
#    「청양고추 냉동 업소용」 → 잡채말이어묵 · 콘소메맛 돼지튀김
#    「냉동 시금치 업소용」  → 시금치 **씨앗** 30g · 다진시금치 90g
#    「쌈채소 대용량」       → 값이 오른 **그 생물 상추** 자체
#    쿠팡 검색은 낱말이 조금만 겹쳐도 물어온다. 아래 세 관문으로 거른다.
#    셋째 칸은 **그 품목에서만 막을 낱말**이다.
#    예: 상추 검색에 「궁채·산상추」(상추 **줄기** 장아찌)가 딸려온다. 이름에 상추가 들어가지만
#        쌈용 상추 대신 쓸 물건이 아니다. 아예 다른 반찬이다.
# 🔴 이 표는 **기획(제미나이)이 정한다.** 개발자가 손으로 채우지 말 것.
#    처음엔 내가 추측으로 채웠다가 통째로 틀렸다 —
#    풋고추에 청양고추(다른 재료), 알배기배추에 포기김치(그 배추로 담그는 김치가 아님),
#    상추에 궁채장아찌(상추 «줄기» 절임). 대표가 눈으로 보고 전부 잡아냈다.
#    회신11 에서 기획이 **주방에서 실제로 호환되는 것만** 남겼고, 나머지는 NONE 이다.
#    NONE 은 억지로 채우지 않는다. 없는 걸 파느니 그 줄을 빼는 게 낫다.
ALT_HINT = {
    "시금치":      ("냉동 시금치 업소용", "시금치", ()),
    "얼갈이배추":   ("냉동 단배추 업소용", "배추", ()),
    "대파":        ("냉동 썰은 대파 업소용", "대파", ()),
    "양파":        ("냉동 다진 양파 업소용", "양파", ()),
    "마늘":        ("냉동 다진 마늘 업소용", "마늘", ()),
    "무":          ("무말랭이 대용량", "무", ()),
    "당근(국산)":   ("냉동 당근 업소용", "당근", ()),
    "감자(수미)":   ("냉동 감자 업소용", "감자", ()),
}

# 대체재가 «없다» 고 기획이 판정한 품목. 검색하지 않는다.
# 쌈·겉절이처럼 **생물이라야 의미가 있는** 재료들이다.
NO_SUBSTITUTE = ("풋고추", "깻잎", "열무", "알배기배추", "상추(적)", "상추(청)", "배추")

# ── 검수 룰 (회신11 확정) ────────────────────────────────────
# 룰1. 이 중 하나는 반드시 상품명에 있어야 한다. 없으면 생물이라는 뜻이다.
FORM = ("냉동", "건조", "말랭이", "다진", "썰은", "깐", "페이스트", "분말",
        "플레이크", "대용량", "업소용")

# 룰2. 이게 있으면 생물이라 버린다.
#      ⚠ 기획은 「국내산(단독 표기 시)」도 넣으라 했지만 코드로 «단독» 판정이 안 된다.
#        국내산은 좋은 냉동 대용량 상품에도 거의 항상 붙는다. 넣으면 멀쩡한 걸 다 버린다.
#        → 뺐다. 룰1(가공 형태 필수)이 생물을 이미 걸러낸다.
FRESH = ("산지직송", "당일수확", "햇")

# 먹는 물건이 아닌 것. 룰과 별개로 늘 버린다.
BAN = ("씨앗", "종자", "모종", "묘목", "비료", "영양제", "화분", "재배", "키우기",
       "즙", "엑기스", "추출", "티백", "사료", "세제")

MIN_G = 1000        # 용량을 읽을 수 있을 때의 하한. 업소에서 쓰려면 최소 1kg


def latest_with_data(cats, cls, start, back=7):
    """데이터가 있는 가장 가까운 날짜와 그 값. 주말·공휴일은 비어 있다."""
    for i in range(back):
        d = start - datetime.timedelta(days=i)
        got = kamis.fetch_many(cats, cls, d.strftime("%Y-%m-%d"))
        if any(got.get(c) for c in cats):
            return d, got
    return start, {}


def surges(today=None):
    today = today or datetime.date.today()
    d_now, now = latest_with_data(CATS, kamis.WHOLESALE, today)
    d_old, old = latest_with_data(CATS, kamis.WHOLESALE, d_now - datetime.timedelta(days=7))

    rows = []
    for cat in CATS:
        a, b = now.get(cat, {}), old.get(cat, {})
        for key, price in a.items():
            was = b.get(key)
            if not was or not price:
                continue
            pct = (price - was) / was * 100
            if pct < SURGE_PCT:
                continue
            name = NAME.get(key)
            if not name:
                continue          # 이름을 모르는 코드는 내보내지 않는다
            rows.append({"name": name, "was": was, "now": price, "pct": round(pct, 1)})
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return d_old, d_now, rows[:MAX_ITEMS]


def _core(name):
    """품목명에서 상품명에 반드시 있어야 할 낱말. 「상추(적)」 → 「상추」."""
    return name.split("(")[0].strip()


def keep(title, core, extra_ban=()):
    """대체재로 내놓아도 되는 상품인가. 검수 룰은 회신11 에서 기획이 정한 것이다.

    ① 그 품목 얘기가 맞나 — 상품명에 핵심 낱말이 있어야 한다
                           (「청양고추…」 검색에 잡채말이어묵이 딸려왔다)
    ② 먹는 물건이 맞나    — 씨앗·비료·사료를 거른다
                           (「냉동 시금치」 검색 1위가 시금치 **씨앗 30g** 이었다)
    ③ 룰1 가공 형태 필수  — 냉동·건조·다진·썰은·깐·분말·대용량·업소용 중 하나
    ④ 룰2 생물 배제       — 산지직송·당일수확·햇 이 붙으면 생물이다
    ⑤ 룰3 중량 미기재     — **버리지 않는다.** 가격 비교만 생략한다.
                           쿠팡은 중량을 이름에 안 적는 일이 흔하다. 그걸 다 버리면
                           진짜 대체재가 전멸한다(시금치 0건 사고). 대신 값 비교를 안 한다.
    """
    t = title or ""
    if core not in t:
        return False
    if any(b in t for b in BAN) or any(b in t for b in extra_ban):
        return False
    if any(f in t for f in FRESH):
        return False
    if not any(f in t for f in FORM):
        return False

    grams, unit = cp.parse_pack(t)
    if unit in ("g", "ml") and grams:
        return grams >= MIN_G
    return True        # 용량 미상 — 통과시키고 가격 비교만 생략한다


def alternatives(rows):
    """폭등 품목마다 대용량·냉동 대체재를 붙인다.

    ⚠️ 검색은 **한도껏(10건)** 받아서 걸러낸 뒤 3건만 쓴다.
       limit=3 으로 받으면 그 3건이 전부 쓰레기일 때 손쓸 수가 없다.
       🔴 limit 최대는 10 이다. 20 을 주면 rCode=400 으로 **0건**이 온다
          (모듈 주석에 이미 적혀 있는데 안 읽고 20 을 넣어 전 품목이 0건이 됐다, 2026-08-02).
    """
    ak, sk = cp.keys(os.path.join(ROOT, ".env"))
    for r in rows:
        # 기획이 «대체 없음» 이라고 못 박은 품목은 검색조차 하지 않는다.
        # 쌈·겉절이처럼 생물이라야 의미가 있는 재료들이다. 억지로 붙이면 거짓말이 된다.
        if r["name"] in NO_SUBSTITUTE:
            r["keyword"] = None
            r["alts"] = []
            continue

        core_default = _core(r["name"])
        kw, core, extra_ban = ALT_HINT.get(
            r["name"], (f"{core_default} 대용량 업소용", core_default, ()))
        r["keyword"] = kw
        try:
            found = cp.items(cp.search(kw, ak, sk, limit=cp.LIMIT))
        except Exception as e:                                  # noqa: BLE001
            print(f"  검색 실패 {kw}: {e}")
            found = []

        good, seen_ids = [], set()
        for it in found:
            title = it.get("productName", "")
            if not keep(title, core, extra_ban):
                continue
            pid = str(it.get("productId", ""))
            if pid in seen_ids:                # 같은 상품의 옵션 중복 제거
                continue
            seen_ids.add(pid)
            good.append({
                "name": title,
                "price": it.get("productPrice", 0),
                "image": it.get("productImage", ""),
                "url": it.get("productUrl", ""),      # ← 이미 제휴링크
            })
            if len(good) == 3:
                break
        r["alts"] = good
        if not good:
            print(f"  ⚠ {r['name']}: 쓸 만한 대체재 없음 ({len(found)}건 중 0건 통과)")
    # 🔴 대체재가 없어도 **줄을 지우지 않는다** (회신11 확정).
    #    이 페이지는 상품 팔이가 아니라 «자영업자 시세 대시보드» 다.
    #    깻잎·상추 폭등은 식당 사장이 가장 민감해하는 정보라, 팔 게 없어도 보여줘야
    #    신뢰가 쌓이고 내일 다시 들어온다. 대신 링크 자리에 «가공 대체 불가» 라고 밝힌다.
    return rows


# 시세와 상관없이 1년 내내 쓰는 것들. 폭등 품목이 전부 «대체 불가» 인 날의 수익원이다.
ALWAYS = (
    ("냉동 다진 마늘 업소용", "마늘"),
    ("깐 양파 업소용", "양파"),
    ("냉동 썰은 대파 업소용", "대파"),
    ("냉동 깍둑 감자 업소용", "감자"),
)


def always_on():
    """상시 노출 섹션 — 「주방 인건비 절감템」. 품목당 1개만 뽑는다."""
    ak, sk = cp.keys(os.path.join(ROOT, ".env"))
    out = []
    for kw, core in ALWAYS:
        try:
            found = cp.items(cp.search(kw, ak, sk, limit=cp.LIMIT))
        except Exception as e:                                  # noqa: BLE001
            print(f"  상시 검색 실패 {kw}: {e}")
            continue
        for it in found:
            t = it.get("productName", "")
            if not keep(t, core):
                continue
            out.append({"name": t, "price": it.get("productPrice", 0),
                        "image": it.get("productImage", ""), "url": it.get("productUrl", "")})
            break
    return out


def main():
    d_old, d_now, rows = surges()
    if not rows:
        print("폭등 품목 없음 — 페이지를 건드리지 않는다")
        return 0

    rows = alternatives(rows)
    data = {
        "base_date": d_old.isoformat(),
        "date": d_now.isoformat(),
        "threshold": SURGE_PCT,
        "items": rows,
        # 폭등 품목이 전부 «대체 불가» 인 주도 있다. 그날도 수익 기회를 버리지 않는다.
        # 시세와 무관하게 식당이 1년 내내 쓰는 것들을 아래에 상시로 깔아둔다 (회신11 확정).
        "always": always_on(),
    }
    os.makedirs(SITE, exist_ok=True)
    with io.open(os.path.join(SITE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    from render import render                                   # noqa: PLC0415
    with io.open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(render(data))

    print(f"{d_old} → {d_now}  폭등 {len(rows)}건")
    for r in rows:
        print(f"  {r['pct']:+6.1f}%  {r['name']:<12} 대체 {len(r['alts'])}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
