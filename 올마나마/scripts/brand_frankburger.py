# -*- coding: utf-8 -*-
"""프랭크버거(frankburger, brands.id=40) 메뉴판 수집 — JSON 파일 하나만 만든다.

  출력: data/brand_menu_list/frankburger.json
  DB 에 쓰지 않는다. brand_menu_store / sqlite 를 import 하지 않는다.

길:
  1) https://frankburger.co.kr/html/menu_1.html  (정적 HTML, urllib 로 읽힘 · 헤드리스 불필요)
     - 사이트맵에 「메뉴 > 메뉴소개」 한 장뿐이다. menu_2 · menu_3 은 **존재하지 않는다**
       (페이지에 적힌 링크로 확인. 번호를 조합해 찔러보지 않았다)
     - 모바일판 m.frankburger.co.kr/html/menu_1.html 도 받아 대조했다 — 카테고리 3개 · 메뉴 34개 ·
       순서까지 **완전히 동일**하고 가격도 마찬가지로 0건이었다
     - 카테고리 = <section> 의 제목 이미지 alt , 메뉴명 = <p class="menu_ko">
  2) 🔴 가격: **웹에는 없고 「자사 앱」에 있다.**  `https://apiv2.frankburger.co.kr/v1/app-menu`

     APK(`com.frankfnb.frankburger`, 폰에 깔린 것을 adb 로 뽑음)의 Hermes 번들
     `assets/index.android.bundle` 문자열에서 API 도메인이 나왔다. **인증 없이 GET 으로 열린다.**

       GET /v1/app-menu?meuCtgGrpCd=<그룹코드>&pageSize=200
       GET /v1/common/code?grpCd=MEU_CTG_GRP_CD      ← 그룹코드 목록(값을 추측하지 않고 여기서 받는다)

     ⚠️ **`pageSize`** 가 맞는 파라미터다. `size`·`limit`·`rowCnt`·`page` 는 **먹지 않고 10건만** 준다
        (그래서 처음엔 58건 중 10건만 보였다).

     🔴🔴 **가격 필드가 두 개다. 반드시 `meuPrc` 를 써라.**
        `meuPrc`     = 매장(홀) 판매가   ← **우리 기준**
        `dlvAppPrc`  = 배달앱 판매가     ← ⛔ 쓰지 마라
        58건 **전부** 두 값이 다르고 `dlvAppPrc` 가 언제나 더 비싸다(버거 +900 / 사이드·음료 +200 /
        세트 +1200). 배달 할증이 얹힌 값이라는 뜻이다.

     ⛔ 아래는 2026-07-28 에 **전부 확인한 것**이다. 웹 쪽은 같은 길을 다시 파지 마라.
        (버거킹이 `dineInprc` 를 자체 API 로 주고 있었기에 프랭크버거도 같은 방식으로 재점검했다.
         웹은 정말로 0건이었고, **앱이 답이었다.**)

     | 어디를 봤나 | 결과 |
     |---|---|
     | PC HTML `/html/menu_1.html` | 「원」·금액꼴 숫자 **0건** |
     | 모바일 HTML `m.frankburger.co.kr/html/menu_1.html` | PC 와 **완전 동일**, 역시 0건 |
     | 자체 JS 6개 (`common_gon.js` `sub_gon.js` `inquiry.js` `ajax.common/contents/simpleinq2.js`) | price·amt·prc·sellPrice·dineIn·takeOut **0건** (걸린 건 전부 CSS `border`) |
     | JS 안의 API 주소 | `franknmts.com/api/contents_datas.php` · `/api/represent_datas.php` 둘뿐. **개인정보처리방침 본문 CMS** 다(`policy_select`·`co_subject`). 메뉴와 무관 |
     | 주문·배달·픽업 경로 | **없다.** 페이지의 링크는 브랜드소개·가맹문의·매장찾기·게시판뿐. 「주문」은 홍보문구 한 줄(“주문과 동시에 직접 구워”), `CONST_ORDER` 는 GNB 인덱스. `ownershub.frankburger.co.kr` 는 점주 로그인 |
     | 브라우저 네트워크 탭 (실제 렌더) | **XHR/JSON 요청 0건.** 정적 파일 + Matomo 통계뿐. 즉 «화면에 안 그려질 뿐 응답엔 있다» 가 성립하지 않는다 |
     | 렌더된 DOM 전체 텍스트 | 「원」 0건, `\\d{1,2},\\d{3}` 꼴 숫자 0건 |
     | 광고 리타게팅 전역변수 (`_amt`·`AW_PRODUCT`·`across_adn_*`) | 전부 빈 값 / 0. 상품가가 실려 있지 않다 |

     메뉴 이미지는 전부 음식 사진(menu1_img*.jpg)이라 가격이 박혀 있지 않고,
     원산지/영양성분 이미지에도 가격은 없다.
     → **에뮬(place_menu_emu.py)까지 갈 필요가 없다.** 위 앱 API 로 34개 전부 채워진다.

  3) ⚠️ 앱에는 메뉴가 58개, 홈페이지 메뉴판에는 34개다.
     차이 24개는 **세트 24종·프랭크팩·엔드필드 콜라보** 로, 홈페이지 메뉴판에 아예 없다.
     메뉴판(`menus`)은 **홈페이지가 정본**이라 34개를 그대로 두고,
     앱에만 있는 것은 `app_only_menus` 에 따로 담는다. **단품과 세트를 섞지 않는다.**

⚠️ 아래 ORIGIN_* · NUTRI_G · ALLERGY 세 표는 **사람이 눈으로 읽은 값**이다.
   출처 이미지 한 장:  https://frankburger.co.kr/img/page/2022_menu/01/ingredient.jpg?2
   (메뉴 페이지 하단 「원산지 / 영양성분 / 알레르기 유발 성분 보기」 → /html/ingredient.html 안의 이미지.
    ⚠️ 그 페이지의 <title> 은 「프랭크버거 영양성분 표시」지만 **실제 내용은 원산지 표기 + 영양성분표 +
    알레르기 유발성분 세 가지**다. 제목만 보고 «영양성분표일 뿐» 이라고 판단하면 안 된다)
   알레르기 ● 표는 눈으로 세지 않고 이미지의 픽셀에서 검출했다(열 14개 · 행 41개, 애매한 칸 0개).
"""

