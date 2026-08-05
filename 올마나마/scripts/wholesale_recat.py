# -*- coding: utf-8 -*-
"""근거가 «계수 곱하기»·«미트박스» 인 도매가를 **식봄 카테고리 실값**으로 바꾼다. (2026-08-01 신설)

    python scripts/wholesale_recat.py             # 무엇으로 바뀌는지 보기만 (기본)
    python scripts/wholesale_recat.py --apply     # DB 반영
    python scripts/wholesale_recat.py --only sauce_normal x_80310d61c8
    python scripts/wholesale_recat.py --cache     # 새로 안 받고 캐시(07-25)로만

🔴 **왜 만들었나**
   메뉴에 쓰이는 재료 210종 중 36종의 도매가가 «소매값 × 0.8» 이거나 «미트박스» 였다.
   · 계수는 근거가 아니라 추측이다. 반박당하면 못 버틴다.
   · 미트박스는 2026-07-27에 **식봄으로 방침을 바꿨는데** 6종이 남아 있었다.

🔴 **왜 검색이 아니라 카테고리(nid)인가**
   이름으로 식봄을 검색하면 «모차렐라 치즈→치즈떡», «불고기용→맛술 혼미린» 이 잡힌다.
   카테고리가 품목을 묶어주니 다른 물건이 애초에 들어올 수 없다. (`데이터소스와스크립트.md`)

🔴 **`pack_kg` 는 여기 있는 것을 쓴다 — 공통모듈 원본을 그대로 믿지 말 것**
   `공통모듈\foodspring\foodspring_collect.py` 에 `pack_kg` 가 **두 번** 정의돼 있고
   나중 것(옛 파서)이 이긴다. 그래서 «5kg2팩» 배수가 안 읽힌다(2026-08-01 확인).
   여기 실린 파서는 `foodspring_repair_cache.py` 의 고쳐진 쪽을 복사한 것이다.
   ⚠️ 공통모듈 규칙대로 **import 하지 않고 복사**한다.

🔴 **못 고르면 비운다.** 애매한 재료는 `UNSURE` 에 이유와 함께 남기고 손대지 않는다.
   틀린 카테고리를 붙이느니 계수인 채로 두는 게 낫다 — 최소한 «추측» 이라고 적혀는 있다.
"""
import argparse
import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SB = os.path.join(BASE, "data", "research", "foodspring")
NIDMAP = os.path.join(SB, "_가공nid.json")
OUT = os.path.join(SB, "_recat.json")
API = "https://api.foodspring.co.kr/v2/graphql"
GAP = 2.0
sys.stdout.reconfigure(encoding="utf-8")

# ── 중량 파서 (foodspring_repair_cache.py 의 고쳐진 것을 복사) ──────────────
_UNIT_KG = {"kg": 1.0, "g": 0.001, "l": 1.0, "ml": 0.001}
_MULT = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*x×]?\s*(\d+)\s*(?:팩|입|봉|개|ea)", re.I)
_BOX = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*/\s*(?:box|박스|비닐|팩)", re.I)
_PAREN = re.compile(r"[(\[]\s*(?:총\s*)?(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[)\]]", re.I)
_HINT = re.compile(r"[*x×]\s*\d+\s*(?:팩|입|봉|개|ea)|box|박스", re.I)
KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I)
G = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I)
L = re.compile(r"(\d+(?:\.\d+)?)\s*(?:l|ℓ|리터)\b", re.I)
ML = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ml|㎖)\b", re.I)
# 🔴 «1봉 가격»·«낱개 가격» 처럼 **가격 기준이 낱개**라고 이름에 적힌 것.
#    이게 있으면 총량 배수를 쓰면 안 된다 — 2026-08-01에
#    「BOX_고구마치즈고로케 600gx12봉_1봉 가격」 을 7.2kg 으로 읽어 722원/kg 이 됐다(실제 8,667원).
_PER_UNIT = re.compile(r"(?:1|한)\s*(?:봉|팩|개|입|ea)\s*(?:당\s*)?가격|낱개\s*가격|개당\s*가격", re.I)


