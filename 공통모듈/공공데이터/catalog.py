# 얼마남아 B2B — 공공 재료 마스터 (ingredients 테이블 시드 원본)
#
# B2C의 재료 마스터는 프랜차이즈 메뉴 역산용(염지닭 10호 등)이라 B2B에 부적합.
# B2B는 "사장님이 실제로 매입하는 식자재"를 공공시세에 연결하는 게 목적이므로
# KAMIS/축평원/참가격 카탈로그를 2026-07-16 실호출로 덤프해 직접 큐레이션함.
#
# 각 항목의 code 값은 전부 실제 API 응답에서 확인된 값. 추측 없음.
#
# source 별 특성 (실측):
#   kamis  — 도매(02)+소매(01) 둘 다 확보 O   → B2B 기본값 wholesale 사용 가능
#   ekape  — 소비자가(소매) + 일부 도매(2026-07-16 추가: 한우 부분육 경락·닭 도체·돼지 지육).
#            도매 미커버 품목(수입육·계란·우유 등)은 wholesale NULL
#   chamga — 소비자가(마트 판매가)만. 주간 조사.                        → wholesale NULL

from . import ekape, kamis

# ────────────────────────────────────────────────────────────
# 1) KAMIS 농산물 — (카테고리, item_code, kind_code)
#    convert_kg_yn=Y 기준으로 '(1kg)' 환산이 성립하는 품목만 등재.
#    수박(1개)·오이 다다기(50개)·애호박(20개) 등 개수단위 품목은 kg 환산 불가라 제외.
# ────────────────────────────────────────────────────────────
KAMIS_ITEMS = [
    # key,                    name,            cat,               item, kind, unit
    ("rice",                  "쌀",             kamis.CAT_GRAIN,     "111", "01", "kg"),
    ("glutinous_rice",        "찹쌀",           kamis.CAT_GRAIN,     "112", "01", "kg"),
    ("soybean",               "콩(국산)",        kamis.CAT_GRAIN,     "141", "01", "kg"),
    ("red_bean",              "팥(수입)",        kamis.CAT_GRAIN,     "142", "01", "kg"),
    ("mung_bean",             "녹두(수입)",      kamis.CAT_GRAIN,     "143", "01", "kg"),
    ("buckwheat",             "메밀(수입)",      kamis.CAT_GRAIN,     "144", "01", "kg"),
    ("sweet_potato",          "고구마(밤)",      kamis.CAT_GRAIN,     "151", "00", "kg"),
    ("potato",                "감자(수미)",      kamis.CAT_GRAIN,     "152", "01", "kg"),

    ("napa_cabbage",          "배추",           kamis.CAT_VEGETABLE, "211", "01", "kg"),
    ("cabbage",               "양배추",          kamis.CAT_VEGETABLE, "212", "00", "kg"),
    ("spinach",               "시금치",          kamis.CAT_VEGETABLE, "213", "00", "kg"),
    ("lettuce_red",           "상추(적)",        kamis.CAT_VEGETABLE, "214", "01", "kg"),
    ("lettuce_green",         "상추(청)",        kamis.CAT_VEGETABLE, "214", "02", "kg"),
    ("eolgari_cabbage",       "얼갈이배추",      kamis.CAT_VEGETABLE, "215", "00", "kg"),
    ("korean_melon",          "참외",           kamis.CAT_VEGETABLE, "222", "00", "kg"),
    ("cucumber",              "오이(가시계통)",   kamis.CAT_VEGETABLE, "223", "01", "kg"),
    ("zucchini",              "쥬키니호박",      kamis.CAT_VEGETABLE, "224", "02", "kg"),
    ("tomato",                "토마토",          kamis.CAT_VEGETABLE, "225", "00", "kg"),
    ("radish",                "무",             kamis.CAT_VEGETABLE, "231", "01", "kg"),
    ("carrot",                "당근(국산)",      kamis.CAT_VEGETABLE, "232", "01", "kg"),
    ("yeolmu",                "열무",           kamis.CAT_VEGETABLE, "233", "00", "kg"),
    ("dried_red_pepper",      "건고추(화건)",    kamis.CAT_VEGETABLE, "241", "00", "kg"),
    ("green_pepper",          "풋고추",          kamis.CAT_VEGETABLE, "242", "00", "kg"),
    ("cheongyang_pepper",     "청양고추",        kamis.CAT_VEGETABLE, "242", "03", "kg"),
    ("red_pepper",            "붉은고추",        kamis.CAT_VEGETABLE, "243", "00", "kg"),
    ("garlic_bulb",           "피마늘(난지·대서)", kamis.CAT_VEGETABLE, "244", "22", "kg"),
    ("onion",                 "양파",           kamis.CAT_VEGETABLE, "245", "00", "kg"),
    ("green_onion",           "대파",           kamis.CAT_VEGETABLE, "246", "00", "kg"),
    ("chives",                "쪽파",           kamis.CAT_VEGETABLE, "246", "02", "kg"),
    ("ginger",                "생강(국산)",      kamis.CAT_VEGETABLE, "247", "00", "kg"),
    ("water_parsley",         "미나리",          kamis.CAT_VEGETABLE, "252", "00", "kg"),
    ("perilla_leaf",          "깻잎",           kamis.CAT_VEGETABLE, "253", "00", "kg"),
    ("bell_pepper",           "피망(청)",        kamis.CAT_VEGETABLE, "255", "00", "kg"),
    ("paprika",               "파프리카",        kamis.CAT_VEGETABLE, "256", "00", "kg"),
    ("peeled_garlic",         "깐마늘(대서)",     kamis.CAT_VEGETABLE, "258", "03", "kg"),
    ("baby_napa_cabbage",     "알배기배추",      kamis.CAT_VEGETABLE, "279", "00", "kg"),
    ("broccoli",              "브로콜리(국산)",   kamis.CAT_VEGETABLE, "280", "00", "kg"),
    ("cherry_tomato",         "대추방울토마토",   kamis.CAT_VEGETABLE, "422", "02", "kg"),

    ("sesame_seed",           "참깨(중국산)",     kamis.CAT_SPECIAL,   "312", "02", "kg"),
    ("perilla_seed",          "들깨(수입)",      kamis.CAT_SPECIAL,   "313", "02", "kg"),
    ("peanut",                "땅콩(국산)",      kamis.CAT_SPECIAL,   "314", "01", "kg"),
    ("oyster_mushroom",       "느타리버섯",      kamis.CAT_SPECIAL,   "315", "00", "kg"),
    ("enoki_mushroom",        "팽이버섯",        kamis.CAT_SPECIAL,   "316", "00", "kg"),
    ("king_oyster_mushroom",  "새송이버섯",      kamis.CAT_SPECIAL,   "317", "00", "kg"),

    ("apple",                 "사과(후지)",      kamis.CAT_FRUIT,     "411", "05", "kg"),
    ("pear",                  "배(신고)",        kamis.CAT_FRUIT,     "412", "01", "kg"),
    ("peach",                 "복숭아(백도)",     kamis.CAT_FRUIT,     "413", "01", "kg"),
    ("grape",                 "포도(캠벨얼리)",   kamis.CAT_FRUIT,     "414", "01", "kg"),
    ("banana",                "바나나(수입)",     kamis.CAT_FRUIT,     "418", "02", "kg"),
    ("kiwi",                  "참다래(그린)",     kamis.CAT_FRUIT,     "419", "02", "kg"),
    ("pineapple",             "파인애플(수입)",   kamis.CAT_FRUIT,     "420", "02", "kg"),
    ("orange",                "오렌지(네이블)",   kamis.CAT_FRUIT,     "421", "06", "kg"),
    ("lemon",                 "레몬(수입)",      kamis.CAT_FRUIT,     "424", "00", "kg"),
    ("mango",                 "망고(수입)",      kamis.CAT_FRUIT,     "428", "00", "kg"),
]