import sys
import io
import os
import re
import json
import html
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://frankburger.co.kr"
SRC = BASE + "/html/menu_1.html"
ORIGIN_IMG = BASE + "/img/page/2022_menu/01/ingredient.jpg?2"
ORIGIN_PAGE = BASE + "/html/ingredient.html"
COLLECTED_AT = "2026-07-28"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "frankburger.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# ---------------------------------------------------------------- 사람이 읽은 값 (이미지 판독)
# 「원산지 표기」 표 — 품목 / 원산지 / 메뉴 세 칸. 표에 **메뉴 이름이 직접 적혀 있다.**
# 아래 키는 그 표의 메뉴 이름(원문 그대로, 띄어쓰기 없음)이고 값은 원산지 칸의 원문이다.
ORIGIN_BY_MENU = {
    "프랭크버거":       ["소고기 : 미국산 호주산 섞음"],
    "치즈버거":         ["소고기 : 미국산 호주산 섞음"],
    "베이컨치즈버거":   ["소고기 : 미국산 호주산 섞음",
                         "돼지고기(베이컨) : 외국산 (미국산,스페인산,브라질산)"],
    "더블비프치즈버거": ["소고기 : 미국산 호주산 섞음"],
    "비프앤쉬림프버거": ["소고기 : 미국산 호주산 섞음"],
    "JG버거":           ["소고기 : 미국산 호주산 섞음",
                         "돼지고기(베이컨) : 외국산 (미국산,스페인산,브라질산)"],
    "깐쇼새우비프버거": ["소고기 : 미국산 호주산 섞음"],
    "맥앤치즈비프버거": ["소고기 : 미국산 호주산 섞음",
                         "돼지고기(베이컨) : 외국산 (미국산,스페인산,브라질산)"],
    "100%한우갈릭버거": ["소고기 / 소고기(우지) : 국내산(한우)",
                         "돼지고기(베이컨) : 외국산 (미국산,스페인산,브라질산)"],
    "100%한우버거":     ["소고기 / 소고기(우지) : 국내산(한우)"],
    "K불고기버거":      ["돼지고기 : 국내산", "소고기(우지) : 국내산(한우)"],
    "K핫불고기버거":    ["돼지고기 : 국내산", "소고기(우지) : 국내산(한우)"],
    "통가슴살후라이드": ["닭고기 : 국내산"],
    "자이언트통닭다리": ["닭고기 : 태국산"],
    "파닭파닭치킨버거": ["닭고기 : 브라질산"],
    "치킨텐더":         ["닭고기 : 중국산"],
    "버팔로윙&봉":      ["닭고기 : 외국산 (리투아니아,태국,폴란드,브라질 등)"],
    "오징어링":         ["오징어 : 중국산"],
}
# 표의 「순살 치킨류」 한 줄이 순살치킨 3종을 한꺼번에 가리킨다
ORIGIN_SUNSAL = ["닭고기 : 브라질산"]