def pack_kg(name):
    """상품명에서 **총 중량(kg)** 을 뽑는다. 후보 중 **가장 큰 값** — 총량은 늘 부분량보다 크다.

    단, 이름이 «1봉 가격» 이라고 말하면 그 말을 따른다(총량으로 나누면 12배 싸진다).
    """
    n = (name or "").replace(",", "")
    per_unit = bool(_PER_UNIT.search(n))
    cands = []
    if not per_unit:
        m = _MULT.search(n)
        if m:
            base = float(m.group(1)) * _UNIT_KG[m.group(2).lower()]
            cands.append((base * int(m.group(3)), "배수"))
        m = _BOX.search(n)
        if m:
            cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "BOX총량"))
        m = _PAREN.search(n)
        if m:
            cands.append((float(m.group(1)) * _UNIT_KG[m.group(2).lower()], "괄호총량"))
    if cands:
        return max(cands)
    m = KG.search(n)
    if m:
        return float(m.group(1)), "단일kg" + ("·1봉가" if per_unit else "")
    m = G.search(n)
    if m:
        return float(m.group(1)) / 1000.0, "단일g" + ("·1봉가" if per_unit else "")
    #  액체는 1L≈1kg 로 본다. 이게 없어서 「사골육수 1.8L」 4건이 0원/kg 이 됐다(2026-08-01)
    m = L.search(n)
    if m:
        return float(m.group(1)), "단일L"
    m = ML.search(n)
    if m:
        return float(m.group(1)) / 1000.0, "단일ml"
    return None, None


# ── 후보에서 뺄 것 ────────────────────────────────────────────────────────
#  카테고리 안이라도 «다른 물건» 이 섞인다. 정육 필터는 meat_price_table.py 와 같은 규칙.
BAD = re.compile(r"세트|선물|샘플|증정|사은품|체험|맛보기|기획전|이벤트")
#  🔴 «스프» 는 뒤에 «링» 이 오면 상호명이다 — 2026-08-01에 「돈등심_캐나다_원물_22kg_**스프링힐**」이
#     BAD «스프» 로 잘렸다. 원물 6,800원짜리가 통째로 후보에서 빠졌다.
BAD_MEAT = re.compile(r"세트|선물|샘플|양념|훈제|햄|소시지|만두|까스|너겟|볶음밥|찌개|스프(?!링)|육수|다시|"
                      r"엑기스|우거지|곰탕|사골탕|설렁탕|국밥|탕수?육|꿔바로우|샤브|지방|우지|기름|"
                      r"염통|무침|육포|장조림|불고기양념|떡갈비")
BLOCK = {"돼지": re.compile(r"소[고기]|우[육양]|육우|한우|쇠고기"),
         "소": re.compile(r"돼지|돈[육민등항목삼갈사]|포크"),
         "닭": re.compile(r"돼지|소고기|우육")}
PLAUS = {"돼지": (1500, 20000), "소": (3000, 90000), "닭": (2000, 15000)}

# 정육 카테고리 nid — meat_price_table.py 에서 그대로 가져온다(거기가 정본)
PORK = {"삼겹살": {"국산": [520, 530], "수입": [548, 564]},
        "앞다리": {"국산": [511, 527], "수입": [560, 572]},
        "등심": {"국산": [509, 529], "수입": [559, 576]},
        "목심": {"국산": [524, 537], "수입": [552, 574]},
        "다짐육": {"국산": [528], "수입": [578]},
        "돈등뼈": {"국산": [513, 536], "수입": [557, 577]}}
BEEF = {"다짐육": {"수입": [610]},
        "양지": {"수입": [603, 617]},
        "차돌박이": {"수입": [599, 611]},
        "전각(불고기감)": {"수입": [613]}}