# ────────────────────────────────────────────────────────────
# 2) 축평원 축산물 — (judgeKind, itemCd, grdNm)
#    ★ B2C의 "소고기 다짐육/우삼겹이 안심·등심값으로 3배 과대" 문제는
#      여기서 부위를 직접 지정함으로써 구조적으로 해소됨.
#      (다짐육·불고기 → 설도/양지, 우삼겹 → 수입 척아이롤/양지)
# ────────────────────────────────────────────────────────────
EKAPE_ITEMS = [
    # key,                       name,                  judgeKind,             itemCd, grdNm,      unit
    ("beef_tenderloin",   "한우 안심(1등급)",        ekape.KIND_BEEF,        "21", "1등급",    "kg"),
    ("beef_sirloin",      "한우 등심(1등급)",        ekape.KIND_BEEF,        "22", "1등급",    "kg"),
    ("beef_bottom_round", "한우 설도(1등급)",        ekape.KIND_BEEF,        "36", "1등급",    "kg"),
    ("beef_brisket",      "한우 양지(1등급)",        ekape.KIND_BEEF,        "40", "1등급",    "kg"),
    ("beef_rib",          "한우 갈비(1등급)",        ekape.KIND_BEEF,        "50", "1등급",    "kg"),

    ("pork_shoulder",     "돼지 앞다리",             ekape.KIND_PORK,        "25", "구분없음",  "kg"),
    ("pork_belly",        "돼지 삼겹살",             ekape.KIND_PORK,        "27", "구분없음",  "kg"),
    ("pork_rib",          "돼지 갈비",               ekape.KIND_PORK,        "28", "구분없음",  "kg"),
    ("pork_neck",         "돼지 목심",               ekape.KIND_PORK,        "68", "구분없음",  "kg"),

    ("beef_brisket_us",   "수입 소 양지(미국산·냉장)", ekape.KIND_BEEF_IMPORT, "29", "미국산",   "kg"),
    ("beef_rib_us",       "수입 소 갈비(미국산·냉동)", ekape.KIND_BEEF_IMPORT, "31", "미국산",   "kg"),
    ("beef_chuckroll_us", "수입 소 척아이롤(미국산·냉장)", ekape.KIND_BEEF_IMPORT, "62", "미국산", "kg"),
    ("beef_chuckroll_au", "수입 소 척아이롤(호주산·냉장)", ekape.KIND_BEEF_IMPORT, "62", "호주산", "kg"),

    ("pork_belly_import", "수입 삼겹살",             ekape.KIND_PORK_IMPORT, "27", "구분없음",  "kg"),
    # ※ 수입 돼지는 축평원에 삼겹살(27) 하나뿐 — 목살·앞다리 없음(품목코드 전수 확인).
    #    식당이 실제로 쓰는 수입 부위는 DERIVED_ITEMS 로 파생시킨다.

    # ★ 닭: KAMIS 9901 '절단육'은 0원만 내려옴(실측). 축평원 육계(kg)를 사용.
    ("chicken_broiler",   "육계(생닭)",              ekape.KIND_CHICKEN,     "99", "구분없음",  "kg"),
    # ★ 계란: 원/30구 → kg 환산 (특란 1구 64g × 30 = 1.92kg). ekape._unit_factor가 처리.
    ("egg",               "계란(특란·일반란)",        ekape.KIND_EGG,         "23", "일반란",    "kg"),
    ("milk",              "흰우유",                  ekape.KIND_MILK,        "01", "구분없음",  "L"),
]

