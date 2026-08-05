# -*- coding: utf-8 -*-
# 요리 정의 데이터 — gen_dishes.py에서 분리 (2026-07-20)
#
# 왜 분리했나: 레시피 생성 관리페이지가 DB로 요리를 추가·수정할 수 있어야 하는데,
#   gen_dishes.py가 이 리터럴로 매 실행 dishes 테이블을 통째로 재생성해서 DB 변경이 날아갔다.
#   여기로 빼두면 gen_dishes는 "DB 우선 + 이 리터럴 폴백"으로 갈 수 있다(P1).
#
# 🔴 healthcheck.py가 이 파일을 import해서 재료키를 검증한다.
#   예전엔 gen_dishes.py 소스를 정규식으로 긁었는데, 데이터를 옮기면 빈 set을 얻어
#   "실패"가 아니라 "조용히 통과"가 된다. 그래서 같이 고쳤다. 구조를 또 바꾸면 healthcheck도 같이 볼 것.
#
# ⚠️ 순수 데이터만 둔다. DB 접속·함수·부수효과 금지(healthcheck가 import하므로).


# (이름, slug, 1인분 표기, 매칭 정규식(우선순위순), 표준 레시피 [(키,양,단위)])
DISHES = [
 ("후라이드치킨","fried-chicken","한 마리", r"후라이드|황금올리브|엄청큰",
   [("raw_chicken_10",1,"kg"),("frying_powder",200,"g"),("frying_oil",300,"ml")]),
 # '숯불양념'은 뺀다(2026-07-19 사용자 지적): 지코바 숯불양념치킨은 튀김+시판 양념치킨소스가 아니라
 #  숯불구이 + 자체 제조 양념이다. 이 요리(=튀긴 양념치킨)에 묶으면 재료 구성이 틀린 채로 비교된다.
 #  해당 메뉴들의 메뉴 페이지는 이미 sauce_normal(자체 제조 양념)로 잡혀 있어 그대로 두면 된다.
 ("양념치킨","yangnyeom-chicken","한 마리", r"(?<!숯불)양념치킨|슈프림양념|맛초킹|레드콤보|매콤강정",
   [("raw_chicken_10",1,"kg"),("frying_powder",200,"g"),("frying_oil",300,"ml"),("sauce_yangnyeom",180,"g")]),
 ("간장치킨","ganjang-chicken","한 마리", r"간장|오리지날|골드킹",
   [("raw_chicken_10",1,"kg"),("frying_powder",200,"g"),("frying_oil",300,"ml")]),
 ("로제떡볶이","rose-tteokbokki","1~2인분", r"로제(?!마라)|투움바떡",
   [("tteok",300,"g"),("sauce_rose",120,"g"),("vienna_sausage",50,"g"),("mozzarella_cheese",40,"g")]),
 ("떡볶이","tteokbokki","1인분", r"떡볶이",
   [("tteok",300,"g"),("fish_cake",80,"g"),("sauce_tteokbokki",60,"g"),("egg_fresh",1,"개")]),
 # 짜장면 — OpenAI 생성 레시피(2026-07-20)의 재료 **전량**으로 교체.
 #  원칙: 만드는 법에 나오는 재료 = 재료표 100% 일치. 물도 넣되 단가 0으로 잡는다.
 #  진간장은 양념 10ml + 밑간 5ml = 15ml 합산.
 ("짜장면","jjajangmyeon","1인분", r"짜장",
   [("noodles_fresh",200,"g"),("x_e6d782c93c",100,"g"),("kv_245",150,"g"),
    ("aehobak_mart",80,"g"),("yangbaechu_mart",80,"g"),("kv_152",80,"g"),
    ("garlic_minced",10,"g"),("sauce_jjajang",80,"g"),("cg_cooking_oil",20,"ml"),
    ("cg_sugar_white",8,"g"),("cg_soy_sauce_jin",15,"ml"),("x_80310d61c8",12,"g"),
    ("water",1825,"ml")]),
 ("짬뽕","jjamppong","1인분", r"짬뽕",
   [("noodles_fresh",200,"g"),("seafood_mix",100,"g"),("x_1294333d76",30,"g"),("kv_245",50,"g"),("yangbaechu_mart",30,"g"),("kv_232",20,"g")]),
 ("탕수육","tangsuyuk","소(小) 기준", r"탕수육|꿔바로우",
   [("pork_loin_tangsuyuk",300,"g"),("frying_powder",80,"g"),("frying_oil",200,"ml"),("sauce_tangsu",150,"g")]),
 ("마라탕","malatang","1인분", r"마라탕",
   [("kv_245",100,"g"),("yangbaechu_mart",60,"g"),("kv_232",40,"g"),("sp_0bfb3849d1",34,"g"),("dangmyeon",33,"g"),("sp_59126f21db",33,"g"),("beef_slices",50,"g"),("sauce_mala",40,"g")]),
 ("마라샹궈","malaxiangguo","1인분", r"마라샹궈",
   [("kv_245",75,"g"),("yangbaechu_mart",45,"g"),("kv_232",30,"g"),("sp_0bfb3849d1",34,"g"),("dangmyeon",33,"g"),("sp_59126f21db",33,"g"),("beef_slices",80,"g"),("sauce_mala",50,"g"),("frying_oil",30,"ml")]),
 ("김치찌개","kimchi-jjigae","1인분", r"김치찌개|김치부대",
   [("kimchi_fresh",200,"g"),("pork_belly_import",100,"g"),("x_cee737406a",100,"g"),("sauce_kimchi",30,"g")]),
 ("부대찌개","budae-jjigae","1인분", r"부대찌개",
   [("x_eae050081a",150,"g"),("x_cee737406a",100,"g"),("noodles_ramen",1,"개"),("sauce_budae",40,"g"),("kv_245",40,"g"),("yangbaechu_mart",24,"g"),("kv_232",16,"g")]),
 ("순대국밥","sundae-gukbap","1인분", r"순대국|순대정식",
   [("x_a0ada5ee05",160,"g"),("rice_uncooked",100,"g"),("soup_base_korean",40,"g")]),
 ("뼈해장국","ppyeo-haejangguk","1인분", r"뼈해장국|감자탕",
   [("x_2458074f8e",350,"g"),("x_a2f018ad7b",80,"g"),("rice_uncooked",100,"g"),("soup_base_korean",40,"g")]),
 ("설렁탕·곰탕","seolleongtang","1인분", r"설렁탕|곰탕|도가니탕",
   [("beef_stew",100,"g"),("rice_uncooked",100,"g"),("x_571aff06f4",200,"g")]),
 # 🔴 재료는 **레시피 본문에 나온 것**을 그대로 넣는다 (2026-08-03 대표 지시).
 #    본문이 정본이고 재료 목록이 그걸 따라간다 — 반대로 하면 «이 값이 어디서 나왔냐»가 된다.
 #    김밥김은 뺐다 — `김밥재료세트` 5종(단무지·우엉·맛살·햄·**김**)에 이미 들어 있다.
 ("김밥","gimbap","1줄", r"김밥",
   [("rice_uncooked",90,"g"),("cg_salt",2,"g"),("oil_sesame_bulk",5,"ml"),
    ("kv_232",20,"g"),("kv_213",30,"g"),("egg_fresh",1,"개"),("kv_223",30,"g"),
    ("gimbap_ingredients",80,"g")]),
 ("돈까스","donkatsu","1인분", r"돈까스|돈가스|카츠",
   [("pork_loin_donkasu",150,"g"),("frying_powder",60,"g"),("frying_oil",150,"ml"),("sauce_donkatsu",50,"g")]),
 ("족발","jokbal","반 마리(중)", r"족발|통구이",
   [("pork_trotter",700,"g")]),
 ("보쌈","bossam","1인분", r"보쌈",
   [("pork_belly_import",300,"g"),("sauce_ssamjang",30,"g"),("kv_245",25,"g"),("yangbaechu_mart",15,"g"),("kv_232",10,"g")]),
 ("쌀국수","pho","1인분", r"쌀국수",
   [("noodles_rice",120,"g"),("beef_stew",60,"g"),("x_571aff06f4",150,"g"),("kv_245",25,"g"),("yangbaechu_mart",15,"g"),("kv_232",10,"g")]),
 ("분짜","buncha","1인분", r"분짜",
   [("noodles_rice",120,"g"),("x_1294333d76",120,"g"),("sauce_nuoccham",60,"g"),("kv_245",30,"g"),("yangbaechu_mart",18,"g"),("kv_232",12,"g")]),
 ("불고기","bulgogi","1인분", r"불고기|와퍼|버거",  # placeholder—버거는 아래 버거 dish가 우선이라 안 옴
   [("beef_slices",150,"g"),("sauce_bulgogi",50,"g"),("kv_245",40,"g"),("yangbaechu_mart",24,"g"),("kv_232",16,"g")]),
 ("제육볶음","jeyuk-bokkeum","1인분", r"제육",
   [("x_1294333d76",200,"g"),("sauce_jeyuk",40,"g"),("kv_245",40,"g"),("yangbaechu_mart",24,"g"),("kv_232",16,"g")]),
 ("피자","pizza","L 한 판", r"피자",
   [("pizza_dough",350,"g"),("mozzarella_cheese",200,"g"),("pizza_sauce",80,"g"),("kv_245",40,"g"),("yangbaechu_mart",24,"g"),("kv_232",16,"g"),("pepperoni",40,"g")]),
 ("햄버거","burger","단품 1개", r"버거|와퍼|빅맥|시그니처",
   [("burger_bun",1,"개"),("beef_patty",100,"g"),("mozzarella_cheese",20,"g"),("kv_245",15,"g"),("yangbaechu_mart",9,"g"),("kv_232",6,"g"),("sauce_burger",20,"g")]),
 ("아메리카노","americano","1잔", r"아메리카노|메리카노",
   [("coffee_bean",18,"g"),("takeout_cup",1,"개")]),
 ("카페라떼","caffe-latte","1잔", r"라떼",
   [("coffee_bean",18,"g"),("milk",200,"ml"),("takeout_cup",1,"개")]),
 ("초밥","sushi","10피스", r"초밥|스시",
   [("rice_uncooked",90,"g"),("salmon_raw",60,"g"),("white_fish_raw",60,"g"),("sushi_sauce_rice",20,"g")]),
 ("샐러드","salad","1인분", r"샐러드|샐러디|웜볼|랩$",
   [("salad_greens",150,"g"),("chicken_breast",80,"g"),("sauce_oriental",30,"g")]),
 ("포케","poke","1인분", r"포케",
   [("rice_uncooked",100,"g"),("salmon_raw",80,"g"),("kv_245",40,"g"),("yangbaechu_mart",24,"g"),("kv_232",16,"g"),("sauce_poke",30,"g")]),
 ("무뼈닭발","dakbal","1인분", r"닭발",
   [("chicken_feet",250,"g"),("sauce_normal",60,"g")]),
 ("곱창구이","gopchang","1인분(200g)", r"곱창|대창|막창|특양",
   [("x_c213e61e77",200,"g"),("kv_245",25,"g"),("yangbaechu_mart",15,"g"),("kv_232",10,"g")]),
 ("핫도그","hotdog","1개", r"핫도그",
   [("hotdog_bread",1,"개"),("vienna_sausage",40,"g"),("frying_powder",40,"g"),("frying_oil",20,"ml")]),
 ("와플","waffle","1개", r"와플",
   [("x_ccdd24c035",80,"g"),("cream_fresh",40,"ml")]),
 ("감자탕","gamjatang","2인분", r"감자탕",
   [("x_2458074f8e",700,"g"),("x_a2f018ad7b",150,"g"),("kv_152",200,"g"),("soup_base_korean",40,"g"),("kv_248",20,"g")]),
 ("삼계탕","samgyetang","1인분", r"삼계탕|백숙",
   [("raw_chicken_10",800,"g"),("rice_uncooked",50,"g"),("kv_258",20,"g"),("kv_246",30,"g")]),
 ("갈비탕","galbitang","1인분", r"갈비탕",
   [("beef_stew",250,"g"),("mu_mart",100,"g"),("dangmyeon",30,"g"),("kv_246",30,"g")]),
 ("육개장","yukgaejang","1인분", r"육개장",
   [("beef_stew",150,"g"),("sukju_mart",80,"g"),("kv_246",60,"g"),("kv_248",20,"g"),("x_571aff06f4",400,"g")]),
 ("순두부찌개","sundubu-jjigae","1인분", r"순두부",
   [("x_cee737406a",250,"g"),("x_05a19b44fc",50,"g"),("kv_248",15,"g"),("egg_fresh",1,"개"),("x_571aff06f4",300,"g")]),
 ("된장찌개","doenjang-jjigae","1인분", r"된장찌개",
   [("soup_base_korean",40,"g"),("x_cee737406a",150,"g"),("kv_152",80,"g"),("kv_245",60,"g"),("x_571aff06f4",300,"g")]),
 ("미역국","miyeokguk","2인분", r"미역국",
   [("kv_642",20,"g"),("beef_stew",100,"g"),("x_571aff06f4",800,"g")]),
 ("물냉면","mul-naengmyeon","1인분", r"물냉면|냉면",
   [("soba_noodles",150,"g"),("beef_stew",60,"g"),("kv_223",50,"g"),("egg_fresh",1,"개"),("mu_mart",50,"g")]),
 ("비빔냉면","bibim-naengmyeon","1인분", r"비빔냉면",
   [("soba_noodles",150,"g"),("beef_stew",50,"g"),("kv_223",50,"g"),("egg_fresh",1,"개"),("cg_gochujang",40,"g")]),
 ("크림파스타","cream-pasta","1인분", r"까르보나라|크림파스타|알프레도",
   [("x_spaghetti",100,"g"),("cream_fresh",150,"ml"),("x_0ebb70edeb",50,"g"),("mozzarella_cheese",30,"g"),("kv_245",40,"g")]),
 ("토마토파스타","tomato-pasta","1인분", r"토마토파스타|아라비아타|마리나라",
   [("x_spaghetti",100,"g"),("pizza_sauce",150,"g"),("kv_245",50,"g"),("kv_258",10,"g"),("mozzarella_cheese",20,"g")]),
 ("칼국수","kalguksu","1인분", r"칼국수",
   # aehobak_mart: kv_224는 KAMIS 개당 시세(단위 '개')라 g 계산 불가(2026-07-20 분리).
   # 소매 6,600=이마트 1,980원/개 ÷ 300g(개당 중량 가정), 도매 1,295=가락 경매.
   [("x_kalguksu",180,"g"),("kv_152",80,"g"),("aehobak_mart",60,"g"),("kv_661",80,"g"),("kv_246",20,"g")]),
 ("잔치국수","janchi-guksu","1인분", r"잔치국수",
   [("cg_noodle_somyeon",120,"g"),("egg_fresh",1,"개"),("kv_246",20,"g"),("kv_642",5,"g"),("x_571aff06f4",500,"g")]),
 ("콩국수","kongguksu","1인분", r"콩국수",
   [("cg_noodle_somyeon",120,"g"),("kv_141",120,"g"),("kv_223",40,"g")]),
 ("삼겹살구이","samgyeopsal","1인분", r"삼겹살(?!살)|생삼겹",
   [("pork_belly_import",200,"g"),("sauce_ssamjang",30,"g"),("kv_214",50,"g"),("kv_258",20,"g")]),
 ("찜닭","jjimdak","2인분", r"찜닭|안동찜닭",
   [("raw_chicken_10",800,"g"),("dangmyeon",100,"g"),("kv_152",150,"g"),("kv_232",80,"g"),("sauce_bulgogi",80,"g")]),
 ("닭갈비","dakgalbi","1인분", r"닭갈비",
   [("chicken_parts",250,"g"),("sauce_dakgalbi",60,"g"),("tteok",80,"g"),("baechu_mart",100,"g"),("yangbaechu_mart",80,"g")]),
 ("비빔밥","bibimbap","1인분", r"비빔밥",
   [("rice_uncooked",100,"g"),("beef_patty",60,"g"),("kongnamul_mart",50,"g"),("kv_213",50,"g"),("kv_232",40,"g"),("egg_fresh",1,"개"),("cg_gochujang",30,"g")]),
 ("볶음밥","bokkeumbap","1인분", r"볶음밥",
   [("rice_uncooked",120,"g"),("egg_fresh",1,"개"),("kv_245",50,"g"),("kv_232",30,"g"),("frying_oil",15,"ml")]),
 ("오므라이스","omurice","1인분", r"오므라이스",
   [("rice_uncooked",120,"g"),("egg_fresh",2,"개"),("kv_245",50,"g"),("pizza_sauce",40,"g"),("beef_patty",40,"g")]),
 ("낙지볶음","nakji-bokkeum","1인분", r"낙지볶음|낙지",
   [("kv_664",180,"g"),("kv_245",60,"g"),("kv_246",30,"g"),("cg_gochujang",40,"g"),("kv_248",15,"g")]),
 ("잡채","japchae","2인분", r"잡채",
   [("dangmyeon",150,"g"),("beef_slices",80,"g"),("kv_213",60,"g"),("kv_232",50,"g"),("kv_245",60,"g"),("sauce_bulgogi",50,"g")]),
 ("만두","mandu","1인분(10개)", r"^만두|군만두|물만두",
   [("x_15a5ea19ad",120,"g"),("x_e6d782c93c",150,"g"),("frying_oil",20,"ml")]),
 ("스테이크","steak","1인분", r"스테이크(?!덮밥)|등심스테이크",
   [("kv_4401",200,"g"),("kv_152",100,"g"),("aehobak_mart",60,"g"),("frying_oil",15,"ml")]),
 ("갈비찜","galbijjim","2인분", r"갈비찜",
   # hanwoo_galbi: ek_beef_갈비(경락=도매)를 소매칸에 쓰던 버그 분리(2026-07-20).
   # 소매 70,400=축평원 소비자가(1+ 7,040/100g), 도매 22,429=경락 스냅샷. ek_*는 시세 전용.
   [("hanwoo_galbi",600,"g"),("mu_mart",100,"g"),("kv_232",80,"g"),("sauce_bulgogi",100,"g")]),
 ("해물찜","haemul-jjim",  "2인분", r"해물찜|아구찜|아귀찜",
   [("seafood_mix",400,"g"),("kongnamul_mart",200,"g"),("cg_gochujang",60,"g"),("kv_248",25,"g")]),
 ("물회","mulhoe","1인분", r"물회",
   [("white_fish_raw",120,"g"),("kv_223",60,"g"),("baechu_mart",50,"g"),("cg_gochujang",50,"g")]),
 ("우동","udon","1인분", r"^우동|가락우동",
   [("x_97a2a65b3a",200,"g"),("x_8266d126cb",30,"g"),("egg_fresh",1,"개"),("kv_246",20,"g")]),
 ("라면","ramyeon","1인분", r"^라면|라볶이",
   [("noodles_ramen",1,"개"),("egg_fresh",1,"개"),("kv_246",20,"g")]),
 ("막국수","makguksu","1인분", r"막국수",
   [("soba_noodles",150,"g"),("kv_223",50,"g"),("baechu_mart",50,"g"),("cg_gochujang",40,"g")]),
 ("제육덮밥","jeyuk-deopbap","1인분", r"제육덮밥|덮밥",
   [("rice_uncooked",120,"g"),("x_1294333d76",150,"g"),("sauce_jeyuk",40,"g"),("kv_245",50,"g")]),
 ("순대볶음","sundae-bokkeum","1인분", r"순대볶음|순대곱창",
   [("x_a0ada5ee05",200,"g"),("tteok",60,"g"),("baechu_mart",80,"g"),("cg_gochujang",40,"g")]),
 ("고등어구이","godeungeo-gui","1인분", r"고등어구이|생선구이",
   # godeungeo_mart: kv_611은 KAMIS 마리당 시세(단위 '마리')라 g 계산 불가(2026-07-20 분리).
   # 소매 17,390=이마트 자반 1kg, 도매 7,495=노르웨이 냉동 20kg 벌크.
   [("godeungeo_mart",200,"g"),("frying_oil",10,"ml")]),
 ("빙수","bingsu","1그릇", r"설빙$|빙수|인절미설빙|메론설빙|치즈설빙|브라우니설빙",
   [("milk",400,"ml"),("x_40dd9f7f0d",80,"g"),("x_cb52df78e9",30,"g"),("x_52d5d550ac",50,"g")]),
]