# ── 배정표 ───────────────────────────────────────────────────────────────
#  「이 재료는 식봄 어느 카테고리에서, 이름에 무엇이 든 것을 찾을 것인가」. 사람이 정한다.
#  ("cat", 경로, [이름에 반드시 들어갈 말]) · ("meat", 축종, 부위, 원산지)
#  ⚠️ 키워드를 비우면 카테고리 최저가가 그냥 잡힌다 — 2026-08-01에 그렇게 해서
#     「떡볶이 양념 = 돼지갈비양념장」 이 나왔다. 가공품은 키워드를 반드시 준다.
MAP = {
    # ── 소스·드레싱 ──
    "x_b22d1fbcbd":     ("cat", "기타 소스류>기타 소스류", [["탕수"]]),          # 허브탕수소스
    "sauce_balsamic":   ("cat", "마요네즈.드레싱>드레싱", [["발사믹"]]),
    "x_ff21430c11":     ("cat", "마요네즈.드레싱>드레싱", [["렌치", "랜치", "스리라차"]]),
    "x_16dcf5fc04":     ("cat", "머스타드.칠리.데리야끼>칠리", [["칠리"]]),      # 크리미칠리
    # ── 육수·조미 ──
    # 🔴 우리 「사골육수 베이스」는 **20배 희석하는 농축액**이다(기존 근거에 그렇게 적혀 있다).
    #    「사골」만 키워드로 주면 바로 쓰는 «면사랑 사골육수 1.8L» 가 잡혀 값이 2.5배로 튄다.
    #    희석 배수가 다른 물건은 같은 재료가 아니다 — 농축·엑기스만 받는다.
    "x_40dd9ec644":     ("cat", "소금.다시다.미원>다시다", [["다시"]]),          # 얼큰다시
    # ── 가루·시럽 ──
    "x_80310d61c8":     ("cat", "밀가루.요리가루.전분>전분", [["전분"]]),
    "x_024d11c694":     ("cat", "잼.꿀.버터.시럽>시럽", [["초코", "초콜"]]),        # 초콜릿시럽
    # ── 기타 가공 ──
    "x_d651ee86ce":     ("cat", "튀김류.냉동식품>고로케", [["고로케", "크로켓"]]),   # 고로케반죽
    "x_21090553e7":     ("cat", "훈제.식육가공류>베이컨", [["베이컨"]]),          # 훈제베이컨칩
    # ── 정육 (미트박스 → 식봄) ──
    "beef_patty":       ("meat", "소", "다짐육", "수입"),
    "x_ffd92fa2a9":     ("meat", "소", "다짐육", "수입"),        # 소다짐육
    "x_chadol":         ("meat", "소", "차돌박이", "수입"),
    "beef_bulgogi":     ("meat", "소", "전각(불고기감)", "수입"),
    # ── 정육 (계수 → 식봄) ──
    "x_118ff29a25":     ("meat", "돼지", "다짐육", "수입"),      # 돈육다짐만두소
    "x_2458074f8e":     ("meat", "돼지", "돈등뼈", "수입"),      # 감자탕돈뼈
}

