# -*- coding: utf-8 -*-
"""밀키트 대체품 조사 — 계획/키워드 생성 (오프라인, API 미사용)

menu_list.json(452) 을 읽어 각 메뉴에 대한 대체 검색 키워드 후보(구체→중간→일반)를
생성한다. 맛 계열 매핑·브랜드 제거·한글화를 적용한다. 결과:
  - data/research/mealkit_kw_plan.json : [{menu_id, brand, menu, type, keywords:[...]}]
  - 콘솔에 통계
API 는 부르지 않는다. 실제 조회는 coupang_search.py 가 한다.
"""
import os, io, json, re
from collections import Counter, OrderedDict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "data", "research")
ML = os.path.join(RES, "menu_list.json")

# 맛 계열 매핑 — 메뉴명에 이 말이 있으면 대체어로 치환/보강
FLAVOR = [
    ("허니", "허니소이"), ("소이", "소이"), ("간장", "소이"),
    ("양념", "양념"), ("강정", "강정"),
    ("레드", "스파이시"), ("매운", "스파이시"), ("핫", "스파이시"),
    ("스파이시", "스파이시"), ("마라", "마라"),
    ("바베큐", "바비큐"), ("바비큐", "바비큐"),
    ("갈릭", "갈릭"), ("마늘", "갈릭"),
    ("치즈", "치즈"), ("커리", "커리"), ("카레", "카레"),
]

# 조리형이 아니라 제외할 카테고리 신호(상품명 필터에도 쓰임)
EXCLUDE = re.compile(
    r"(교환권|상품권|기프트|기프티|쿠폰|바우처|"
    r"소스\b|양념장|드레싱\b|시즈닝|파우더\b|"
    r"과자|스낵|칩\b|젤리|사탕|초콜릿|초코릿|음료|콜라|사이다|주스|"
    r"사료|간식|장난감|굿즈|티셔츠|의류|세트할인|"
    r"영양제|비타민|생수|커피믹스)"
)

# 음료/커피 — 밀키트 대상 아님. API 호출 낭비 방지로 미리 건너뛴다.
BEVERAGE = re.compile(
    r"(아메리카노|라떼|라뗴|카페라|에스프레소|커피|프라페|프라푸치노|빽스치노|"
    r"스무디|에이드|피지오|자바칩|마키아또|콜드브루|카푸치노|초코라?떼|"
    r"주스|쥬스|생과일|빙수|말차|녹차라|버블티|밀크티|음료|아아|메리카노)")
BEVERAGE_BRAND = re.compile(r"(메가MGC커피|빽다방|컴포즈커피|스타벅스|투썸플레이스|"
                            r"이디야|공차|더벤티|매머드|파스쿠찌)")

# 브랜드명(영문/약어) → 검색에서 제거하거나 한글 요리로. 영문 브랜드는 오염 심함.
BRAND_STRIP = re.compile(r"(BBQ|BHC|KFC|bhc|VIPS|빕스|맘스터치|버거킹|롯데리아|맥도날드|"
                         r"교촌|굽네|네네|처갓집|호식이|또래오래|페리카나|바른치킨|"
                         r"자담|60계|푸라닭|노랑통닭|지코바|"
                         r"도미노|피자헛|미스터피자|파파존스|피자알볼로|"
                         r"본죽|김밥천국|한솥|본도시락|"
                         r"스타벅스|투썸|이디야|메가커피|빽다방|공차)")

# 괄호/수량/옵션 제거
PAREN = re.compile(r"[\(\[][^\)\]]*[\)\]]")
QTY = re.compile(r"\d+\s*(개|인분|조각|마리|판|인|ml|g|kg|L|미|ea|EA|셋트|세트)\b")