# 매칭 우선순위: 리스트 순서(먼저 맞으면 그 dish). 버거를 불고기보다 먼저 처리하도록 순서 조정
ORDER = [d[0] for d in DISHES]

PRIORITY = ["햄버거","로제떡볶이","떡볶이","양념치킨","간장치킨","후라이드치킨"]  # 겹침 조정

# 포장(판매) 단위: key → (base_unit 기준 수량, 표기). 시판제품은 이름에서 자동 파싱, 그 외 기본값.
# 요리의 정체성을 만드는 재료 — 소스·가루여도 **메인**으로 올린다(2026-07-20 사용자 지시).
#  "청정원 중화춘장이 짜장면 메인인데 왜 집에 있을 만한 것으로 내려가나"
MAIN_KEYS = {
 "jjajangmyeon": ("sauce_jjajang",),
 "fried-chicken": ("frying_powder",), "yangnyeom-chicken": ("frying_powder", "sauce_yangnyeom"),
 "ganjang-chicken": ("frying_powder",),
 "tteokbokki": ("sauce_tteokbokki",), "rose-tteokbokki": ("sauce_rose",),
 "tangsuyuk": ("frying_powder", "sauce_tangsu"), "donkatsu": ("frying_powder", "sauce_donkatsu"),
 "malatang": ("sauce_mala",), "malaxiangguo": ("sauce_mala",),
 "kimchi-jjigae": ("kimchi_fresh", "sauce_kimchi"), "budae-jjigae": ("sauce_budae",),
 "jeyuk-bokkeum": ("sauce_jeyuk",), "dakgalbi": ("sauce_dakgalbi",),
 "bulgogi": ("sauce_bulgogi",), "japchae": ("sauce_bulgogi",),
 "buncha": ("sauce_nuoccham",), "poke": ("sauce_poke",), "salad": ("sauce_oriental",),
 "burger": ("sauce_burger",), "pizza": ("pizza_sauce",), "hotdog": ("frying_powder",),
 "sushi": ("sushi_sauce_rice",), "americano": ("coffee_bean",), "caffe-latte": ("coffee_bean",),
 "waffle": ("x_ccdd24c035",), "bingsu": ("x_40dd9f7f0d",),
}