# ── 사람이 상품을 직접 지정한 것 ───────────────────────────────────────────
#  🔴 카테고리 최저가로 안 되는 것들이 있다. 재료명이 **특정 제품**이거나(「친수 느억맘 소스 500g」),
#     품목이 카테고리 안에서 이름으로만 갈리는 경우다. 이건 사람이 검색해서 고른다.
#     ⚠️ 검색은 **카테고리로 안 될 때만.** 먼저 검색하면 임박상품·다른 품목이 잡힌다.
#  (2026-08-01 조사. 값은 조사일 기준 — 시세라 바뀐다)
PICKED = {
    "sauce_padthai":  (5760,  "PANTAI 팟타이소스 5L/EA 28,800원",
                       "「팟타이」 24건 중 L당 최저. 청정원 380g 은 식봄에 없다"),
    "sauce_nuoccham": (8060,  "친수 베트남피쉬소스(느억맘 500g/EA) 4,030원",
                       "재료명과 **같은 브랜드·같은 규격**. 「느억맘」 20건"),
    "gim":            (45833, "꼬마 김밥김 240g(200매) 2절 절단김 업소용 11,000원",
                       "김은 250g 에 100매다. 1kg 은 400매라 «대용량» 기준이 다르다"),
    "x_40dd9f7f0d":   (3233,  "리치스 통단팥 3kg 9,700원",
                       "설빙 팥인절미설빙은 앙금이 아니라 **통단팥**"),
    "sp_0aa832a814":  (6733,  "무순 (150g/EA) 1,010원",
                       "「무순」 53건. 150g 이 업소 규격"),
    # 🔴 아래 5종은 «식봄에 없다» 고 결론냈다가 **검색어를 바꾸니 나온 것들**이다(2026-08-01 대표 지적:
    #    "지금 나오는거 다 말장난이야 조금만 변형해서 생각해"). 재료명 그대로 치지 말 것.
    #      바바리안커스터드 → 「슈크림」 으로 치니 **상품명에 «바바리안» 이 그대로** 있었다
    #      시저와사비 → 「시저드레싱」 은 230ml 뿐, 「시저」 로 치니 2kg 업소용이 나왔다
    "x_5c2550a90f":   (2427,  "신진 바바리안 슈크림 필링 3kg 7,280원",
                       "「슈크림」 73건. 재료명 «바바리안» 이 상품명에 그대로 있다"),
    "x_73d12e71cb":   (3800,  "이츠웰 시저드레싱(The맛있는 2Kg/EA) 7,600원",
                       "「시저드레싱」은 230ml 뿐 → 「시저」 로 치니 2kg 업소용이 나왔다"),
    "x_b1ea1c0f4b":   (5200,  "스위티코리아 허니꿀짱 1kg 5,200원",
                       "「허니시럽」 43건. 꿀 원물(벌꿀 2.4kg 2,133원/kg)이 아니라 시럽 제품"),
    "beef_stew":      (15060, "♥정육특가♥ 소양지(호주산 냉동 500g 덩어리 1kg/EA) 15,060원",
                       "카테고리 최저와 「우양지」·「양지 덩어리」 검색 결과가 일치"),
    "pork_loin_donkasu": (6800, "[냉동] 돼지등심_캐나다_원물_1kg_하이라이프 6,800원",
                       "수입 원물 최저. 카테고리가 탕수육용 큐브로 차 있어 검색으로 교차확인"),
    "x_2255eba1be":   (6800,  "[냉동] 돼지등심_캐나다_원물_1kg_하이라이프 6,800원",
                       "등심돈육 — 위와 같은 상품"),
    # 🔴 2차(2026-08-01 오후) — 「고기도 식봄으로」·「족발육수 말고 족발간장으로 쳐봐」 지시로 추가.
    "sauce_jokbal":   (3950,  "소스대통령 족발용 간장육수 10kg 39,500원",
                       "「족발간장」 검색. **우리 근거의 그 상품이 식봄에 그대로** 있었다 — "
                       "×0.8 을 곱할 이유가 없었다(39,500/10kg = 3,950)"),
    "pork_head_meat": (11800, "춘풍접객 국내산 돼지 머릿고기 슬라이스 2kg 23,600원",
                       "쿠팡 → 식봄. 순대국 쇼츠에서 쓴 것과 **같은 상품**"),
    # 🔴 **「육수용 닭발」을 붙이면 안 된다**(2026-08-01). 카테고리 최저는 육수용 2,600원인데
    #    한신포차 한신닭발은 **먹는 닭발**이다. 국물용과 구이용은 같은 부위여도 다른 물건이다.
    "chicken_feet_bone": (6300, "통닭발(뼈있음) 국내산 10kg 냉동 63,000원",
                       "옛 근거가 «조사 고정단가(출처 비공개)» 였다 — 근거가 아니다. "
                       "값은 6,500→6,300 으로 거의 같고 **근거가 생겼다**"),
    "sauce_dakgalbi": (3261,  "본테이스트 닭갈비양념장 2.3kg 7,500원",
                       "네이버 쇼핑API 종료 → 식봄. 옛 값은 소매 180g 병 기준이라 4.5배 비쌌다"),
    "malatang_base":  (6960,  "이츠웰 사골엑기스(1Kg/EA) 6,960원",
                       "대상 사골육수베이스는 **20배 농축**(대표 확인·웹 확인). "
                       "식봄엔 그만큼 싼 농축액이 없어 최저가 채택"),
    "sauce_poke":     (4000,  "사조대림 오리엔탈 드레싱 (2kg) 샐러드 포케 소스 8,000원",
                       "포케올데이 소스는 3종뿐(렌치스리라차·시저와사비·포케소스). "
                       "식봄이 «포케 소스» 로 파는 오리엔탈 드레싱이 최저"),
    # 🔴 3차(2026-08-01) — 네이버 쇼핑API 종료로 재조사 경로가 없어진 것들을 식봄으로 옮긴다.
    "sauce_ssamjang": (1810,  "★초특가★황금찬 양념쌈장(지함 14Kg/EA) 25,340원",
                       "보쌈 4메뉴. 옛 값은 소매 500g 병 기준이라 5.6배 비쌌다"),
    "sauce_budae":    (5320,  "쉐프원 부대찌개양념 2kg 10,640원",
                       "옛 근거가 «CJ 다담 부대찌개 양념 140g» — 소매 소포장이었다"),
    "x_52d5d550ac":   (7500,  "한입만 도시락떡 인절미 800g 6,000원",
                       "설빙 3메뉴. ⚠️ 「800g * 20」의 20은 총량이 아니라 **최소주문수량**이다 — "
                       "같은 상품이 ×20·×10·×5 로 나오는데 값은 6,000~8,300원뿐"),
    #  ⚠️ 원산지를 정해야 하는 것 — 중국산 1,300원 / 국내산 2,680원. 김치찌개 전문점이라 국내산으로 잡는다
    "kimchi_fresh":   (2680,  "남도 포기김치 10kg 배추김치 국내산 26,800원",
                       "백채김치찌개 3메뉴. **국내산 기준**(중국산은 1,300~1,520원). "
                       "브랜드가 원산지를 밝히면 그때 바꿀 것"),
    #  ⚠️ 용도가 섞여 있다 — 베이킹(롤케익·크림빵)과 요리(로제떡볶이·뇨끼피자)가 한 재료다
    "cream_fresh":    (4500,  "밀락 쿠킹크림 (요리용) 1L 냉장유크림 4,500원",
                       "8메뉴 중 6개가 로제떡볶이·마라샹궈·뇨끼피자 같은 **요리용**이다. "
                       "동물성 생크림(칸디아 9,600원)은 베이킹용이라 2배 비싸다 — 용도를 쪼개야 한다"),
    "sp_2ca2668d33":  (5600,  "[무료배송] 바로푸드 고구마크러스트 고구마무스 1kg 냉장 5,600원",
                       "샐러디 탄단지샐러디에 들어가는 건 **고구마 무스**다(대표 확인). "
                       "「스윗포테이토」로 치면 고구마프라이만 나온다"),
}