# 브랜드 공통 한 장이므로 최상위에도 원문 전체를 남긴다
ORIGIN_NOTE = (
    "원산지 표기 (프랭크버거 공통 · https://frankburger.co.kr/html/ingredient.html 이미지 판독)\n"
    "소고기 : 미국산 호주산 섞음 — 프랭크버거, 치즈버거, 베이컨치즈버거, 더블비프치즈버거, "
    "비프앤쉬림프버거, JG버거, 깐쇼새우비프버거, 맥앤치즈비프버거\n"
    "소고기 / 소고기(우지) : 국내산(한우) — 100%한우갈릭버거, 100%한우버거\n"
    "돼지고기 : 국내산 / 소고기(우지) : 국내산(한우) — K불고기버거, K핫불고기버거\n"
    "돼지고기(베이컨) : 외국산 (미국산,스페인산,브라질산) — 베이컨치즈버거, 100%한우갈릭버거, "
    "JG버거, 맥앤치즈비프버거\n"
    "닭고기 : 국내산 — 통가슴살후라이드\n"
    "닭고기 : 태국산 — 자이언트통닭다리\n"
    "닭고기 : 브라질산 — 파닭파닭치킨버거, 순살 치킨류\n"
    "닭고기 : 중국산 — 치킨텐더\n"
    "닭고기 : 외국산 (리투아니아,태국,폴란드,브라질 등) — 버팔로 윙&봉\n"
    "오징어 : 중국산 — 오징어링"
)

# 「영양성분표」 중량g 칸 — 제품명(원문) : 중량g
NUTRI_G = {
    "프랭크버거": 157, "치즈버거": 170, "베이컨치즈버거": 234, "쉬림프버거": 201,
    "비프앤쉬림프버거": 257, "JG버거": 222, "더블비프치즈버거": 249, "K불고기버거": 195,
    "K핫불고기버거": 189, "청양마요쉬림프버거": 220, "100%한우갈릭버거": 246,
    "100%한우버거": 192, "파닭파닭치킨버거": 218, "깐쇼새우비프버거": 272,
    "맥앤치즈비프버거": 324,
    "순살치킨_후라이드(기본)": 140, "순살치킨_청양마요": 169, "순살치킨_양념": 166,
    "바삭어니언링": 116, "해쉬포테이토(1개)": 51, "오징어링(3개)": 48, "프렌치프라이": 95,
    "치즈프렌치프라이": 145, "치즈스틱(3개)": 75, "더치즈볼(3개)": 90, "치킨텐더(2개)": 60,
    "통가슴살후라이드(1개)": 103, "버팔로윙봉(2+2)": 132, "자이언트통닭다리(1개)": 167,
    "콘샐러드": 100, "코울슬로": 100, "바닐라밀크쉐이크": 380,
    # 아래는 영양성분표에만 있고 메뉴판에는 없는 행 — 메뉴로 만들지 않는다
    # 콜라/제로콜라/사이다/탐스오렌지제로(매장용) 400 · 아메리카노 400 · 아이스아메리카노 400
    # 토마토케첩(소포장) 9 · 허니머스타드(소포장) 12 · 치킨용소스(소포장) 30
}