# ────────────────────────────────────────────────────────────
# 2-b) 축평원 도매(경락) 매핑 — 2026-07-16 추가
#
#    EKAPE_ITEMS의 소비자가(retail)는 그대로 두고, 여기 등록된 항목만
#    wholesale을 병행 수집한다(도소매가 나란히 쌓여야 도소매 비교가 됨).
#    스펙 형식은 ekape.pick_wholesale() 주석 참조 — 엔드포인트별 개별 매핑.
#
#    ⚠️ 한우: retail은 '1등급' 소비자가, wholesale은 부분육 박스경락
#       한우 전체평균(hanAvgT) — 등급 기준이 다름을 유의(등급별은 hanAvg_0~3,
#       육우는 yukAvgT로 받을 수 있음).
#    ⚠️ auct/beefGrade는 미문서화 API(WADL에만 존재) — ekape.py 주석 참조.
# ────────────────────────────────────────────────────────────
EKAPE_WHOLESALE = {
    # 기존 소비자가 항목에 도매 병행 (부위명은 beefGrade cutmeatName 실측값)
    "beef_tenderloin":   {"api": "beefGrade", "cut": "안심", "field": "hanAvgT"},
    "beef_sirloin":      {"api": "beefGrade", "cut": "등심", "field": "hanAvgT"},
    "beef_bottom_round": {"api": "beefGrade", "cut": "설도", "field": "hanAvgT"},
    "beef_brisket":      {"api": "beefGrade", "cut": "양지", "field": "hanAvgT"},
    "beef_rib":          {"api": "beefGrade", "cut": "갈비", "field": "hanAvgT"},
    # 닭: avg를 wholesale로. franchise/agency/mart는 리포트로 보존(ekape.py 주석 참조)
    "chicken_broiler":   {"api": "chickenDomae", "field": "avg"},
}