# 없을 때 대체 안내 — "집에 없으면 이렇게 해도 된다"를 알려준다(사용자 지시).
SUBST = {
 "frying_powder": "없으면 밀가루 7 : 전분 3으로 섞어 써도 돼요",
 "x_80310d61c8": "감자전분 대신 옥수수전분도 괜찮아요",
 "garlic_minced": "생마늘을 다져 써도 돼요",
 "milk": "우유 대신 찬물에 20분 담가도 잡내가 빠져요",
 "cg_soy_sauce_jin": "국간장 말고 진간장이어야 색이 진하게 나와요",
 "sauce_jjajang": "춘장은 짜장 맛의 핵심이라 대체가 어려워요",
}

PACK = {
 "raw_chicken_10":(1.0,"생닭 1마리(1kg)"),"burger_bun":(6,"6개입"),"hotdog_bread":(6,"6개입"),
 "takeout_cup":(20,"20세트"),"egg_fresh":(30,"특란 30구"),"milk":(0.9,"900ml"),
 "frying_oil":(0.9,"900ml"),"cream_fresh":(0.5,"500ml"),"noodles_ramen":(0.5,"사리 5개"),
 "x_cee737406a":(0.3,"두부 1모"),"gim":(0.025,"김밥김 10장"),"pizza_dough":(0.25,"도우 1장"),
 "salad_greens":(0.15,"샐러드채소 1봉"),"coffee_bean":(0.2,"원두 200g"),"noodles_fresh":(0.4,"생면 2인분"),
 "noodles_rice":(0.4,"건면 400g"),"tteok":(0.5,"떡 500g"),"fish_cake":(0.5,"어묵 500g"),
 "vegetables_fresh":(0.5,"모둠채소 500g"),"kimchi_fresh":(1.0,"포기김치 1kg"),
 "pork_trotter":(1.0,"장족 1kg"),"chicken_breast":(1.0,"냉동 1kg"),"rice_uncooked":(1.0,"쌀 1kg"),
 "x_2458074f8e":(1.0,"등뼈 1kg"),"frying_powder":(1.0,"튀김가루 1kg"),"pepperoni":(0.2,"페퍼로니 200g"),
 "mozzarella_cheese":(0.4,"피자치즈 400g"),
 # 짜장면 재료 포장단위 (2026-07-20 조사)
 "garlic_minced":(0.5,"다진마늘 500g"),"x_e6d782c93c":(0.5,"다짐육 500g"),
 "cg_cooking_oil":(0.9,"식용유 900ml"),"cg_sugar_white":(1.0,"설탕 1kg"),
 "cg_soy_sauce_jin":(0.86,"진간장 860ml"),"x_80310d61c8":(0.5,"전분 500g"),
 "sauce_jjajang":(0.25,"춘장 250g"),"kv_152":(1.0,"감자 1kg"),
 "aehobak_mart":(0.3,"애호박 1개"),"water":(999,"수돗물"),
}