# 「알레르기 유발성분」 ● 행렬 — 이미지 픽셀에서 검출 (열 14개, 애매한 칸 0)
ALLERGY = {
    "프랭크버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기",
    "치즈버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기",
    "베이컨치즈버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기",
    "쉬림프버거": "알류, 우유, 대두, 밀, 새우, 토마토, 쇠고기",
    "비프앤쉬림프버거": "알류, 우유, 대두, 밀, 새우, 돼지고기, 토마토, 닭고기, 쇠고기",
    "JG버거": "알류, 우유, 대두, 밀, 돼지고기, 닭고기, 쇠고기",
    "더블비프치즈버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기",
    "K불고기버거": "알류, 우유, 대두, 밀, 돼지고기, 아황산류, 쇠고기",
    "K핫불고기버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 아황산류, 닭고기, 쇠고기, 조개류",
    "청양마요쉬림프버거": "알류, 우유, 대두, 밀, 새우, 토마토, 아황산류, 쇠고기",
    "100%한우갈릭버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기, 조개류",
    "100%한우버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 아황산류, 닭고기, 쇠고기, 조개류",
    "파닭파닭치킨버거": "알류, 우유, 땅콩, 대두, 밀, 토마토, 닭고기, 쇠고기, 조개류",
    "깐쇼새우비프버거": "알류, 우유, 대두, 밀, 새우, 돼지고기, 토마토, 아황산류, 닭고기, 쇠고기, 조개류",
    "맥앤치즈비프버거": "알류, 우유, 대두, 밀, 돼지고기, 토마토, 닭고기, 쇠고기",
    "순살치킨_후라이드(기본)": "알류, 우유, 대두, 밀, 닭고기, 쇠고기",
    "순살치킨_청양마요": "알류, 우유, 대두, 밀, 아황산류, 닭고기, 쇠고기",
    "순살치킨_양념": "알류, 우유, 대두, 밀, 토마토, 닭고기, 쇠고기",
    "바삭어니언링": "우유, 대두, 밀",
    "해쉬포테이토(1개)": "대두, 토마토",
    "오징어링(3개)": "알류, 밀, 오징어",
    "프렌치프라이": "대두",
    "치즈프렌치프라이": "우유, 대두",
    "치즈스틱(3개)": "우유, 대두, 밀",
    "더치즈볼(3개)": "우유, 대두, 밀",
    "치킨텐더(2개)": "대두, 밀, 닭고기",
    "통가슴살후라이드(1개)": "대두, 밀, 닭고기, 쇠고기",
    "버팔로윙봉(2+2)": "밀, 닭고기",
    "자이언트통닭다리(1개)": "대두, 밀, 닭고기",
    "콘샐러드": "알류, 대두",
    "코울슬로": "알류, 대두, 조개류",
    "바닐라밀크쉐이크": "우유, 대두",
}

