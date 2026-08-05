# -*- coding: utf-8 -*-
"""앱 검색 결과에서 '그 재료가 맞는' 상품만 골라 원/kg를 낸다.

왜 필요한가 — 검색 결과에는 엉뚱한 게 섞인다. 그냥 최저가를 집으면
그게 그 재료의 시세로 둔갑한다. 실제로 걸렸던 것들:
  연어  → 세네갈 손질갈치 / 코코넛치즈연어스틱
  계란  → 계란동그랑땡
  배추  → **양**배추      (부분문자열 함정)
  옥수수 → 옥수수**전분**
  차돌  → 오뚜기 컵밥(차돌강된장)
  두부  → 두부곤약면
그래서 ①이름에 재료가 있어야 하고 ②가공형은 빼고 ③품목별 금칙어로 한 번 더 거른다.
"""
import json, io, os, re

S = os.path.dirname(os.path.abspath(__file__))

# 생재료가 다른 물건으로 바뀐 형태 — 시세로 쓰면 안 된다.
# (검색어 자신에 들어있는 말은 자동으로 예외 처리한다. '쫄면'을 '면'으로 자르면 안 되니까)
BAD = ["동그랑땡", "후라이", "지단", "장조림", "볶음밥", "만두", "돈까스", "까스",
       "고로케", "크로켓", "튀김", "전골", "스프", "죽", "김밥",
       "샐러드", "샌드위치", "피클", "절임", "장아찌", "조림", "패티",
       "소스", "드레싱", "육수", "베이스", "시즈닝", "가루", "분말", "전분",
       "음료", "주스", "라떼", "시럽", "잼", "케이크", "쿠키", "칩",
       "베이글", "스틱", "곤약", "컵밥", "강된장", "캔", "볼", "너겟",
       "맛향", "향기름", "구이용양념", "과자", "무침", "유탕", "한과"]

# 앱 상품명이 우리 말과 다른 것 — 검색어를 늘려 잡는다
ALIAS = {"브로콜리": ["브로콜리", "브로컬리"], "옥수수": ["옥수수", "스위트콘"],
         "맛술": ["맛술", "미림", "미향"], "삼겹살": ["삼겹살", "삼겹"]}

# 생물로 잡을 재료 — 냉동/가공형을 뺀다
FRESH = {"대파", "당근", "양파", "양배추", "감자", "고구마", "오이", "배추", "무",
         "파프리카", "피망", "청양고추", "부추", "미나리", "상추", "깻잎", "시금치",
         "콩나물", "숙주", "애호박", "가지", "브로콜리", "마늘", "생강", "옥수수",
         "표고버섯", "새송이", "팽이버섯"}
FRESH_BAD = ["냉동", "슬라이스", "다이스", "분태", "건조", "페이스트", "퓨레", "채썰"]

# 품목별 금칙어 — 부분문자열/동음이의 함정 전용
NOT = {
    "배추": ["양배추", "얼갈이", "열무"],
    "무": ["단무지", "무말랭이", "무침", "무우말"],   # '무'는 워낙 흔해 별도 처리(아래 MIN_LEN)
    "치즈": ["치즈떡", "치즈볼", "치즈스틱", "치즈까스"],
    "새우": ["해물모둠", "해물모듬", "새우깡"],
    "부추": ["부추전"],
    "연어": ["연어스틱", "훈제"],
    "차돌": ["컵밥", "된장"],
    "두부": ["두부면", "곤약"],
    "모짜렐라": ["베이글", "볼"],
    "표고버섯": ["표고버섯캔"],
    "참깨": ["기름"],
    "옥수수": ["전분", "통조림"],
    "쌀": ["찹쌀", "흑미", "현미", "쌀떡", "쌀국수", "쌀과자"],
    "원두": ["PET", "아메리카노", "라떼", "240ml", "음료"],   # 원두커피'음료'가 섞인다
    "깻잎": ["무침", "장아찌"],
    "고구마": ["유탕", "고로케", "샐러드", "치즈", "말랭이"],
    "감자": ["고로케", "샐러드", "튀김", "칩"],
}