def clean_menu(name):
    s = PAREN.sub(" ", name)
    s = BRAND_STRIP.sub(" ", s)
    s = QTY.sub(" ", s)
    s = re.sub(r"[\+\-/·,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def flavor_terms(name):
    out = []
    for key, rep in FLAVOR:
        if key in name and rep not in out:
            out.append(rep)
    return out


# 카테고리별 앵커(선정 시 관련성 판단용) — 상품명에 이게 있으면 그 요리로 인정
ANCHORS = {
    "치킨": ["치킨", "닭", "가라아게", "강정", "너겟", "윙", "봉", "순살", "지파이", "텐더"],
    "피자": ["피자", "도우", "화덕"],
    "햄버거": ["버거", "패티", "햄버거"],
    "분식": ["떡볶이", "떡꼬치", "소떡", "순대", "어묵", "김밥", "핫도그", "라볶이", "쫄면", "튀김"],
    "돈까스": ["돈까스", "돈가스", "카츠", "가츠", "커틀릿"],
    "족발보쌈": ["족발", "보쌈", "수육"],
    "곱창": ["곱창", "막창", "대창", "양깃"],
    "초밥": ["초밥", "스시", "롤", "회", "사시미", "포케", "덮밥", "회덮밥"],
    "파스타": ["파스타", "스파게티", "리조또", "라자냐", "뇨끼"],
    "샐러드": ["샐러드", "샐러디", "포케", "닭가슴살"],
    "국탕찌개": ["국", "탕", "찌개", "전골", "찜", "육개장", "해장국", "곰탕", "설렁탕"],
    "베이커리": ["빵", "케이크", "도넛", "크로플", "와플", "번", "브레드", "파이", "베이글"],
    "중식": ["짜장", "짬뽕", "탕수육", "마라", "꿔바로우", "볶음밥", "중화"],
    "면류": ["국수", "냉면", "우동", "라면", "칼국수", "쌀국수", "분짜", "파스타", "면"],
}


# 요리 카테고리 분류. 메뉴명의 요리 단어를 먼저 보고, 없으면 브랜드로 보정.
def category_for(brand, menu):
    b = brand or ""
    m = menu or ""

    def inm(*xs):
        return any(x in m for x in xs)

    # 1) 메뉴명 우선(브랜드 오분류 방지: BBQ의 소떡을 치킨으로 잡지 않게)
    if inm("소떡", "핫도그", "떡볶이", "떡꼬치", "순대", "어묵", "라볶이", "쫄면", "김밥"):
        return "분식"
    if inm("짜장", "짬뽕", "탕수육", "꿔바로우", "마라샹궈", "마라탕", "고추짜장", "울면"):
        return "중식"
    if inm("돈까스", "돈가스", "카츠", "가츠"):
        return "돈까스"
    if inm("족발", "보쌈"):
        return "족발보쌈"
    if inm("곱창", "막창", "대창"):
        return "곱창"
    if inm("초밥", "스시", "사시미", "회덮밥", "포케"):
        return "초밥"
    if inm("파스타", "스파게티", "리조또", "라자냐"):
        return "파스타"
    if inm("쌀국수", "분짜", "우동", "냉면", "칼국수", "잔치국수", "막국수", "콩국수", "국수"):
        return "면류"
    if inm("육개장", "해장국", "설렁탕", "곰탕", "시래기", "찌개", "전골", "육개장"):
        return "국탕찌개"
    if inm("샐러드", "샐러디"):
        return "샐러드"
    if inm("피자"):
        return "피자"
    if inm("버거", "햄버거"):
        return "햄버거"
    if inm("만두"):
        return "분식"
    if inm("치킨", "통닭", "강정", "닭강정", "순살", "후라이드", "양념치킨", "윙", "콤보"):
        return "치킨"
    if inm("빵", "케이크", "도넛", "크로플", "와플", "고로케", "브레드", "베이글", "토스트"):
        return "베이커리"

    # 2) 브랜드 보정
    def inb(*xs):
        return any(x in b for x in xs)

    if inb("치킨", "통닭", "BBQ", "교촌", "굽네", "네네", "처갓집", "푸라닭", "60계", "지코바", "노랑", "가마로강정", "또래오래", "페리카나", "호식이", "bhc", "BHC"):
        return "치킨"
    if inb("피자", "도미노", "피자헛", "파파존스", "알볼로"):
        return "피자"
    if inb("버거", "버거킹", "맘스터치", "롯데리아", "맥도날드"):
        return "햄버거"
    if inb("분식", "김밥", "떡볶이", "핫도그", "명랑"):
        return "분식"
    if inb("족발", "보쌈"):
        return "족발보쌈"
    if inb("곱창", "막창", "포차"):
        return "곱창"
    if inb("초밥", "스시", "포케", "슬로우캘리", "포케올데이"):
        return "초밥"
    if inb("파스타", "스파게티"):
        return "파스타"
    if inb("쌀국수", "포메인", "미스사이공", "에머이"):
        return "면류"
    if inb("육개장", "국밥", "시래기", "한식"):
        return "국탕찌개"
    if inb("샐러", "샐러디"):
        return "샐러드"
    if inb("베이커리", "파리바게", "뚜레쥬르", "던킨", "빵"):
        return "베이커리"
    return None


def is_beverage(brand, menu):
    b = brand or ""
    m = menu or ""
    if BEVERAGE.search(m):
        return True
    # 음료 브랜드인데 메뉴가 명백한 먹거리(토스트/샌드/베이글 등)가 아니면 음료로 간주
    if BEVERAGE_BRAND.search(b) and not re.search(r"(토스트|샌드|베이글|와플|케이크|쿠키|빵)", m):
        return True
    return False


def build_keywords(item):
    brand = item.get("brand") or ""
    menu = item.get("menu") or ""
    cleaned = clean_menu(menu)
    flav = flavor_terms(menu)
    cat = category_for(brand, menu)
    kws = []

    def add(k):
        k = re.sub(r"\s+", " ", k).strip()
        if k and 2 <= len(k) <= 30 and k not in kws:
            kws.append(k)

    # 카테고리 있는 치킨/분식류: 맛+카테고리를 먼저 — 테스트상 '허니치킨 냉동'류가 최고 품질
    # (황금올리브·허니콤보 같은 상품라인명 직역보다 맛+요리 대체가 정확)
    if cat and flav:
        for f in flav:
            add(f + " " + cat + " 냉동")
    # 1) 중간 단계: 정리된 요리명 + 냉동 / 밀키트 (핵심 — 대부분 여기서 해결)
    if cleaned:
        add(cleaned + " 냉동")
        add(cleaned + " 밀키트")
    # 2) 맛 없는 카테고리도 맛 조합 시도
    if cat:
        for f in flav:
            add(f + " " + cat + " 냉동")
        # 3) 일반 카테고리 냉동/밀키트
        add(cat + " 냉동")
        add(cat + " 밀키트")
    # 4) 정리명 자체(냉동 없이) — 최후
    if cleaned and len(cleaned) >= 3:
        add(cleaned)
    return kws, cat


def main():
    data = json.load(io.open(ML, encoding="utf-8"))
    plan = []
    no_cat = []
    skipn = 0
    for it in data:
        kws, cat = build_keywords(it)
        bev = is_beverage(it.get("brand"), it.get("menu"))
        if bev:
            skipn += 1
        plan.append({"menu_id": it["menu_id"], "brand": it["brand"],
                     "menu": it["menu"], "type": it["type"],
                     "category": cat, "anchors": ANCHORS.get(cat, []),
                     "skip": bev,
                     "skip_reason": "음료/커피(밀키트 대상 아님)" if bev else None,
                     "keywords": kws})
        if not cat:
            no_cat.append(it)
    io.open(os.path.join(RES, "mealkit_kw_plan.json"), "w", encoding="utf-8").write(
        json.dumps(plan, ensure_ascii=False, indent=1))

    # 유니크 키워드(전체) 수집 — 캐시 대비 (skip 메뉴 제외)
    allkw = OrderedDict()
    for p in plan:
        if p.get("skip"):
            continue
        for k in p["keywords"]:
            allkw[k] = allkw.get(k, 0) + 1
    io.open(os.path.join(RES, "mealkit_kw_all.json"), "w", encoding="utf-8").write(
        json.dumps(list(allkw.keys()), ensure_ascii=False, indent=1))

    print("메뉴 %d개 · 유니크 키워드 %d개 · 음료 skip %d개" % (len(plan), len(allkw), skipn))
    print("카테고리 미분류(대상 제외 후보) %d개" % len(no_cat))
    cnt = Counter(p["category"] for p in plan)
    for c, n in cnt.most_common():
        print("  %-8s %d" % (str(c), n))


if __name__ == "__main__":
    main()