# 🔴 **못 고르겠는 것은 손대지 않는다.** 이유를 남긴다 — 다음 사람이 판단할 수 있게.
UNSURE = {
    # 🔴 sauce_normal 은 **사는 물건이 아니다**(2026-08-01 확인). 매장에서 섞는 양념이고
    #    `menu_ingredients.composition` 에 구성이 이미 적혀 있다 —
    #    네네 오리엔탈파닭 «진간장·물엿·대파·참기름» · 한솥 치킨마요 «간장·물엿·마요».
    #    7개 브랜드 12개 메뉴가 이 하나를 공유한다. 식봄에서 완제품을 찾을 대상이 아니라
    #    **구성 재료로 계산**하거나 브랜드별로 쪼개야 한다(→ shared-sauce-ingredients-need-split).
    #  ── ① 자가 양념: 매장에서 섞는다. 완제품을 찾을 대상이 아니다 ──
    "sauce_normal":     "[7브랜드 12메뉴] 진간장·물엿·대파·참기름 / 케첩·머스터드·마요 — 자가 양념",
    "sauce_tteokbokki": "[8메뉴] 고추장·고춧가루·설탕·물엿·진간장·다진마늘 — 자가 양념",
    "sauce_poke":       "[포케올데이 야채만포케] 간장·참기름·미림·스리라차·통깨 — 자가 양념",
    "x_ad6cbb3b0c":     "[고봉민 매운김밥 30g] 고추장 볶음 **소고기**+청양고추 — 자가 조리."
                        " ⚠️ DB 분류가 `축산물/돼지` 인데 실제로는 소고기다",
    #  🔴 이름과 내용이 다르다. 셋이 한 재료에 묶여 있어 어느 쪽으로도 값을 못 정한다.
    "sauce_jokbal":     "[족발 2곳 4메뉴] 간장육수(진간장·물엿·마늘·생강·계피) / 소금구이 기름장 /"
                        " 불족발 고추장양념 — **세 가지가 한 재료에 섞여 있다.** 쪼개야 한다",
    #  ── ② 단위·농축도가 안 맞아 비교가 성립하지 않는 것 ──
    "malatang_base":    "[마라탕·순대국] 대상 사골육수베이스는 **20배 농축**(대표 확인)."
                        " 식봄 농축액 6,960~18,740원/kg 은 농축 배수 표기가 없어 비교 불가",
    "x_09ca761481":     "[바르다김선생 바른김밥 120g] 김밥 속 **전체**를 한 덩어리로 잡았다."
                        " 단무지·시금치·당근·계란·우엉으로 쪼개야 한다",
    "x_98ec9c2144":     "[큰맘할매순대국 순대국(특) 50g] 마늘과 양파 **두 재료를 합쳐놨다**",
    #  ── ④ 식봄에 없는 것 ──
    "x_38168ca271":     "[파리바게트 실키롤케익 350g] 「롤케이크시트」 검색 0건."
                        " 완제품 케이크 350g 을 통째로 시트로 잡은 것 자체가 이상하다",
}