# dish → 밀키트 (2026-07 조사: data/research/sauceresearch_*.json 기반. 가격 변동 가능)
MEALKIT = {
 "떡볶이": ("오뚜기 컵떡볶이/즉석떡볶이", "1인", 3000),
 "로제떡볶이": ("석관동떡볶이 로제떡볶이 밀키트", "2인", 12900),
 "마라탕": ("하이디라오 마라탕 밀키트", "2인", 15900),
 "마라샹궈": ("하이디라오 마라샹궈 밀키트", "2인", 16900),
 "짜장면": ("울아빠짜장 수제 짜장소스 밀키트 250g×3", "6인", 12900),
 "짬뽕": ("보배반점 중화 해물 짬뽕 밀키트", "2인", 13205),
 "탕수육": ("냉동 탕수육 완제품(소스 동봉) 600g", "2~3인", 9900),
 "김치찌개": ("비비고 돼지고기 김치찌개 460g", "2인", 6980),
 "부대찌개": ("햄가득 부대찌개 밀키트", "2인", 13900),
 "불고기": ("소불고기 밀키트(야채 포함)", "2인", 12900),
 "제육볶음": ("제육볶음 밀키트(고기+양념)", "2인", 11900),
 "돈까스": ("쉐푸드 등심 통돈까스 300g×2", "2인", 9480),
 "샐러드": ("프레시지 시저 샐러드 키트", "1인", 6900),
 "포케": ("연어 포케 밀키트", "1인", 8900),
 "분짜": ("프레시지 오리엔탈 분짜", "1인", 8900),
 "양념치킨": ("CJ 고메 소바바치킨 양념순살 240g", "1~2인", 5980),
 "간장치킨": ("CJ 고메 소바바치킨 소이허니 375g", "1~2인", 7000),
 "족발": ("자연과농부 마늘족발 350g", "1인", 9900),
 "햄버거": ("수제버거 밀키트(패티+번+소스)", "1~2인", 9900),
 "순대국밥": ("순대국밥 밀키트(순대+내장+육수)", "2인", 13900),
 "닭갈비": ("우마왕 춘천닭갈비 700g×3", "6인", 23900),
}