# 메뉴판 이름 → 영양성분표/알레르기 표의 행 이름.
# 띄어쓰기만 다른 것은 자동으로 붙고, 아래는 표기가 다른 것만 손으로 적은 것.
NUTRI_ALIAS = {
    "해쉬 포테이토": "해쉬포테이토(1개)",
    "순살치킨 후라이드 (200g)": "순살치킨_후라이드(기본)",
    "순살치킨 양념 (200g)": "순살치킨_양념",
    "순살치킨 청양마요 (200g)": "순살치킨_청양마요",
    "자이언트 통닭다리": "자이언트통닭다리(1개)",
    "통가슴살 후라이드": "통가슴살후라이드(1개)",
    "버팔로윙봉 (4개)": "버팔로윙봉(2+2)",
    "코울슬로 샐러드": "코울슬로",
    # 아래 둘은 영양성분표에서 여러 행으로 갈린다(탄산음료 4행 · 아메리카노 2행) →
    # 1:1 로 못 붙이므로 **비워둔다.** 짐작해서 붙이지 않는다
    "탄산음료": None,
    "아메리카노": None,
}

# 원산지 표의 메뉴 이름 → 메뉴판 이름이 다른 것
ORIGIN_ALIAS = {
    "치킨텐더 (2개)": "치킨텐더",
    "버팔로윙봉 (4개)": "버팔로윙&봉",
    "오징어링 (3개)": "오징어링",
    "통가슴살 후라이드": "통가슴살후라이드",
    "자이언트 통닭다리": "자이언트통닭다리",
}

# 세트 구성/옵션이 메뉴판 본문에 적힌 것 (원문 그대로). 홍보문구는 넣지 않는다.
COMPOSE = {
    "탄산음료": "콜라 / 제로콜라 / 사이다 / 오렌지맛",
}


# ---------------------------------------------------------------- 앱 API (가격)
APP_API = "https://apiv2.frankburger.co.kr"
APP_MENU = APP_API + "/v1/app-menu"
APP_CODE = APP_API + "/v1/common/code?grpCd=MEU_CTG_GRP_CD"
APP_UA = {"User-Agent": "okhttp/4.12.0", "Accept": "application/json"}

# 홈페이지 메뉴판 이름 → 앱 메뉴 이름. 띄어쓰기만 다른 건 자동으로 붙으니
# **표기가 실제로 다른 것만** 적는다.
APP_ALIAS = {
    "해쉬 포테이토": "해쉬포테이토",
    "자이언트 통닭다리": "자이언트 통닭다리(1개)",
    "통가슴살 후라이드": "통가슴살 후라이드(1개)",
    "버팔로윙봉 (4개)": "버팔로윙봉",
    "아메리카노": "아메리카노(ICE)",
}
# 「탄산음료」 한 줄이 앱에서는 5종으로 갈린다. **다섯 개 값이 전부 같을 때만** 그 값을 쓴다.
FIZZ = ["콜라", "제로콜라", "사이다", "제로사이다", "탐스쥬씨오렌지"]


def norm(s):
    return re.sub(r"\s+", "", s)


def app_menus():
    """앱 API 에서 전 메뉴를 받는다. 그룹코드는 추측하지 않고 API 에서 받아 쓴다."""
    def get(url):
        req = urllib.request.Request(url, headers=APP_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    groups = [c["cd"] for c in get(APP_CODE)["data"]["codeList"]]
    out = {}
    short = []
    for g in groups:
        mp = get("%s?meuCtgGrpCd=%s&pageSize=200" % (APP_MENU, g))["data"]["menuPage"]
        rows = mp["content"]
        if rows and len(rows) != rows[0]["totalCount"]:
            short.append((g, len(rows), rows[0]["totalCount"]))
        for x in rows:
            out[x["meuIdn"]] = x
    if short:
        print("⚠️ 덜 받아온 그룹이 있다(페이징 확인 필요):", short)
    return out


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_dead(h):
    """HTML 주석을 먼저 걷어낸다 — 죽은 메뉴·숨은 탭이 섞인다."""
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S | re.I)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S | re.I)
    return h


