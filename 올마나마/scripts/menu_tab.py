# -*- coding: utf-8 -*-
"""메뉴판 **탭 이름을 브랜드마다 똑같이** 맞춘다 — 단일 출처. 2026-07-28
(대표 지시: *"각 브랜드별 탭메뉴 동일하게 적용해"*)

왜 필요한가
----------
탭을 «브랜드가 준 이름» 그대로 쓰니 이렇게 됐다:

    BBQ        사이드 / 치킨 / 음료 / 세트 / 반마리 / 피자 / 소스 / 기타
    bhc        치킨 · BHC시그니처 / 사이드 · 뿌링클유니버스 / BHC시그니처 · 콜팝 …
    롯데리아      추천메뉴 / 디저트 / 아이스샷 / 버거 / 음료 / 치킨
    나머지 34곳   **전부 「기타」** (1,129줄 중 834줄이 카테고리 없음)

브랜드마다 탭이 다르면 사용자가 페이지를 옮길 때마다 다시 읽어야 한다.
「뿌링클유니버스」 같은 브랜드 내부 용어는 남이 알 수 없다.

규칙
----
· **표준 탭 9개**로 통일한다 (아래 `TABS` 순서 그대로 화면에 깔린다)
· 브랜드가 준 카테고리를 **먼저** 보고, 없거나 못 알아보면 **메뉴명**으로 판정한다
· 「추천메뉴」·「BEST」 처럼 **중복 진열 탭은 쓰지 않는다** — 같은 메뉴가 두 번 나온다
· ⛔ 확실하지 않으면 「기타」로 둔다. 억지로 밀어 넣으면 엉뚱한 탭에서 메뉴를 찾게 된다
"""
import re

# 화면에 깔리는 순서. 왼쪽이 그 가게의 «주력» 이다.
TABS = ["치킨", "피자", "버거", "밥·면", "분식", "사이드", "디저트", "음료", "세트", "기타"]

# 브랜드가 준 카테고리 → 표준 탭 (그대로 못 쓰는 말들)
_ALIAS = {
    "추천메뉴": None, "베스트": None, "best": None, "인기": None, "신메뉴": None,
    "new": None, "전체": None, "이벤트": None,      # None = 이름으로 다시 판정
    "아이스샷": "음료", "커피": "음료", "음료수": "음료", "beverage": "음료",
    "디저트": "디저트", "dessert": "디저트", "빙수": "디저트", "아이스크림": "디저트",
    "사이드": "사이드", "side": "사이드", "사이드메뉴": "사이드", "곁들임": "사이드",
    "버거": "버거", "burger": "버거", "햄버거": "버거",
    "치킨": "치킨", "chicken": "치킨", "닭": "치킨", "반마리": "치킨", "한마리": "치킨",
    "피자": "피자", "pizza": "피자",
    "세트": "세트", "콤보": "세트", "combo": "세트",
    "소스": "사이드", "시즈닝": "사이드", "무": "사이드",
    "밥": "밥·면", "면": "밥·면", "덮밥": "밥·면", "국물": "밥·면", "탕": "밥·면",
    "떡볶이": "분식", "분식": "분식", "김밥": "분식", "튀김": "분식", "순대": "분식",
}

# 메뉴 **이름**으로 판정 — 위에서 못 정했을 때. 위에서부터 먼저 맞는 것을 쓴다.
_BYNAME = [
    ("세트", r"(세트|콤보|패키지|\bSET\b|1\+1|2인|3인|4인|파티)"),
    ("음료", r"(콜라|사이다|음료|주스|아메리카노|라떼|커피|에이드|스무디|밀크|티\b|차\b|"
             r"제로|펩시|스프라이트|환타|맥주|생맥|소주|하이볼|샷|"
             # 브랜드 고유 음료명 — 「음료」라는 글자가 없다
             r"미닛메이드|킹플로트|킹퓨전|미네랄워터|순수\(|플로트)"),
    # 🔴 «피자» 를 «디저트» 보다 **먼저** 본다 (2026-07-28).
    #    「몬스터 레드콘 피자」가 «콘»(아이스크림 콘) 에 걸려 디저트로 갔다.
    #    이름에 «피자» 가 있으면 그건 피자다 — 더 구체적인 신호가 이긴다.
    ("피자", r"(피자|PIZZA|칼조네|포카치아)"),
    ("디저트", r"(빙수|아이스크림|케이크|도넛|와플|츄러스|쿠키|마카롱|파이|타르트|"
              r"에그타르트|푸딩|젤라또|소프트콘|디저트|선데|아포가토)"),
    # 🔴 「버거」라는 글자가 안 들어간 햄버거가 많다 (2026-07-28 버거킹에서 34개가 「기타」로 감).
    #    와퍼·맥시멈·크리스퍼·스테이크버거 계열은 브랜드 고유명이라 글자만 보면 못 잡는다.
    ("버거", r"(버거|버-거|BURGER|샌드위치|랩\b|토스트|와퍼|WHOPPER|맥시멈|주니어|"
             r"크리스퍼|치즈스틱버거|원파운더|빅맥|맥치킨|맥스파이시|불고기버거|치즈버거|"
             r"오리지널스)"),
    ("치킨", r"(치킨|닭|윙|봉|다리|순살|후라이드|양념|반마리|한마리|콤보윙|텐더|넉겟|너겟|"
             r"바삭킹|너겟킹|크리스퍼\s*텐더)"),
    ("분식", r"(떡볶이|떡순|김밥|순대|튀김|어묵|오뎅|핫도그|만두|라볶이|쫄면|국수)"),
    ("밥·면", r"(밥\b|덮밥|비빔|볶음밥|정식|국밥|찌개|탕\b|전골|죽\b|면\b|우동|짜장|짬뽕|"
             r"파스타|라면|칼국수|쌀국수|도시락|초밥|회\b|돈까스|카레)"),
    ("사이드", r"(감자|프라이|치즈볼|치즈스틱|샐러드|무\b|피클|소스|시즈닝|콘슬로|"
              r"너비아니|웨지|스틱|볼\b|사이드|추가|토핑|"
              # 브랜드 고유 사이드 — 어니언링·딥소스·바삭킹(치킨 조각) 등
              r"어니언링|딥\s|체다치즈|코울슬로|콘샐러드|해시브라운)"),
]
_BYNAME = [(t, re.compile(p, re.I)) for t, p in _BYNAME]