# 도매 전용 신규 항목 — 소비자가 짝이 없는 것들.
#   · 한우 목심/앞다리: consumerPriceDaily 4301엔 안심·등심·설도·양지·갈비 5부위뿐
#     (2026-07-16 실측 전수확인) → retail 없음, beefGrade 경락만.
#   · 돼지 지육: 부분육이 아니라 도체(지육) 단가 — 정육 부위가와 직접 비교 금지.
#     '등외제외'(등외·모돈 제외 평균)가 통상 지표. 실측(2026-07-10) 7,038원/kg.
EKAPE_WHOLESALE_ONLY = [
    # key,            name,                        wholesale spec,                                            unit
    ("beef_neck",     "한우 목심(부분육 경락)",      {"api": "beefGrade", "cut": "목심",  "field": "hanAvgT"},   "kg"),
    ("beef_foreleg",  "한우 앞다리(부분육 경락)",    {"api": "beefGrade", "cut": "앞다리", "field": "hanAvgT"},   "kg"),
    ("pork_carcass",  "돼지 지육(경락·등외제외)",    {"api": "pigGrade", "grade": "등외제외", "field": "CTotAmt"}, "kg"),
]

# ────────────────────────────────────────────────────────────
# 3) 참가격 가공식품 — (goodId, 포장중량/용량)
#    goodPrice는 '포장 1개 가격'이라 pack 값으로 나눠 kg/L 단가로 환산한다.
#    goodId·상품명은 B2C가 확보한 참가격 상품목록(chamga_goods.tsv)에서 발췌.
# ────────────────────────────────────────────────────────────
CHAMGA_ITEMS = [
    # key,             name,                     goodId, pack, unit
    ("sesame_oil",     "참기름(오뚜기 320ml)",       "225", 0.32, "L"),
    ("cooking_oil",    "식용유(해표 900ml)",         "254", 0.90, "L"),
    ("sugar_white",    "백설탕(백설 1kg)",           "257", 1.00, "kg"),
    ("salt",           "꽃소금(해표 1kg)",           "35",  1.00, "kg"),
    ("soy_sauce_jin",  "진간장(금F3 860ml)",         "1385", 0.86, "L"),
    ("soy_sauce_brew", "양조간장(501 500ml)",        "1221", 0.50, "L"),
    ("vinegar",        "사과식초(오뚜기 900ml)",      "291", 0.90, "L"),
    ("gochujang",      "고추장(해찬들 태양초 1kg)",    "638", 1.00, "kg"),
    ("doenjang",       "된장(해찬들 재래식 1kg)",     "332", 1.00, "kg"),
    ("ssamjang",       "쌈장(청정원 순창 500g)",      "536", 0.50, "kg"),
    ("red_pepper_powder", "고춧가루(태양초 1kg)",     "1453", 1.00, "kg"),
    ("mayonnaise",     "마요네즈(오뚜기 500g)",       "230", 0.50, "kg"),
    ("flour_medium",   "중력 밀가루(큐원 1kg)",       "1410", 1.00, "kg"),
    ("flour_strong",   "강력 밀가루(큐원 1kg)",       "1412", 1.00, "kg"),
    ("noodle_somyeon", "소면(옛날국수 900g)",         "239", 0.90, "kg"),
    ("dangmyeon",      "당면(옛날 자른당면 300g)",     "1184", 0.30, "kg"),
    ("starch_syrup",   "물엿(오뚜기 1.2kg)",          "1469", 1.20, "kg"),
    ("oligo_syrup",    "올리고당(백설 1.2kg)",        "1470", 1.20, "kg"),
    ("butter",         "버터(서울우유 450g)",         "1502", 0.45, "kg"),
    ("sliced_cheese",  "체다슬라이스치즈(서울우유 360g)", "1610", 0.36, "kg"),
]