def looks_like_menu(name, cats):
    """메뉴 아닌 것(홍보문구·탭 이름·UI 문자열) 거르기."""
    if not name:
        return False, "빈 문자열"
    if name[-1] in ".!?~":
        return False, "문장부호로 끝난다"
    if len(name) >= 18:
        return False, "18자 이상"
    if norm(name) in {norm(c) for c in cats}:
        return False, "카테고리 이름과 같다"
    return True, None


def parse(hpage):
    seg = re.search(r'<div[^>]*id=["\']content["\'].*?<div class="footer_wrap"',
                    hpage, re.S)
    seg = seg.group(0) if seg else hpage

    toks = re.findall(
        r'menu_title[\w_]*\.png"\s+alt="([^"]*)"'
        r'|class="menu_ko">(.*?)</p>'
        r"|background-image:url\('([^']+)'\)",
        seg, re.S)

    cats, rows = [], []
    cur, img = None, None
    for a, b, c in toks:
        if a:
            cur = html.unescape(a).strip()
            if cur not in cats:
                cats.append(cur)
            img = None
        elif c:
            img = c
        elif b:
            nm = html.unescape(re.sub(r"<[^>]+>", " ", b))
            nm = re.sub(r"\s+", " ", nm).strip()
            rows.append((cur, nm, img))
            img = None
    return cats, rows


def img_url(p):
    if not p:
        return None
    return BASE + "/" + p.lstrip("./").lstrip("/") if not p.startswith("http") else p