def cat_call(nid, first=80):
    q = ("query($nid:Int!,$sort:GoodsSortKind!,$first:Int!){"
         "goodsCategory(nid:$nid){name goodsList(sort:$sort,first:$first){"
         "totalCount edges{node{name price{salePrice}}}}}}")
    body = json.dumps({"query": q, "variables": {"nid": nid, "sort": "POPULAR_DESC",
                                                 "first": first}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Device-Type": "pc",
        "Accept": "application/json", "Origin": "https://www.foodspring.co.kr",
        "Referer": "https://www.foodspring.co.kr/", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())["data"]["goodsCategory"]
    rows = []
    for e in d["goodsList"]["edges"]:
        n = e["node"]
        sp = (n.get("price") or {}).get("salePrice")
        if not sp or "샘플" in n["name"]:
            continue
        kg, how = pack_kg(n["name"])
        rows.append({"name": n["name"], "sale_price": sp, "pack_kg": kg, "pack_how": how,
                     "won_per_kg": round(sp / kg) if kg else None})
    return d.get("name") or str(nid), rows


MIN_CAND = 3        # 후보가 이보다 적으면 «최저가» 라고 부를 수 없다


def pick(rows, meat_sp=None, kw=None):
    """카테고리 안에서 **가장 싼 원/kg**. (채택행, 후보수, 탈락사유목록) 반환.

    🔴 **중앙값 이상치 필터를 걷어냈다**(2026-08-01). 「중앙값의 0.4배 미만은 파싱 오류」로
       잘랐는데, 카테고리에 **등급이 섞여 있어서**(수입 다짐육 칸에 한우가 들어옴) 중앙값이
       31,134원까지 올라갔고 그 결과 **정상적인 최저가 6,444원이 잘렸다.**
       대신 13,100원짜리가 채택돼 «미트박스보다 77% 비싸다» 는 거짓 결론이 나왔다.
       파싱 오류는 중앙값이 아니라 **`pack_how` 와 이름의 묶음 힌트**로 잡는다.

    🔴 **이름 키워드를 반드시 확인한다.** 카테고리는 «다른 품목이 못 들어오게» 하는 울타리지
       «같은 물건» 을 보장하지 않는다. `기타 소스류` 한 칸에 소스가 수백 종이라
       제일 싼 «돼지갈비양념장» 이 떡볶이양념·팟타이소스·탕수육소스를 전부 먹었다.
       울타리(카테고리) + 품목확인(키워드) **둘 다** 있어야 한다.
    """
    bad = BAD_MEAT if meat_sp else BAD
    cand, drop = [], []
    for r in rows:
        w, nm, kg = r.get("won_per_kg"), r["name"], r.get("pack_kg")
        if not w or not kg:
            continue
        if kg < 0.5:                             # 소포장은 업소 기준이 아니다
            continue
        if bad.search(nm):
            continue
        #  이름에 묶음 표기가 있는데 «단일» 로 읽혔으면 중량을 못 믿는다 → 뺀다
        if (r.get("pack_how") or "").startswith("단일") and _HINT.search(nm):
            drop.append((w, nm, "묶음 표기가 있는데 배수를 못 읽음"))
            continue
        #  kw 는 **묶음의 목록**이다. 묶음끼리는 AND, 묶음 안은 OR.
        #    [["사골"], ["농축","엑기스"]] = 사골이면서 농축이거나 엑기스인 것.
        #    OR 하나로만 두면 「농축」에 «모밀소바소스(5배농축)» 가 걸린다(2026-08-01).
        if kw:
            miss = [g for g in kw if not any(k in nm for k in g)]
            if miss:
                drop.append((w, nm, "이름에 %s 가 없다" % " + ".join("·".join(g) for g in miss)))
                continue
        if meat_sp:
            if BLOCK[meat_sp].search(nm):        # 교차종(돼지 칸에 소고기)
                continue
            lo, hi = PLAUS[meat_sp]
            if not (lo <= w <= hi):
                drop.append((w, nm, "가격이 %s~%s 밖" % (format(lo, ","), format(hi, ","))))
                continue
        cand.append(r)
    if not cand:
        return None, 0, drop
    return min(cand, key=lambda x: x["won_per_kg"]), len(cand), drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--cache", action="store_true", help="새로 안 받고 캐시로만")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()

    nidmap = json.load(io.open(NIDMAP, encoding="utf-8"))
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    info = {r["ingredient_key"]: r for r in c.execute(
        """SELECT i.ingredient_key, i.name, i.base_unit bu, i.wholesale_price wp, i.wholesale_basis wb,
                  (SELECT COUNT(DISTINCT menu_id) FROM menu_ingredients mi
                    WHERE mi.ingredient_key=i.ingredient_key) mn FROM ingredients i""")}

    todo = {k: v for k, v in MAP.items() if not a.only or k in a.only}
    #  필요한 nid 를 먼저 모아 **한 번씩만** 부른다
    need = []
    for k, v in todo.items():
        if v[0] == "cat":
            nid = nidmap.get(v[1])
            if nid:
                need.append(nid)
        else:
            tbl = PORK if v[1] == "돼지" else BEEF
            need += tbl.get(v[2], {}).get(v[3], [])
    need = sorted(set(need))

    pool, catname = {}, {}
    cachefile = os.path.join(SB, "_recat_raw.json")
    if a.cache and os.path.exists(cachefile):
        d = json.load(io.open(cachefile, encoding="utf-8"))
        pool = {int(k): v["rows"] for k, v in d.items()}
        catname = {int(k): v["name"] for k, v in d.items()}
        #  🔴 캐시의 `won_per_kg` 는 **그때의 파서**로 계산된 값이다. 파서를 고쳤으면
        #     다시 계산해야 한다 — 안 그러면 고친 게 반영이 안 된 채 «괜찮아 보인다».
        for rows in pool.values():
            for r in rows:
                kg, how = pack_kg(r["name"])
                r["pack_kg"], r["pack_how"] = kg, how
                r["won_per_kg"] = round(r["sale_price"] / kg) if kg else None
        print("캐시에서 카테고리 %d개 (지금 파서로 단가 재계산)" % len(pool))
    else:
        print("식봄 카테고리 %d개를 새로 받는다 (%.0f초 예상)" % (len(need), len(need) * GAP))
        for i, nid in enumerate(need, 1):
            try:
                nm, rows = cat_call(nid)
            except Exception as e:
                print("  !! nid %s %s" % (nid, e))
                continue
            pool[nid], catname[nid] = rows, nm
            print("  %2d/%d nid %-4s %-16s %3d건" % (i, len(need), nid, nm[:16], len(rows)))
            time.sleep(GAP)
        json.dump({str(k): {"name": catname.get(k, ""), "rows": v} for k, v in pool.items()},
                  io.open(cachefile, "w", encoding="utf-8"), ensure_ascii=False)

    print()
    today = date.today().isoformat()
    plan, fail = [], []
    for k, v in todo.items():
        r = info.get(k)
        if not r:
            continue
        if v[0] == "cat":
            nid = nidmap.get(v[1])
            best, ncand, drop = pick(pool.get(nid, []), kw=v[2] if len(v) > 2 else None)
            label = v[1]
        else:
            tbl = PORK if v[1] == "돼지" else BEEF
            nids = tbl.get(v[2], {}).get(v[3], [])
            rows = [x for n in nids for x in pool.get(n, [])]
            best, ncand, drop = pick(rows, meat_sp=v[1])
            label = "정육 %s %s(%s)" % (v[1], v[2], v[3])
        if not best:
            fail.append((k, r["name"], label, "후보 0건", drop))
            continue
        # 🔴 후보가 2건뿐인데 «최저가» 라고 하면 안 된다 — 2026-08-01에 「양지」 카테고리가
        #    12건 중 필터 통과 2건(나머지는 사골분말·육수엑기스)이었다. 표본이 곧 근거다.
        if ncand < MIN_CAND:
            fail.append((k, r["name"], label, "후보 %d건뿐 — 최저가라 할 수 없다" % ncand, drop))
            continue
        basis = ("식봄 %s %s %s = %s원/kg (후보 %d건 중 최저·중량 %s)"
                 % (label, today, best["name"][:60], format(best["won_per_kg"], ","),
                    ncand, best["pack_how"]))
        plan.append({"k": k, "name": r["name"], "old": r["wp"], "oldwb": (r["wb"] or "")[:30],
                     "new": best["won_per_kg"], "prod": best["name"], "basis": basis,
                     "mn": r["mn"], "cat": label, "n": ncand})

    #  사람이 고른 것 — 카테고리로 안 되는 것들. 근거에 «사람 지정» 을 남긴다
    for k, (won, prod, why) in PICKED.items():
        if a.only and k not in a.only:
            continue
        r = info.get(k)
        if not r:
            continue
        plan.append({"k": k, "name": r["name"], "old": r["wp"], "oldwb": (r["wb"] or "")[:30],
                     "new": won, "prod": prod,
                     "basis": "식봄 %s %s = %s원/kg (사람 지정 — %s)" % (today, prod, format(won, ","), why),
                     "mn": r["mn"], "cat": "검색·사람지정", "n": 0})

    plan.sort(key=lambda x: -x["mn"])
    print("=" * 96)
    print("%-18s %8s → %8s %6s %4s  %s" % ("재료", "지금", "식봄", "변화", "후보", "채택 상품"))
    print("-" * 96)
    for p in plan:
        d = (p["new"] - p["old"]) / p["old"] * 100 if p["old"] else 0
        print("%-18s %8s → %8s %+5.0f%% %4d  %s" % (p["name"][:18], format(p["old"], ","),
                                                    format(p["new"], ","), d, p["n"], p["prod"][:40]))
    print("-" * 96)
    print("바꿀 것 %d종 · 못 고름 %d종 · 손 안 댐 %d종" % (len(plan), len(fail), len(UNSURE)))
    for k, nm, lb, why, drop in fail:
        print("   ✗ %-16s %s — %s" % (nm[:16], lb, why))
        #  「없다」는 대개 내 필터 탓이다. 뭘 왜 뺐는지 남긴다
        for w, dn, dw in sorted(drop, key=lambda x: x[0])[:3]:
            print("        아깝게 뺀 것: %8s원/kg %-34s (%s)" % (format(w, ","), dn[:34], dw))
    for k, why in UNSURE.items():
        if info.get(k):
            print("   … %-16s %s" % (info[k]["name"][:16], why))

    json.dump(plan, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n→ %s" % OUT)

    if not a.apply:
        print("\n반영하려면 --apply")
        return 0
    n = 0
    for p in plan:
        c.execute("UPDATE ingredients SET wholesale_price=?, wholesale_basis=?, updated_at=? "
                  "WHERE ingredient_key=?", (p["new"], p["basis"], today, p["k"]))
        n += 1
    c.commit()
    print("\n✅ %d종 반영. 원가 재계산이 필요하다 → python scripts/compute_line_costs.py" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