# ────────────────────────────────────────────────────────────
# 4) 파생 재료 — 공공 API에 없는 부위를, 있는 부위 시세에 계수를 걸어 만든다.
#
#    왜 필요한가: 식당이 실제로 쓰는 부위가 공공데이터에 없는 경우가 많다.
#    (예: 제육볶음은 목심이 아니라 '목전지'를 쓰는데 축평원엔 목전지가 없음)
#    고정값(manual)으로 박으면 시세를 못 따라가므로, 있는 부위에 계수를 걸어
#    시세를 자동 추종하게 한다. markup_factor는 refresh_costs.py가 적용한다.
#
#    ⚠️ 계수는 추정치다. OCR 영수증으로 실매입가가 들어오면 보정할 것.
# ────────────────────────────────────────────────────────────
DERIVED_ITEMS = [
    # key,                 name,              기준(축종, 품목, 등급),                    unit, factor, 근거
    ("pork_collar_import", "수입 돼지 목전지", ekape.KIND_PORK, "25", "구분없음", "kg", 0.693,
     "국내 앞다리 × 0.533(수입/국내 실측비: 수입삼겹 15,390÷국내삼겹 28,880) × 1.3(목전지 프리미엄, 앞다리~목심 사이 추정)"),
]


def all_rows():
    """ingredients 테이블 INSERT용 dict 리스트."""
    import json

    rows = []
    for key, name, cat, item, kind, unit in KAMIS_ITEMS:
        rows.append(dict(
            ingredient_key=key, name=name, cls="농축산물", type="live",
            kamis_cat=cat, kamis_item_code=item, kamis_kind_code=kind,
            ekape_item=None, composite_formula=None, chamgagyeok_key=None,
            manual_price=None, base_unit=unit, source="kamis",
        ))
    for key, name, jk, item, grd, unit in EKAPE_ITEMS:
        spec = {"kind": jk, "item": item, "grd": grd}
        if key in EKAPE_WHOLESALE:  # 도매 병행 수집 항목
            spec["wholesale"] = EKAPE_WHOLESALE[key]
        rows.append(dict(
            ingredient_key=key, name=name, cls="농축산물", type="live",
            kamis_cat=None, kamis_item_code=None, kamis_kind_code=None,
            ekape_item=json.dumps(spec, ensure_ascii=False),
            composite_formula=None, chamgagyeok_key=None,
            manual_price=None, base_unit=unit, source="ekape",
        ))
    for key, name, wspec, unit in EKAPE_WHOLESALE_ONLY:
        rows.append(dict(
            ingredient_key=key, name=name, cls="농축산물", type="live",
            kamis_cat=None, kamis_item_code=None, kamis_kind_code=None,
            ekape_item=json.dumps({"wholesale": wspec}, ensure_ascii=False),
            composite_formula=None, chamgagyeok_key=None,
            manual_price=None, base_unit=unit, source="ekape",
        ))
    for key, name, jk, item, grd, unit, factor, _why in DERIVED_ITEMS:
        rows.append(dict(
            ingredient_key=key, name=name, cls="농축산물", type="live",
            kamis_cat=None, kamis_item_code=None, kamis_kind_code=None,
            ekape_item=json.dumps({"kind": jk, "item": item, "grd": grd}, ensure_ascii=False),
            composite_formula=None, chamgagyeok_key=None,
            manual_price=None, base_unit=unit, source="derived", markup=factor,
        ))
    for key, name, good_id, pack, unit in CHAMGA_ITEMS:
        rows.append(dict(
            ingredient_key=key, name=name, cls="가공품", type="live",
            kamis_cat=None, kamis_item_code=None, kamis_kind_code=None,
            ekape_item=None, composite_formula=None,
            chamgagyeok_key=json.dumps({"goodId": good_id, "pack": pack}, ensure_ascii=False),
            manual_price=None, base_unit=unit, source="chamga",
        ))
    return rows