# 브랜드 업종(categories.name) → 이름으로 못 정했을 때의 기본 탭.
# ⛔ **주력이 뚜렷한 업종만** 넣는다. 한식·분식처럼 메뉴가 섞이는 곳은 넣지 않는다 —
#    엉뚱한 탭에 몰아넣으면 「기타」보다 나쁘다.
_BRAND_FALLBACK = {
    "피자": "피자",
    "치킨": "치킨",
    "버거": "버거",
}


def tab_of(menu_name, raw_category=None, brand_cat=None):
    """(메뉴명, 브랜드가 준 카테고리, 브랜드 업종) → 표준 탭 하나.

    🔴 `brand_cat` 이 있으면 **마지막 폴백**으로 쓴다 (2026-07-28).
       청년피자의 「옥수동 새우집」·「베를린 메가미트」처럼 **「피자」라는 글자가 없는
       피자 메뉴**가 많다. 피자집에서 파는 건 대체로 피자다 — 「기타」보다 낫다.
    """
    # ① 브랜드가 준 카테고리 — 「치킨 · BHC시그니처」 처럼 붙어 오면 조각마다 본다
    for piece in re.split(r"[·,/|]", (raw_category or "")):
        key = re.sub(r"\s+", "", piece).lower()
        if not key:
            continue
        if key in _ALIAS:
            v = _ALIAS[key]
            if v:
                return v
            break                       # 「추천메뉴」 등 — 이름으로 다시 판정
        for k, v in _ALIAS.items():     # 「사이드메뉴」 처럼 말이 붙은 경우
            if v and k in key:
                return v
    # ② 메뉴 이름으로
    nm = menu_name or ""
    for t, rx in _BYNAME:
        if rx.search(nm):
            return t
    # ③ 브랜드 업종으로 폴백 — 피자집의 정체불명 메뉴는 대개 피자다
    if brand_cat:
        v = _BRAND_FALLBACK.get(brand_cat)
        if v:
            return v
    return "기타"


def order_key(tab):
    """화면 정렬용 — TABS 순서, 모르는 건 맨 뒤."""
    return TABS.index(tab) if tab in TABS else len(TABS)


if __name__ == "__main__":
    import io
    import os
    import sqlite3
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c = sqlite3.connect(os.path.join(BASE, "data", "eolmanama.db"), timeout=60)
    c.row_factory = sqlite3.Row
    rows = c.execute("""SELECT b.name bn, o.name, o.category FROM brand_menu_official o
                        JOIN brands b ON b.id=o.brand_id WHERE o.price>0""").fetchall()
    by = {}
    for r in rows:
        t = tab_of(r["name"], r["category"])
        by.setdefault(r["bn"], {}).setdefault(t, []).append(r["name"])
    tot = {}
    for bn, d in sorted(by.items(), key=lambda x: -sum(len(v) for v in x[1].values()))[:14]:
        print("● %-14s %s" % (bn[:14], " / ".join(
            "%s %d" % (t, len(d[t])) for t in sorted(d, key=order_key))))
        for t, v in d.items():
            tot[t] = tot.get(t, 0) + len(v)
    print("\n전체: %s" % " / ".join("%s %d" % (t, tot[t]) for t in sorted(tot, key=order_key)))
    etc = [r["name"] for r in rows if tab_of(r["name"], r["category"]) == "기타"]
    print("\n「기타」 %d개 — 표본: %s" % (len(etc), " / ".join(etc[:12])))