def main():
    page = strip_dead(fetch(SRC))
    cats, rows = parse(page)
    if not cats or not rows:
        print("[중단] 카테고리/메뉴를 하나도 못 얻었다 — 파일을 쓰지 않는다")
        return 1

    nutri_n = {norm(k): v for k, v in NUTRI_G.items()}
    aller_n = {norm(k): v for k, v in ALLERGY.items()}
    origin_n = {norm(k): v for k, v in ORIGIN_BY_MENU.items()}

    # ---- 앱 API 에서 가격 (홀 매장가 meuPrc)
    app = app_menus()
    by_name = {}
    for x in app.values():
        by_name.setdefault(norm(x["meuNm"]), x)
    print("앱 API 메뉴 %d개" % len(app))

    dropped = []
    menus = []
    matched_idn = set()
    seen_pos = {c: 0 for c in cats}
    for cat, nm, img in rows:
        ok, why = looks_like_menu(nm, cats)
        if not ok:
            dropped.append((cat, nm, why))
            continue

        # ---- 중량 · 알레르기
        key = NUTRI_ALIAS.get(nm, nm)
        wr = al = None
        if key is not None:
            k = norm(key)
            if k in nutri_n:
                wr = "%dg" % nutri_n[k]
            if k in aller_n:
                al = aller_n[k]

        # ---- 원산지
        okey = ORIGIN_ALIAS.get(nm, nm)
        org = origin_n.get(norm(okey))
        if org is None and nm.startswith("순살치킨"):
            org = ORIGIN_SUNSAL
        org_raw = " / ".join(org) if org else None

        note = None
        if org_raw or wr or al:
            note = "메뉴 이미지 판독 " + ORIGIN_IMG

        # ---- 가격 (앱 API · meuPrc = 홀 매장가. dlvAppPrc(배달가)는 쓰지 않는다)
        price = psrc = pnote = None
        if nm == "탄산음료":
            got = [by_name[norm(f)] for f in FIZZ if norm(f) in by_name]
            vals = {g["meuPrc"] for g in got}
            if len(got) == len(FIZZ) and len(vals) == 1:
                price = vals.pop()
                pnote = ("앱 API meuPrc(홀 매장가) · 앱에서는 %s %d종으로 갈리는데 "
                         "값이 모두 같아 그 값을 쓴다" % (" / ".join(FIZZ), len(FIZZ)))
        else:
            a = by_name.get(norm(APP_ALIAS.get(nm, nm)))
            if a:
                price = a["meuPrc"]
                matched_idn.add(a["meuIdn"])
                pnote = ("앱 API meuPrc(홀 매장가) · meuCd=%s · 같은 메뉴 배달가 dlvAppPrc=%s "
                         "(배달 할증이라 쓰지 않음)" % (a["meuCd"], a["dlvAppPrc"]))
        if price is not None:
            psrc = "app_api"
            pnote = APP_MENU + " — " + pnote

        pos = seen_pos[cat]
        seen_pos[cat] += 1
        menus.append({
            "name": nm,
            "price": price,
            "price_source": psrc,
            "price_note": pnote,
            "compose_raw": COMPOSE.get(nm),
            "weight_raw": wr,
            "origin_raw": org_raw,
            "allergy_raw": al,
            "detail_url": None,
            "image_url": img_url(img),
            "ext_id": None,
            "cats": [[cat, pos]],
            "_src_note": note,
        })

    # 판독 출처는 모든 메뉴에 같은 키로 둔다(없으면 null) — 키가 들쭉날쭉하면 읽는 쪽이 깨진다.
    for m in menus:
        m["source_note"] = m.pop("_src_note")

    # 앱에만 있고 홈페이지 메뉴판에 없는 것 — 세트·팩·콜라보.
    # 🔴 메뉴판(menus)에 섞지 않는다. 단품/세트를 뒤섞지 말라는 규칙이다.
    app_only = []
    fizz_idn = {by_name[norm(f)]["meuIdn"] for f in FIZZ if norm(f) in by_name}
    for x in sorted(app.values(), key=lambda y: (y["meuCtgGrpCdNm"], y["dispRnk"], y["meuNm"])):
        if x["meuIdn"] in matched_idn or x["meuIdn"] in fizz_idn:
            continue
        app_only.append({
            "name": x["meuNm"],
            "price": x["meuPrc"],
            "price_source": "app_api",
            "delivery_price": x["dlvAppPrc"],
            "is_set": x["setYn"] == "Y",
            "app_category": x["meuCtgGrpCdNm"],
            "ext_id": x["meuCd"],
        })

    doc = {
        "brand": "프랭크버거",
        "slug": "frankburger",
        "source": SRC + "  (골격·원산지) + " + APP_MENU + "  (가격)",
        "price_source_note": (
            "가격은 자사 앱 API `" + APP_MENU + "` 의 **meuPrc(매장 홀 판매가)** 다. "
            "같은 응답의 dlvAppPrc 는 배달앱가(항상 더 비쌈)라 쓰지 않았다. "
            "홈페이지 HTML·JS·렌더DOM 에는 가격이 0건이다."),
        "collected_at": COLLECTED_AT,
        "origin_note": ORIGIN_NOTE,
        "origin_source": ORIGIN_PAGE + " (이미지 " + ORIGIN_IMG + ") — 사람이 눈으로 읽음",
        "cats": [{"name": c, "parent": None, "ext_id": None} for c in cats],
        "menus": menus,
        "app_only_menus": app_only,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("저장: %s" % OUT)
    print("카테고리 %d개 / 메뉴 %d개 / 가격 있는 것 %d개"
          % (len(cats), len(menus), sum(1 for m in menus if m["price"] is not None)))
    miss = [m["name"] for m in menus if m["price"] is None]
    if miss:
        print("⚠️ 가격 못 붙인 메뉴 %d개: %s" % (len(miss), ", ".join(miss)))
    print("앱에만 있는 메뉴 %d개(세트 %d) — app_only_menus 로 따로 담음"
          % (len(app_only), sum(1 for x in app_only if x["is_set"])))
    print("버린 줄 %d개" % len(dropped))
    for c, n, w in dropped:
        print("   - [%s] %s  ← %s" % (c, n, w))
    return 0


if __name__ == "__main__":
    sys.exit(main())