# 요리별 아이콘 (Claude Design 기준) — dish 상세·요리사전 공용, 루프보다 먼저 정의
ICON = {
 "후라이드치킨":"🍗","양념치킨":"🍗","간장치킨":"🍗",
 "떡볶이":"🥘","로제떡볶이":"🥘","김밥":"🍙","핫도그":"🌭",
 "짜장면":"🍜","짬뽕":"🍜","탕수육":"🍤","마라탕":"🌶️","마라샹궈":"🌶️","쌀국수":"🍜","분짜":"🍜",
 "김치찌개":"🍲","부대찌개":"🍲","순대국밥":"🍚","뼈해장국":"🍚","설렁탕·곰탕":"🍚",
 "불고기":"🍚","제육볶음":"🍚","족발":"🥓","보쌈":"🥓","곱창구이":"🔥","무뼈닭발":"🌶️",
 "돈까스":"🍤","초밥":"🍣","피자":"🍕","햄버거":"🍔",
 "샐러드":"🥗","포케":"🥗","아메리카노":"☕","카페라떼":"☕","와플":"🧇","빙수":"🍧",
}

# 배민식 카테고리 묶음 + 검색
# 🔴 요리를 추가하면 **반드시 여기에도 넣어야** 목록 페이지에 뜬다.
#    빠뜨리면 페이지는 생성되는데 어디서도 링크되지 않는 고아 페이지가 된다
#    (healthcheck '어디서도 링크 안 되는 발행 페이지'가 실제로 16건 잡아냈다, 2026-07-20).
DISH_CAT = {
 "치킨":["후라이드치킨","양념치킨","간장치킨","찜닭","닭갈비"],
 "분식":["떡볶이","로제떡볶이","김밥","핫도그","만두","잔치국수","칼국수","콩국수"],
 "중식·아시안":["짜장면","짬뽕","탕수육","마라탕","마라샹궈","쌀국수","분짜"],
 "한식":["김치찌개","부대찌개","된장찌개","순두부찌개","순대국밥","뼈해장국","감자탕","설렁탕·곰탕",
        "갈비탕","삼계탕","육개장","미역국","불고기","제육볶음","족발","보쌈","삼겹살구이",
        "곱창구이","무뼈닭발","낙지볶음","잡채","비빔밥","볶음밥","갈비찜","해물찜",
        "물회","제육덮밥","순대볶음","고등어구이"],
 "면·냉면":["물냉면","비빔냉면","크림파스타","토마토파스타","우동","라면","막국수"],
 "일식·양식":["돈까스","초밥","피자","햄버거","오므라이스","스테이크"],
 "샐러드":["샐러드","포케"],
 "카페·디저트":["아메리카노","카페라떼","와플","빙수"],
}