WT = re.compile(r"([\d.]+)\s*(Kg|kg|KG|g|G|L|l|ml|ML)\b")
MULT = re.compile(r"X\s*(\d+)\s*입")          # '(115g/EA) X 48입'


def pack_kg(name):
    m = WT.findall(name)
    if not m:
        return None
    v, u = m[-1]
    v, u = float(v), u.lower()
    if u in ("g", "ml"):
        v /= 1000.0
    elif u not in ("kg", "l"):
        return None
    mm = MULT.search(name)                    # 박스 단위 판매면 총량이 배수만큼 는다
    if mm:
        v *= int(mm.group(1))
    return v


def won(s):
    return int(re.sub(r"[^\d]", "", s))


def pick(kw, items):
    k = kw.replace(" ", "")
    keys = [x.replace(" ", "") for x in ALIAS.get(kw, [kw])]
    ok = []
    for it in items:
        if it["coupon"]:
            continue
        nm = it["name"].replace(" ", "")
        if not any(x in nm for x in keys):
            continue
        if any(b in nm for b in NOT.get(kw, [])):
            continue
        if any(b in nm for b in BAD if b not in k):     # 검색어 자신은 금칙어에서 제외
            continue
        if kw in FRESH and any(b in nm for b in FRESH_BAD):
            continue
        kg = pack_kg(it["name"])
        if not kg:
            continue
        ok.append((won(it["price"]) / kg, kg, it))
    ok.sort(key=lambda x: x[0])
    return ok


# 별칭으로 따로 검색한 것을 원래 재료로 합친다 (검색어 → 우리 재료)
FOLD = {"브로컬리": "브로콜리", "스위트콘": "옥수수", "미림": "맛술", "미향": "맛술",
        "생표고": "표고버섯", "깐마늘": "마늘", "삼겹": "삼겹살", "쌀 20kg": "쌀"}


def main():
    data = json.load(io.open(os.path.join(S, "app_prices.json"), encoding="utf-8"))
    # 별칭 검색 결과를 원래 재료 쪽으로 밀어넣는다
    merged = {}
    for r in data:
        key = FOLD.get(r["kw"], r["kw"])
        merged.setdefault(key, {"kw": key, "total": r["total"], "items": []})
        merged[key]["items"] += r["items"]
    data = list(merged.values())

    out = []
    for r in data:
        kw = r["kw"]
        ok = pick(kw, r["items"])
        if not ok:
            out.append({"kw": kw, "status": "후보없음", "total": r["total"],
                        "raw": [i["name"] for i in r["items"] if not i["coupon"]][:3]})
            continue
        unit, kg, it = ok[0]
        out.append({"kw": kw, "status": "OK", "total": r["total"],
                    "code": it["code"], "name": it["name"], "pack_kg": kg,
                    "price": won(it["price"]), "list": won(it["list"]),
                    "rate": it["rate"], "won_per_kg": round(unit), "cands": len(ok),
                    "alts": [x[2]["name"] for x in ok[1:4]]})
    io.open(os.path.join(S, "picked.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))

    okn = [o for o in out if o["status"] == "OK"]
    print("확정 %d종 / 후보없음 %d종\n" % (len(okn), len(out) - len(okn)))
    for o in okn:
        print("%-10s %-46s %9s원  %9s원/kg" % (
            o["kw"], o["name"][:46], f"{o['price']:,}", f"{o['won_per_kg']:,}"))
    print("\n[후보없음 — 검색결과 상위 3건]")
    for o in out:
        if o["status"] != "OK":
            print("  %-8s (총%s) %s" % (o["kw"], o["total"], " | ".join(n[:28] for n in o.get("raw", []))))


main()
