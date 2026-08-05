"""
방구석 약국 관리 프로그램 (GUI 버전)

사용 방법:
1. credentials.json 파일을 이 스크립트와 같은 폴더에 둔다.
2. BLOG_URL을 본인 블로그 주소로 수정한다 (아래 설정 부분).
3. posts 폴더를 만들고, 발행할 글 텍스트 파일을 넣는다.
4. 이 파일을 더블클릭하거나 "python manager.py"로 실행한다.
5. 뜨는 창에서 버튼을 눌러서 작업한다. (터미널 명령어 안 쳐도 됨)
"""

import os
import re
import json
import glob
import shutil
import base64
import pickle
import threading
import time
import requests
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog, ttk

from naver_export import export_post_for_naver, convert_content_for_naver, copy_html_to_clipboard
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ===== 설정 (본인 정보로 수정) =====
BLOG_URL = "https://bangpharmacy.blogspot.com/"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
POSTS_FOLDER = "posts"
POSTED_FOLDER = "posted"
SCOPES = ["https://www.googleapis.com/auth/blogger"]

# 짧은 시간에 여러 글을 연속 발행하면 Blogger가 스팸/어뷰징으로 판단해
# 신규 글 발행(insert) 자체를 막아버리는 경우가 있어, 글 사이에 대기시간을 둔다.
PUBLISH_DELAY_SECONDS = 8

GITHUB_CONFIG_FILE = "github_config.json"
CARD_INSERTS_FOLDER = "card_inserts"
CARD_INSERTED_FOLDER = "card_inserted"

# 임시글(임시N) 덮어쓰기 + 예약발행용 폴더. insert()가 스팸 차단에 걸려 있어서
# "대시보드에서 임시N 수동 등록 -> API로 덮어쓰기 -> 예약발행" 워크플로우를 쓴다.
TEMP_PUBLISH_FOLDER = "temp_publish"
TEMP_PUBLISHED_FOLDER = "temp_published"

# 네이버 브릿지 글 입력 폴더. 재미나이(웹)에서 편성표 기반으로 "완성해서 통으로 받은 글"을
# 파일로 넣으면 문단 간격 정리 + [방구석 약국] 링크 확인 후 그대로 발행한다.
# (네이버는 Blogspot과 링크 연결만, 콘텐츠는 재미나이에서 독립 작성 — 2026-07-09 확정)
# 파일 형식 (bridge_input/상품명.txt):
#   TITLE: 글 제목
#   BLOGSPOT_URL: 연결할 방구석 약국 글 URL
#   TAGS: 태그1, 태그2
#   ---
#   (재미나이에서 받은 완성 글 전체 — 빈 줄로 문단 구분)
BRIDGE_INPUT_FOLDER = "bridge_input"
BRIDGE_DONE_FOLDER = "bridge_done"

# 각 글 대표이미지 삽입용 폴더. 파일명(확장자 제외)이 글 제목에 포함된 키워드와
# 일치하는 글을 찾아서 본문 맨 위에 이미지를 넣는다.
THUMBNAILS_FOLDER = "thumbnails"
THUMBNAILS_DONE_FOLDER = "thumbnails_done"
THUMBNAIL_MARKER = "<!-- THUMBNAIL_IMAGE_V1 -->"

# 게시물 본문에 삽입하는 모바일 최적화 CSS 식별용 마커 (중복 삽입 방지)
MOBILE_CSS_MARKER = "<!-- MOBILE_FONT_CSS_V1 -->"
# 블로그 제목(타이틀) 글자 크기 확대용 선택자 후보 (Dynamic Views 테마는 클래스명이
# 정확히 확인되지 않아, 흔히 쓰이는 후보들을 한 번에 지정해 실제로 맞는 것만 적용되게 함)
# .widget.Blog(본문 글 영역)로 범위를 한정해서, 사이드바의 인기게시물 위젯 제목까지
# 커지는 부작용을 막는다.
TITLE_SELECTORS = (
    ".widget.Blog .post-title,.widget.Blog .post-title a,"
    ".widget.Blog .entry-title,.widget.Blog .entry-title a"
)

# 테마(Soho 계열) 기본 본문 폰트가 Lora(영문 세리프)라서 한글이 명조/바탕체로
# 렌더링되는 문제가 있어, 본문 전체를 고딕 계열로 강제한다.
BODY_FONT_STACK = (
    "'Noto Sans KR','Malgun Gothic','맑은 고딕','Apple SD Gothic Neo',sans-serif"
)

MOBILE_CSS_BLOCK = (
    MOBILE_CSS_MARKER +
    "<style>"
    # 포스팅 제목을 홈 화면과 통일: 초록 배경 배너 제거 + 글자색을 테마 초록으로
    f"{TITLE_SELECTORS}{{font-size:32px !important;line-height:1.4 !important;color:#25a186 !important;}}"
    ".widget.Blog .post-title-container{background:transparent !important;}"
    f".post-body,.post-body *{{font-family:{BODY_FONT_STACK} !important;}}"
    ".post-body,.post-body p,.post-body li{font-size:17px !important;line-height:1.8 !important;}"
    # (주의) 사이드바/인기게시물 스타일은 여기 넣지 말 것!
    # 이 CSS는 포스팅 페이지에만 적용되어 홈 화면과 어긋나게 된다.
    # 사이드바 관련 스타일은 전부 "목차 가젯"(사이드바_목차_가젯_코드.md) 한 곳에서만 관리한다.
    ".widget.Blog .byline.post-timestamp{display:none !important;}"
    # 쿠팡 상품카드 구매유도 강화: 카드 그림자 + 버튼 강조/호버 효과
    '.post-body div[style*="border:1px solid #eee"]{border-radius:12px !important;box-shadow:0 2px 10px rgba(0,0,0,0.07) !important;}'
    '.post-body a[style*="background-color:#e60000"]{font-size:17px !important;border-radius:8px !important;'
    "transition:background-color .15s,transform .15s,box-shadow .15s;}"
    '.post-body a[style*="background-color:#e60000"]:hover{background-color:#c50000 !important;'
    "transform:translateY(-1px);box-shadow:0 4px 12px rgba(230,0,0,0.3);}"
    # 블로그 배경 일러스트 + 본문 영역 반투명 흰 배경 (가독성 확보)
    "body{background-image:url('https://raw.githubusercontent.com/bangpharmacy-images/bangpharmacy-images/main/images/bg_illustration.jpeg') !important;"
    "background-size:cover !important;background-attachment:fixed !important;background-position:center top !important;}"
    ".page_body{background:rgba(255,255,255,0.93) !important;border-radius:12px !important;box-shadow:0 2px 16px rgba(0,0,0,0.08) !important;}"
    "@media screen and (max-width: 640px){"
    ".post-body,.post-body p,.post-body li{font-size:19px !important;line-height:1.8 !important;}"
    ".post-body a{font-size:18px !important;}"
    ".post-body h2{font-size:24px !important;}"
    ".post-body h3{font-size:20px !important;}"
    f"{TITLE_SELECTORS}{{font-size:22px !important;}}"
    "}"
    "</style>"
)

COUPANG_DISCLOSURE_SMALL = (
    '<div style="text-align: center;">'
    '<span style="font-size: x-small;">'
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받을 수 있습니다."
    "</span></div>"
)

# 글 맨 끝에 한 번만 삽입하는 "소용량 테스트구매 유도" 문구 (중복 삽입 방지 마커 포함)
TEST_PURCHASE_NOTE_MARKER = "<!-- TEST_PURCHASE_NOTE_V1 -->"
TEST_PURCHASE_NOTE_HTML = (
    TEST_PURCHASE_NOTE_MARKER +
    '<p style="margin-top:20px; padding:14px; background-color:#f7f7f7; border-radius:8px; '
    'color:#555; line-height:1.7;">'
    "<strong>참고로,</strong> TV 홈쇼핑에서는 보통 60포~120포 이상을 한 세트로 묶어 판매해 "
    "개당 단가는 낮아 보이지만, 실제로는 한 번에 목돈이 나가고 다 먹기 전에 유통기한이 지나버리는 "
    "경우도 적지 않습니다. 반면 이 글에 소개된 상품들은 대부분 1~2개월분 소용량 구성이라, "
    "아이 입맛에 맞는지·먹은 뒤 반응이 어떤지 먼저 확인해보는 '테스트 구매'에 부담이 적습니다. "
    "잘 맞는 걸 확인한 뒤에 대용량으로 넘어가도 늦지 않습니다."
    "</p>"
)

# ============================================================
# 표준 콘텐츠 서식 (2026.7 확정) — 앞으로 모든 영양제 글에 공통 적용
# 1) 대용량 구매 주의사항: 상품카드 삽입 위치 "바로 앞"에 삽입
# 2) 자연 섭취 방법 + 아이허브/쿠팡 이용 안내: 관련 글 섹션 "바로 앞"에 삽입
# 두 블록 모두 마커 포함 → 재실행해도 중복 삽입되지 않고 교체됨
# ============================================================

BULK_PURCHASE_WARNING_MARKER = "<!-- BULK_PURCHASE_WARNING_V1 -->"
BULK_PURCHASE_WARNING_HTML = (
    BULK_PURCHASE_WARNING_MARKER +
    '<div style="margin: 30px 0; padding: 16px; background-color: #fff8e1; border-left: 4px solid #f5a623; border-radius: 6px;">'
    '<p style="margin: 0 0 10px 0; font-weight: bold; color: #7a5c00;">⚠️ 대용량 구매 전 꼭 확인하세요</p>'
    '<p style="margin-bottom: 10px; line-height: 1.7;">홈쇼핑 등에서 흔히 보이는 6개월~1년 치 대용량 구성은 개당 단가가 낮아 보이지만, '
    '실제로는 유통기한 안에 다 먹지 못하거나 개봉 후 보관 중 변질될 위험이 있습니다.</p>'
    '<p style="margin-bottom: 10px; line-height: 1.7;">✅ <strong>유산균(생균 함유)</strong> — 온도·습도 변화에 민감해서, 포장에 상온 보관이라 '
    '적혀 있어도 개봉 후에는 냉장 보관하는 것이 균 생존력 유지에 유리합니다. 유통기한이 남았더라도 색이 변했거나 이상한 냄새가 나면 폐기하는 것이 안전합니다.</p>'
    '<p style="margin-bottom: 10px; line-height: 1.7;">✅ <strong>오메가3(불포화지방산)</strong> — 열·빛·산소에 취약해 산패가 진행되기 쉽습니다. '
    '비린내가 평소보다 심해졌거나, 캡슐이 물렁해지거나 여러 개가 서로 들러붙어 있거나, 색이 탁해졌다면 산패 신호이니 즉시 폐기하세요.</p>'
    '<p style="margin-bottom: 0; line-height: 1.7;">그래서 처음 시도하는 제품이라면 1~2개월분 소용량으로 먼저 테스트해보고, '
    '몸에 잘 맞고 꾸준히 먹을 수 있다는 확신이 선 뒤에 대용량으로 넘어가는 것을 권장합니다.</p>'
    '</div>'
)

# 보관/섭취 타이밍/인증마크 확인법 (여유 있을 때 함께 넣는 보너스 블록, 위 경고와 별도 마커)
STORAGE_TIPS_MARKER = "<!-- STORAGE_TIPS_V1 -->"
STORAGE_TIPS_HTML = (
    STORAGE_TIPS_MARKER +
    '<div style="margin: 20px 0; padding: 16px; background-color: #f7f7f7; border-radius: 6px;">'
    '<p style="margin: 0 0 10px 0; font-weight: bold;">📦 보관·섭취 팁</p>'
    '<p style="margin-bottom: 8px; line-height: 1.7;">✅ <strong>보관 방법</strong> — 직사광선을 피해 서늘하고 건조한 곳에 보관하고, '
    '여름철 고온다습한 환경이라면 냉장 보관을 고려하세요 (정확한 보관법은 제품 표기가 우선입니다).</p>'
    '<p style="margin-bottom: 8px; line-height: 1.7;">✅ <strong>섭취 타이밍</strong> — 오메가3·루테인처럼 지용성 성분은 식사 중이나 식후에 '
    '먹어야 지방과 함께 흡수되어 흡수율이 높아집니다. 유산균은 제품마다 권장 시점이 다르니 표기를 확인하세요.</p>'
    '<p style="margin-bottom: 0; line-height: 1.7;">✅ <strong>인증마크 확인</strong> — 포장에 "건강기능식품" 문구·도안(식약처 인증)이 있는지, '
    'GMP(우수건강기능식품제조기준) 인증 표시가 있는지 확인하면 최소한의 안전장치를 확인할 수 있습니다.</p>'
    '</div>'
)

# 성분별 "자연 섭취 방법" — 영양제를 대체하는 게 아니라 함께 챙기면 좋다는 보완적 톤
NATURAL_FOOD_SOURCES = {
    "유산균": (
        "김치·된장·청국장·요구르트·치즈 같은 발효식품에 유산균이 자연적으로 들어있습니다. "
        "여기에 양파·마늘·바나나·귀리처럼 유산균의 먹이가 되는 식이섬유(프리바이오틱스)를 함께 챙기면 "
        "장에 이미 자리잡은 유익균이 더 잘 자랄 수 있는 환경이 만들어집니다."
    ),
    "오메가3": (
        "고등어·삼치·꽁치·연어 같은 등푸른 생선을 주 2회 이상 챙기면 오메가3(EPA·DHA)를 자연스럽게 보충할 수 있습니다. "
        "생선을 자주 못 드신다면 들기름·아마씨유·호두 같은 식물성 오메가3(ALA) 공급원도 도움이 됩니다."
    ),
    "루테인": (
        "시금치·케일·브로콜리·옥수수, 그리고 달걀노른자에 루테인이 풍부합니다. "
        "루테인은 지용성이라 나물을 무칠 때 참기름을 살짝 더하거나 기름에 볶아 먹으면 흡수율을 높일 수 있습니다."
    ),
}
NATURAL_FOOD_MARKER = "<!-- NATURAL_FOOD_V1 -->"


def build_natural_food_html(ingredient):
    """ingredient(유산균/오메가3/루테인)에 맞는 '자연 섭취 방법' 섹션 HTML을 만든다."""
    body = NATURAL_FOOD_SOURCES.get(ingredient)
    if not body:
        return ""
    return (
        NATURAL_FOOD_MARKER +
        '<h3 style="margin-top: 30px; margin-bottom: 15px; font-size: 18px; color: #222;">평소 식사로도 함께 챙기면 좋아요</h3>'
        f'<p style="margin-bottom: 20px; line-height: 1.7;">영양제는 부족하기 쉬운 부분을 보충하는 수단이지, 식사를 대신할 수는 없습니다. {body} '
        "영양제와 자연식품 섭취를 함께 병행하는 것이 가장 안정적인 방법입니다.</p>"
    )


# 아이허브 vs 쿠팡파트너스 구매 안내 — 한쪽을 깎아내리지 않는 병렬 비교 톤
IHERB_COUPANG_GUIDE_MARKER = "<!-- IHERB_COUPANG_GUIDE_V1 -->"
IHERB_COUPANG_GUIDE_HTML = (
    IHERB_COUPANG_GUIDE_MARKER +
    '<h3 style="margin-top: 30px; margin-bottom: 15px; font-size: 18px; color: #222;">구매처별 이용 안내 — 아이허브 vs 쿠팡</h3>'
    '<p style="margin-bottom: 10px;"><strong>🌍 아이허브(iHerb) 이용 안내</strong><br>'
    "1996년 설립된 미국 기반 세계 최대 건강기능식품 전문 온라인 리테일러로, 한국소비자원 조사에서 해외직구 플랫폼 중 "
    "소비자 상담(불만) 건수가 가장 적어 신뢰도가 높게 평가된 곳입니다. 국내에 없는 브랜드나 고함량 제품을 폭넓게 접할 수 있고, "
    "한국 창고 경유 물량이 많아 평균 배송은 4~7일 정도이며 4만원 이상 구매 시 무료배송입니다(미만은 배송비 약 5천원). "
    "처음 이용하신다면: ①간단한 이메일 회원가입 → ②원화 결제 가능 → ③관세청 사이트(p.customs.go.kr)에서 개인통관고유부호 발급 후 "
    "결제 시 입력 → ④자가사용 목적으로 150달러 이하면 관세·부가세가 면제됩니다(단, 건강기능식품은 총 6병까지만 자가사용으로 인정되며, "
    "한 주문당 150달러 이상은 결제 자체가 제한됩니다).</p>"
    '<p style="margin-bottom: 20px;"><strong>🚀 쿠팡파트너스 이용 안내</strong><br>'
    "로켓배송 상품은 당일~익일 도착이 가능해 지금 바로 필요한 경우에 유리하고, 국내 정식 유통 채널이라 반품·교환도 "
    "국내 소비자 기준으로 간편하게 처리됩니다(로켓배송 상품은 대부분 무료 반품 회수 지원). 해외 결제나 통관 절차 없이 "
    "익숙한 방식으로 바로 구매할 수 있다는 점이 강점입니다.</p>"
    '<p style="margin-bottom: 20px; line-height: 1.7;">정리하면, <strong>당장 빠르게 받아보고 반품·교환도 간편하게 하고 싶다면 쿠팡</strong>이, '
    "<strong>국내에 없는 브랜드나 고함량 제품을 직접 골라보고 싶고 약간의 배송 대기와 통관 절차를 감수할 수 있다면 아이허브</strong>가 "
    "더 유리합니다. 둘 다 장단점이 있으니 상황에 맞게 선택하시면 됩니다.</p>"
)

_FIRST_CARD_ANCHOR_RE = re.compile(
    r'<!-- (?:PRODCARD:[^>]*|CARD_PLACEHOLDER:[^>]*) -->'
    r'|\(쿠팡 파트너스 상품 링크/위젯 삽입 영역[^)]*\)'
    r'|<p[^>]*>\s*<a href="https://link\.coupang\.com'  # 카드 시스템 이전에 만든 구형 상품 링크(고소틴/가누다/프로메가 등) 대비
)
_RELATED_HR_RE = re.compile(
    r'<hr[^>]*>\s*(?=<p[^>]*><strong>관련 글:?</strong>)'
)


def detect_ingredient(labels):
    """글의 라벨에서 자연 섭취 방법 성분(유산균/오메가3/루테인)을 판별한다."""
    for tag in ("유산균", "오메가3", "루테인"):
        if tag in labels:
            return tag
    return None


def add_purchase_guide_sections(content, labels, include_storage_tips=True):
    """표준 서식 3종을 글 본문에 삽입한다 (신규/기존 글 공용, 재실행해도 안전).

    1) 대용량 구매 주의사항 -> 첫 상품카드/플레이스홀더 바로 앞
    2) 자연 섭취 방법 + 아이허브·쿠팡 구매 안내 (+선택: 보관/타이밍/인증마크 팁)
       -> "관련 글" 구분선 바로 앞 (없으면 테스트구매 문구/고지문구 앞, 그것도 없으면 맨 끝)
    """
    new_content = content

    if BULK_PURCHASE_WARNING_MARKER not in new_content:
        m = _FIRST_CARD_ANCHOR_RE.search(new_content)
        if m:
            idx = m.start()
            # 카드 여러 개를 감싸는 외부 wrapper div(예: cfu.html)가 바로 앞에 있으면
            # 그 wrapper div 시작 지점 앞으로 삽입 위치를 옮긴다 (wrapper 내부에 끼는 것 방지).
            preceding = new_content[max(0, idx - 400):idx]
            wrap_m = re.search(r'<div style="display:flex;[^"]*">\s*$', preceding)
            if wrap_m:
                idx = idx - (len(preceding) - wrap_m.start())
            new_content = new_content[:idx] + BULK_PURCHASE_WARNING_HTML + new_content[idx:]

    if IHERB_COUPANG_GUIDE_MARKER not in new_content:
        ingredient = detect_ingredient(labels)
        block = ""
        if ingredient and NATURAL_FOOD_MARKER not in new_content:
            block += build_natural_food_html(ingredient)
        block += IHERB_COUPANG_GUIDE_HTML
        if include_storage_tips and STORAGE_TIPS_MARKER not in new_content:
            block += STORAGE_TIPS_HTML

        m = _RELATED_HR_RE.search(new_content)
        if m:
            idx = m.start()
            new_content = new_content[:idx] + block + new_content[idx:]
        elif TEST_PURCHASE_NOTE_MARKER in new_content:
            idx = new_content.find(TEST_PURCHASE_NOTE_MARKER)
            new_content = new_content[:idx] + block + new_content[idx:]
        elif COUPANG_DISCLOSURE_SMALL in new_content:
            idx = new_content.find(COUPANG_DISCLOSURE_SMALL)
            new_content = new_content[:idx] + block + new_content[idx:]
        else:
            new_content = new_content.rstrip() + block

    return new_content


# ---------------------------------------------------------------------------
# 애드센스 심사 기간 임시 조치: 쿠팡 파트너스 상품카드/링크/고지문구를
# 화면에서 안 보이게 HTML 주석으로 감췄다가, 승인 후 되돌리기 위한 함수 쌍.
# (HTML 주석은 중첩이 안 되므로, 기존 PRODCARD 마커 주석은 대괄호로 치환한 뒤
#  전체를 하나의 진짜 주석으로 감싼다. 재실행해도 안전하게 설계됨.)
# ---------------------------------------------------------------------------
COUPANG_HIDDEN_OPEN = "<!--COUPANG_HIDDEN_FOR_ADSENSE:"
COUPANG_HIDDEN_CLOSE = "-->"

_PRODCARD_BLOCK_RE = re.compile(r'<!-- PRODCARD:(.*?) -->(.*?)<!-- /PRODCARD -->', re.DOTALL)
_RAW_COUPANG_ANCHOR_RE = re.compile(r'<a\s+href="https://link\.coupang\.com[^"]*"[^>]*>.*?</a>', re.DOTALL)
# 고지문구는 글마다 감싸는 태그(div/p/small/em)와 문구 자체 표현도 조금씩 다르다
# ("쿠팡 파트너스"/"쿠팡파트너스", "제공받을 수 있습니다"/"제공받습니다", 앞뒤 ※·따옴표 유무 등).
# 감싸는 태그는 건드리지 않고 문장 텍스트 자체만 정확히 찾아서 그 부분만 주석으로 감싼다
# (어떤 태그로 감싸여 있든 안전하게 동작).
_DISCLOSURE_VARIANT_RE = re.compile(
    r'※?\s*"?이 포스팅은 쿠팡\s?파트너스 활동의 일환으로,?\s*'
    r'이에 따른 일정액의 수수료를 제공받(?:을 수 있습니다|습니다)\.?"?'
)


def _wrap_prodcard_block(m):
    link, inner = m.group(1), m.group(2)
    return f'{COUPANG_HIDDEN_OPEN}[[PRODCARD:{link}]]{inner}[[/PRODCARD]]{COUPANG_HIDDEN_CLOSE}'


def hide_coupang_content(content):
    """쿠팡 파트너스 상품카드/링크/고지문구를 화면에 보이지 않게 HTML 주석으로 감싼다.

    HTML 주석은 중첩될 수 없으므로, PRODCARD 카드 블록 내부에 있는 링크는
    raw-link 처리 대상에서 반드시 제외해야 한다 (안 그러면 카드를 감싸는 바깥쪽
    주석이 카드 내부에서 개별로 감싼 링크의 '-->'에 의해 조기 종료되어 페이지가 깨짐).

    이미 (일부라도) 숨겨진 글에 다시 실행해도 항상 안전하도록, 먼저 완전히 복원한
    "진짜 원본" 기준으로 처리한다 (문구 패턴이 나중에 추가/수정돼도 재실행으로 따라잡을 수 있음).
    """
    content = restore_coupang_content(content)

    # 1) PRODCARD 블록 범위를 원본 기준으로 먼저 기록해둔다 (raw link가 그 안에 있는지 판정용).
    prodcard_spans = [
        (m.start(), m.end())
        for m in re.finditer(r'<!-- PRODCARD:.*?<!-- /PRODCARD -->', content, re.DOTALL)
    ]

    # 2) PRODCARD 범위 밖에 있는 raw 레거시 링크만 개별로 감싼다 (뒤에서부터 치환해 인덱스 안 밀리게).
    raw_matches = [
        m for m in _RAW_COUPANG_ANCHOR_RE.finditer(content)
        if not any(s <= m.start() <= e for s, e in prodcard_spans)
    ]
    new_content = content
    for m in reversed(raw_matches):
        new_content = (
            new_content[:m.start()]
            + COUPANG_HIDDEN_OPEN + m.group(0) + COUPANG_HIDDEN_CLOSE
            + new_content[m.end():]
        )

    # 3) 고지문구 (표준 문구 + 스타일/표현이 조금 다른 예전 버전 모두 이 정규식 하나로 처리.
    #    COUPANG_DISCLOSURE_SMALL도 결국 이 문장을 포함하므로 별도 처리 시 이중으로 감싸져
    #    주석이 깨지는 문제가 있어, 반드시 이 정규식 하나만 사용한다.)
    new_content = _DISCLOSURE_VARIANT_RE.sub(
        lambda m: COUPANG_HIDDEN_OPEN + m.group(0) + COUPANG_HIDDEN_CLOSE,
        new_content
    )

    # 4) PRODCARD 카드 블록 전체를 감싼다 (내부 마커 주석은 대괄호로 치환해 중첩 방지).
    new_content = _PRODCARD_BLOCK_RE.sub(_wrap_prodcard_block, new_content)

    return new_content


_HIDDEN_PRODCARD_RE = re.compile(
    re.escape(COUPANG_HIDDEN_OPEN) + r'\[\[PRODCARD:(.*?)\]\](.*?)\[\[/PRODCARD\]\]' + re.escape(COUPANG_HIDDEN_CLOSE),
    re.DOTALL
)
_HIDDEN_GENERIC_RE = re.compile(
    re.escape(COUPANG_HIDDEN_OPEN) + r'(.*?)' + re.escape(COUPANG_HIDDEN_CLOSE),
    re.DOTALL
)


def restore_coupang_content(content):
    """hide_coupang_content()로 감춘 쿠팡 카드/링크/고지문구를 원상복구한다 (애드센스 승인 후 사용)."""
    new_content = content

    def _restore_card(m):
        link, inner = m.group(1), m.group(2)
        return f'<!-- PRODCARD:{link} -->{inner}<!-- /PRODCARD -->'
    new_content = _HIDDEN_PRODCARD_RE.sub(_restore_card, new_content)

    new_content = _HIDDEN_GENERIC_RE.sub(lambda m: m.group(1), new_content)

    return new_content


_RELATED_LINK_PLACEHOLDER_RE = re.compile(r'([^<>\n]+?)\s*\((?:링크\s*삽입|링크,?\s*준비중|링크)\)')


def auto_link_related_posts(content, all_posts):
    """"제목 (링크 삽입)" 형태의 관련 글 표시를 실제 발행된 글 URL로 자동 연결한다.

    all_posts: fetch_all_posts() 결과 (title, url 필드 사용) — 하드코딩된 매핑표 없이
    현재 블로그에 실제로 존재하는 제목과 대조해서 매칭한다.
    """
    title_url = {p["title"]: p["url"] for p in all_posts}

    def repl(m):
        phrase = m.group(1).strip()
        url = title_url.get(phrase)
        if not url:
            return m.group(0)  # 매칭 안 되면 원본 그대로 둠 (수동 확인 필요)
        return f'<a href="{url}">{phrase}</a>'

    return _RELATED_LINK_PLACEHOLDER_RE.sub(repl, content)


def finalize_blogspot_content(raw_body, labels, all_posts, apply_hide=True):
    """표준 Blogspot 서식 파이프라인을 새 글 본문에 일괄 적용한다.

    순서: 상단 원본 고지문구 제거 -> 서식 표준화(restyle_content) -> 표준 3종 섹션
    삽입(add_purchase_guide_sections) -> 관련 글 자동 링크 -> 표준 마무리 문구(테스트구매+
    고지문구) append -> 모바일 CSS 블록 prepend -> (apply_hide=True면) 애드센스 심사기간
    정책에 따라 쿠팡 관련 내용 주석처리.
    """
    from _restyle_lib import restyle_content

    body = re.sub(
        r'<p>\s*이 포스팅은 쿠팡\s?파트너스 활동의 일환으로,?\s*이에 따른 일정액의 수수료를 제공받(?:을 수 있습니다|습니다)\.?\s*</p>\s*',
        '', raw_body, count=1
    )

    body = restyle_content(body)
    body = add_purchase_guide_sections(body, labels)
    body = auto_link_related_posts(body, all_posts)
    body = body.rstrip() + "\n" + TEST_PURCHASE_NOTE_HTML + "\n" + COUPANG_DISCLOSURE_SMALL

    if not body.startswith(MOBILE_CSS_MARKER):
        body = MOBILE_CSS_BLOCK + body

    if apply_hide:
        body = hide_coupang_content(body)

    return body


# 본문에 남아있는 "#태그,#태그,#태그" 형태의 해시태그 나열 줄을 찾기 위한 패턴
HASHTAG_BLOCK_PATTERN = re.compile(
    r'<p[^>]*>\s*(?:#[^\s,<]+\s*,\s*)+#[^\s,<]+\s*,?\s*</p>\s*',
    re.IGNORECASE
)
HASHTAG_INLINE_PATTERN = re.compile(
    r'(?:#[^\s,<]+\s*,\s*){1,}#[^\s,<]+',
    re.IGNORECASE
)

# 본문에서 지운 해시태그를 본문 텍스트 대신 Blogger 라벨(태그)로 다시 넣을 때 쓰는 기본 목록
DEFAULT_HASHTAG_LABELS = ["프로바이오틱스", "유산균", "여성유산균", "남성유산균", "갱년기유산균", "다이어트유산균"]



def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("blogger", "v3", credentials=creds)


def execute_with_retry(request, max_retries=4, log=None):
    """API 요청을 실행하되, 일시적 오류(레이트리밋 429, 서버 5xx, 네트워크 끊김)면
    지수 백오프(2→4→8→16초)로 재시도한다. 40개 글 일괄 수정 중간에 일시 오류로
    절반만 적용되는 사고를 방지하는 것이 목적. 영구 오류(권한 403, 404 등)는 즉시 올린다."""
    from googleapiclient.errors import HttpError
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return request.execute()
        except HttpError as e:
            status = e.resp.status if e.resp is not None else None
            if status not in (429, 500, 502, 503, 504):
                raise  # 재시도해도 소용없는 오류는 바로 올림
            last_error = e
        except (ConnectionError, OSError) as e:
            last_error = e
        if attempt < max_retries:
            wait = 2 ** (attempt + 1)
            if log:
                log(f"  일시 오류, {wait}초 후 재시도 ({attempt + 1}/{max_retries}): {last_error}")
            time.sleep(wait)
    raise last_error


def get_blog_id(service):
    result = execute_with_retry(service.blogs().getByUrl(url=BLOG_URL))
    return result["id"]


def fetch_all_posts(service, blog_id, fetch_bodies=True, statuses=None, log=None):
    """블로그의 전체 글을 페이지네이션 처리해서 한 번에 가져온다 (재시도 포함).

    statuses: 예 ['LIVE', 'DRAFT', 'SCHEDULED'] — 지정 안 하면 LIVE만 반환됨(API 기본값).
    """
    posts = []
    kwargs = {"blogId": blog_id, "maxResults": 500}
    if not fetch_bodies:
        kwargs["fetchBodies"] = False
    if statuses:
        kwargs["status"] = statuses
    request = service.posts().list(**kwargs)
    while request is not None:
        response = execute_with_retry(request, log=log)
        posts.extend(response.get("items", []))
        request = service.posts().list_next(request, response)
    return posts


def load_github_config():
    if not os.path.exists(GITHUB_CONFIG_FILE):
        raise FileNotFoundError(
            f"{GITHUB_CONFIG_FILE} 파일이 없습니다. username/repo/branch/token을 담은 파일을 만들어주세요."
        )
    with open(GITHUB_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_bytes_to_github(image_bytes, name_hint, github_cfg):
    """이미지 바이트를 GitHub 저장소에 업로드하고, 웹에서 접근 가능한 raw URL을 반환한다."""
    username = github_cfg["username"]
    repo = github_cfg["repo"]
    branch = github_cfg.get("branch", "main")
    token = github_cfg["token"]

    ext = os.path.splitext(name_hint)[1].split("?")[0] or ".jpg"
    if len(ext) > 5:  # 이상한 확장자 방지
        ext = ".jpg"
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", os.path.splitext(os.path.basename(name_hint))[0])
    # 광고차단 필터가 걸릴 만한 단어(banner, affiliate 등)는 무해한 단어로 치환
    safe_name = re.sub(r"(banner|affiliate|ads?|widget|sponsor)", "img", safe_name, flags=re.IGNORECASE)
    if not safe_name:
        safe_name = "product"
    filename = f"{safe_name}{ext}"

    content_b64 = base64.b64encode(image_bytes).decode("utf-8")

    api_url = f"https://api.github.com/repos/{username}/{repo}/contents/images/{filename}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # 같은 이름의 파일이 이미 있으면 GitHub가 기존 파일의 sha 값을 요구한다.
    # 없으면(404) 새 파일로 생성하고, 있으면 그 sha를 넣어 덮어쓴다.
    existing = requests.get(f"{api_url}?ref={branch}", headers=headers, timeout=15)
    sha = existing.json().get("sha") if existing.status_code == 200 else None

    data = {
        "message": f"add {filename}",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha

    res = requests.put(api_url, headers=headers, json=data, timeout=30)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"GitHub 업로드 실패 ({res.status_code}): {res.text[:300]}")

    return f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/images/{filename}"


def upload_to_github(filepath, github_cfg):
    """로컬 이미지 파일을 GitHub에 업로드한다 (기존 방식, 하위 호환용)."""
    with open(filepath, "rb") as f:
        image_bytes = f.read()
    return upload_bytes_to_github(image_bytes, os.path.basename(filepath), github_cfg)


def download_and_upload_to_github(image_url, github_cfg):
    """원본 이미지 URL(쿠팡 CDN 등)에서 서버가 직접 다운로드한 뒤 GitHub에 업로드한다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }
    res = requests.get(image_url, headers=headers, timeout=20)
    if res.status_code != 200 or not res.content:
        raise RuntimeError(f"이미지 다운로드 실패 ({res.status_code}): {image_url}")

    name_hint = os.path.basename(image_url.split("?")[0]) or "product.jpg"
    return upload_bytes_to_github(res.content, name_hint, github_cfg)


def build_product_card_html(product, image_url):
    """상품 1개 정보를 받아 좌:텍스트 / 우:이미지 카드 HTML을 생성한다."""
    name = product.get("NAME", "")
    brand = product.get("BRAND", "")
    desc = product.get("DESC", "")
    link = product.get("LINK", "")

    price_low = product.get("PRICE_LOW", "").strip()
    price_high = product.get("PRICE_HIGH", "").strip()
    price_basis = product.get("PRICE_BASIS", "").strip()
    price_single = product.get("PRICE", "").strip()  # 범위 대신 단일 참고가만 있는 경우
    rocket = product.get("ROCKET", "").strip().upper() in ("Y", "YES", "TRUE", "1")

    brand_html = f'<span style="font-size:0.9em; color:#777; font-weight:normal;"> ({brand})</span>' if brand else ""
    desc_html = desc.replace("\n", "<br>")

    basis_text = f" ({price_basis})" if price_basis else ""

    if price_low and price_high:
        price_line = f"최저가 {price_low}원 ~ 최고가 {price_high}원{basis_text}"
    elif price_single:
        price_line = f"참고가 {price_single}{basis_text}"
    else:
        price_line = "가격 확인불가 (쿠팡 링크에서 실시간가 확인)"

    price_html = (
        f'<span style="display:inline-block; margin-top:6px; padding:4px 10px; '
        f'background-color:#fff3f3; color:#e60000; font-size:0.92em; font-weight:bold; '
        f'border-radius:4px;">{price_line}</span>'
        f'<br><span style="font-size:0.82em; color:#999;">'
        f'※ 실제 가격은 쿠폰·할인 적용 여부에 따라 실시간으로 달라질 수 있습니다.</span>'
    )

    button_label = "🛒 쿠팡 최저가 확인하러 가기"

    button_style = (
        "display:block; margin-top:15px; padding:14px; background-color:#e60000; color:#ffffff; "
        "font-size:16px; font-weight:bold; border-radius:6px; text-decoration:none; text-align:center;"
    )

    return f'''<!-- PRODCARD:{link} -->
<div style="margin-bottom:30px; padding:15px; border:1px solid #eee; border-radius:8px;">
  <div style="display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:center; gap:20px;">
    <div style="flex:1; min-width:200px;">
      <p style="margin:0 0 6px 0; font-size:1.1em;"><strong>{name}</strong>{brand_html}</p>
      <p style="margin:0 0 8px 0; color:#555; line-height:1.6;">{desc_html}</p>
      <p style="margin:0;">{price_html}</p>
    </div>
    <div style="flex-shrink:0; text-align:center;">
      <a href="{link}" target="_blank" rel="nofollow sponsored">
        <img src="{image_url}" alt="{name}" width="120" height="240" style="border-radius:6px; display:block; margin:0 auto;">
      </a>
    </div>
  </div>
  <a href="{link}" target="_blank" rel="nofollow sponsored" style="{button_style}">{button_label}</a>
</div>
<!-- /PRODCARD -->'''


def parse_card_file(filepath):
    """card_inserts 폴더의 .txt 파일을 파싱한다.

    형식:
        SLUG: cfu
        IMAGE_DIR: 이미지/kids   (IMAGE 값이 로컬 파일명일 때만 사용, URL이면 무시됨)

        [상품1]
        NAME: 락토핏 생유산균 키즈
        BRAND: 종근당건강
        DESC: 보장균수 10억 CFU, 60포/2개월분
        PRICE_LOW: 18,540
        PRICE_HIGH: 30,910
        PRICE_BASIS: 60포 1통 기준
        ROCKET: Y
        SECTION: 혈당관리   (선택 항목. 있으면 본문의 "...영역 - 혈당관리" 처럼
                            섹션별 플레이스홀더에 나눠 들어감. 없으면 기존처럼
                            "...영역" 단일 플레이스홀더에 들어감)
        IMAGE: https://static.coupangcdn.com/image/affiliate/banner/xxxx@2x.jpg
        LINK: https://link.coupang.com/a/e69nLmQNlQ

        [상품2]
        ...

    PRICE_LOW/PRICE_HIGH가 둘 다 있으면 "최저가~최고가" 범위로 표시하고,
    범위 데이터가 부족하면 PRICE(단일 참고가) 항목만 넣어도 된다. 아무 가격도
    없으면 "가격 확인불가"로 표시된다. ROCKET을 Y로 주면 버튼 문구에 "쿠팡
    로켓배송으로 구매하러가기"가 들어간다.
    IMAGE 항목은 http(s):// 로 시작하면 원본 URL로 간주해 서버가 직접
    다운로드한 뒤 GitHub에 재업로드한다. http로 시작하지 않으면 로컬 파일
    (IMAGE_DIR 기준 상대경로)로 취급한다.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    header, _, body = content.partition("[상품1]")
    header_lines = header.strip().split("\n")
    slug = ""
    image_dir = ""
    for line in header_lines:
        if line.startswith("SLUG:"):
            slug = line.replace("SLUG:", "").strip()
        elif line.startswith("IMAGE_DIR:"):
            image_dir = line.replace("IMAGE_DIR:", "").strip()

    blocks = re.split(r"\[상품\d+\]", "[상품1]" + body)
    products = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        entry = {}
        for line in block.split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                entry[key.strip().upper()] = val.strip()
        if entry.get("NAME"):
            products.append(entry)

    return slug, image_dir, products


def parse_post_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---", 1)
    header = parts[0]
    body = parts[1].strip() if len(parts) > 1 else ""
    title = ""
    labels = []
    for line in header.strip().split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("LABELS:"):
            labels = [l.strip() for l in line.replace("LABELS:", "").split(",")]
    return title, labels, body


class App:
    def __init__(self, root):
        self.root = root
        root.title("방구석 약국 관리 프로그램")
        root.geometry("700x500")

        tk.Label(root, text="방구석 약국 관리 프로그램", font=("맑은 고딕", 16, "bold")).pack(pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="새 글 발행 (posts 폴더)", width=25, height=2,
                  command=self.run_publish).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="쿠팡 문구 위치 수정 (기존 글 전체)", width=30, height=2,
                  command=self.run_fix_disclosure).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="전체 글 목록 보기 (제목+URL)", width=25, height=2,
                  command=self.run_list_posts).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="관련 글 링크 자동 연결", width=25, height=2,
                  command=self.run_auto_link).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="쿠팡 상품 삽입 (inserts 폴더)", width=28, height=2,
                  command=self.run_insert_products).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="쿠팡 이미지 표시 오류 수정 (전체 글)", width=32, height=2,
                  command=self.run_fix_images).grid(row=1, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="GitHub 업로드 + 카드형 상품 삽입 (card_inserts 폴더)", width=40, height=2,
                  command=self.run_insert_product_cards).grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        tk.Button(btn_frame, text="모바일 폰트 확대 CSS 적용 (전체 글)", width=32, height=2,
                  command=self.run_add_mobile_css).grid(row=2, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="테스트구매 유도문구 추가 (전체 글)", width=32, height=2,
                  command=self.run_add_test_purchase_note).grid(row=3, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="해시태그 줄 제거 (전체 글)", width=32, height=2,
                  command=self.run_remove_hashtags).grid(row=3, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="해시태그를 라벨로 재등록 (전체 글)", width=32, height=2,
                  command=self.run_add_hashtag_labels).grid(row=3, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="대표이미지 삽입 (thumbnails 폴더)", width=32, height=2,
                  command=self.run_insert_thumbnails).grid(row=4, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="임시글 덮어쓰기+예약발행 (temp_publish 폴더)", width=38, height=2,
                  command=self.run_publish_temp).grid(row=4, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="쿠팡 숨김 (애드센스 심사용)", width=25, height=2, fg="#b00",
                  command=self.run_hide_coupang).grid(row=5, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="쿠팡 복원 (승인 후)", width=25, height=2, fg="#070",
                  command=self.run_restore_coupang).grid(row=5, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="네이버 내보내기 (naver_export 폴더)", width=32, height=2,
                  command=self.run_naver_export).grid(row=5, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="네이버 브릿지 글 발행 (bridge_input 폴더)", width=40, height=2,
                  command=self.run_bridge_posts).grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        tk.Button(btn_frame, text="네이버 발행 관리 (저장 리스트)", width=32, height=2, fg="#03c",
                  command=self.open_naver_manager).grid(row=6, column=2, padx=5, pady=5)

        tk.Label(root, text="실행 로그", font=("맑은 고딕", 10)).pack(anchor="w", padx=10)
        self.log_box = scrolledtext.ScrolledText(root, width=85, height=22)
        self.log_box.pack(padx=10, pady=5)

    def log(self, message):
        # tkinter는 스레드 안전하지 않으므로, 작업 스레드에서 직접 위젯을 만지지 않고
        # 메인 스레드 이벤트 루프에 위임한다 (간헐적 멈춤/크래시 방지).
        def _append():
            self.log_box.insert(tk.END, message + "\n")
            self.log_box.see(tk.END)
        self.root.after(0, _append)

    def _run_job(self, fn):
        """작업을 백그라운드 스레드로 실행하되, 한 번에 하나만 돌게 한다.
        (두 작업이 같은 글을 동시에 수정하면 나중 저장이 먼저 저장을 덮어써 유실됨)"""
        if getattr(self, "_job_running", False):
            self.log("!! 이미 다른 작업이 실행 중입니다. 끝난 뒤 다시 눌러주세요.")
            return
        self._job_running = True

        def _wrapper():
            try:
                fn()
            finally:
                self._job_running = False

        threading.Thread(target=_wrapper, daemon=True).start()

    def run_publish(self):
        self._run_job(self.publish_posts)

    def run_fix_disclosure(self):
        self._run_job(self.fix_disclosure)

    def run_list_posts(self):
        self._run_job(self.list_posts)

    def run_auto_link(self):
        self._run_job(self.auto_link)

    def run_insert_products(self):
        self._run_job(self.insert_products)

    def run_fix_images(self):
        self._run_job(self.fix_images)

    def run_insert_thumbnails(self):
        self._run_job(self.insert_thumbnails)

    def run_insert_product_cards(self):
        self._run_job(self.insert_product_cards)

    def run_add_mobile_css(self):
        self._run_job(self.add_mobile_css)

    def run_add_test_purchase_note(self):
        self._run_job(self.add_test_purchase_note)

    def run_remove_hashtags(self):
        self._run_job(self.remove_hashtags)

    def run_add_hashtag_labels(self):
        self._run_job(self.add_hashtag_labels)

    def run_hide_coupang(self):
        self._run_job(self.hide_coupang_all)

    def run_restore_coupang(self):
        self._run_job(self.restore_coupang_all)

    def run_publish_temp(self):
        self._run_job(self.publish_temp_posts)

    def run_bridge_posts(self):
        # 발행 여부는 메인 스레드에서 미리 묻는다 (작업 스레드에서 다이얼로그 금지)
        do_publish = messagebox.askyesno(
            "네이버 브릿지 글",
            "문단 정리 후 바로 네이버에 발행할까요?\n\n"
            "예: 비공개로 자동 발행 (확인 후 네이버에서 공개로 전환)\n"
            "아니오: 정리·클립보드 복사까지만 하고 발행은 직접",
            parent=self.root)
        self._run_job(lambda: self.process_bridge_posts(do_publish))

    def process_bridge_posts(self, do_publish=False):
        """bridge_input 폴더의 완성글(재미나이 웹에서 통으로 작성)을 네이버용으로 정리·발행한다.

        글 자체는 재미나이(웹)에서 편성표 기반으로 완성해서 받아오고 (2026-07-09 확정),
        여기서는 문단 간격 정리 + [방구석 약국] 링크 확인 + 발행만 담당한다.
        do_publish=True면 Playwright(창 보이는 모드)로 비공개 발행까지 자동 진행.
        """
        self.log("=== 네이버 브릿지 글 처리 시작 (bridge_input 폴더) ===")
        try:
            if not os.path.exists(BRIDGE_INPUT_FOLDER):
                os.makedirs(BRIDGE_INPUT_FOLDER)
                self.log(f"{BRIDGE_INPUT_FOLDER} 폴더가 없어서 새로 만들었습니다. "
                         f"완성글 파일(TITLE/BLOGSPOT_URL/TAGS/---/본문)을 넣고 다시 실행해주세요.")
                return
            if not os.path.exists(BRIDGE_DONE_FOLDER):
                os.makedirs(BRIDGE_DONE_FOLDER)

            files = sorted(glob.glob(os.path.join(BRIDGE_INPUT_FOLDER, "*.txt")))
            if not files:
                self.log(f"{BRIDGE_INPUT_FOLDER} 폴더에 처리할 파일이 없습니다.")
                return

            from gemini_client import write_image_prompts_file
            from naver_export import (export_post_for_naver, copy_html_to_clipboard,
                                      convert_content_for_naver, text_to_naver_html)

            for filepath in files:
                name = os.path.splitext(os.path.basename(filepath))[0]
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
                header, _, content = raw.partition("---")
                title, blogspot_url, tags = "", "", []
                for line in header.strip().split("\n"):
                    if line.startswith(("TITLE:", "PRODUCT:")):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("BLOGSPOT_URL:"):
                        blogspot_url = line.replace("BLOGSPOT_URL:", "").strip()
                    elif line.startswith("TAGS:"):
                        tags = [t.strip() for t in line.replace("TAGS:", "").split(",") if t.strip()]
                content = content.strip()
                if not title or not content:
                    self.log(f"건너뜀 (TITLE 또는 본문 누락): {filepath}")
                    continue

                self.log(f"[{name}] 브릿지 글 정리 중...")

                # 완성글을 문단 간격 있는 HTML로 변환 (빈 줄 = 문단 구분)
                body = text_to_naver_html(content)

                # 안전검증: 쇼핑몰 링크 금지, 방구석 약국 링크는 마지막에 보장
                if re.search(r'link\.coupang\.com|iherb\.com', body, re.IGNORECASE):
                    self.log(f"!! 건너뜀 (쇼핑몰 링크 포함 — 네이버 글 규칙 위반): {filepath}")
                    continue
                if blogspot_url and blogspot_url not in body:
                    body += (f'\n<p><br></p>\n<p>더 자세한 브랜드별 비교표와 최저가는 '
                             f'<a href="{blogspot_url}">[방구석 약국]</a> 링크에서 확인하세요.</p>')
                self.log(f"  제목: {title}")

                fake_post = {"title": title, "content": body,
                             "url": f"bridge/{name}", "labels": tags}
                out_dir = export_post_for_naver(fake_post, log=self.log)
                write_image_prompts_file(title, out_dir, html_content=body, log=self.log)
                self.log(f"  저장: {out_dir}")

                if do_publish:
                    from naver_publish import publish_to_naver
                    self.log("  네이버 발행 중 (비공개, 창이 뜨면 건드리지 마세요)...")
                    url = publish_to_naver(
                        title=title,
                        html_fragment=convert_content_for_naver(body),
                        tags=tags,
                        visibility="private",
                        headless=False,
                        log=self.log)
                    self.log(f"  발행 완료: {url}")
                else:
                    try:
                        copy_html_to_clipboard(convert_content_for_naver(body))
                        self.log("  본문 클립보드 복사됨 — 네이버 에디터에 Ctrl+V 하면 됩니다.")
                    except Exception:
                        pass

                shutil.move(filepath, os.path.join(BRIDGE_DONE_FOLDER, os.path.basename(filepath)))

            self.log("=== 네이버 브릿지 글 생성 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    # ------------------------------------------------------------------
    # 네이버 발행 관리 창 (방침 v2: 저장 리스트 -> 다중선택 -> 자동 날짜 배정 -> 예약발행)
    # ------------------------------------------------------------------
    def open_naver_manager(self):
        import naver_queue

        win = tk.Toplevel(self.root)
        win.title("네이버 발행 관리")
        win.geometry("820x460")

        cols = ("title", "status", "scheduled", "images", "tags")
        tree = ttk.Treeview(win, columns=cols, show="headings", selectmode="extended", height=14)
        for col, text, width in [("title", "제목", 320), ("status", "상태", 80),
                                 ("scheduled", "예약일시", 130), ("images", "이미지", 60), ("tags", "태그", 180)]:
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh():
            tree.delete(*tree.get_children())
            data = naver_queue.load_queue()
            for p in data["posts"]:
                status = {"ready": "대기", "scheduled": "예약됨"}.get(p["status"], p["status"])
                tree.insert("", "end", iid=p["id"], values=(
                    p["title"], status, p.get("scheduled_at") or "-",
                    f"{len(p.get('images', []))}장", ", ".join(p.get("tags", []))))

        def add_set():
            txt_path = filedialog.askopenfilename(
                parent=win, title="글 파일 선택 (TITLE/BLOGSPOT_URL/TAGS/---/본문)",
                filetypes=[("텍스트", "*.txt"), ("모든 파일", "*.*")])
            if not txt_path:
                return
            with open(txt_path, "r", encoding="utf-8") as f:
                raw = f.read()
            header, _, content = raw.partition("---")
            title, blogspot_url, tags = "", "", []
            for line in header.strip().split("\n"):
                if line.startswith(("TITLE:", "PRODUCT:")):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("BLOGSPOT_URL:"):
                    blogspot_url = line.replace("BLOGSPOT_URL:", "").strip()
                elif line.startswith("TAGS:"):
                    tags = [t.strip() for t in line.replace("TAGS:", "").split(",") if t.strip()]
            content = content.strip()
            if not title or not content:
                messagebox.showerror("형식 오류", "TITLE 또는 본문(--- 아래)이 없습니다.", parent=win)
                return

            img_paths = filedialog.askopenfilenames(
                parent=win, title="이미지 선택 (썸네일 먼저, 최대 6장 — 없으면 취소)",
                filetypes=[("이미지", "*.png *.jpg *.jpeg *.webp *.jfif")])
            img_paths = list(img_paths)[:6]

            from naver_export import text_to_naver_html, insert_images_into_body
            body = text_to_naver_html(content)
            if re.search(r'link\.coupang\.com|iherb\.com', body, re.IGNORECASE):
                messagebox.showerror("규칙 위반", "본문에 쇼핑몰 링크가 있어 등록할 수 없습니다.", parent=win)
                return
            if blogspot_url and blogspot_url not in body:
                body += (f'\n<p><br></p>\n<p>더 자세한 브랜드별 비교표와 최저가는 '
                         f'<a href="{blogspot_url}">[방구석 약국]</a> 링크에서 확인하세요.</p>')

            image_urls = []
            if img_paths:
                try:
                    github_cfg = load_github_config()
                    stamp = time.strftime("%Y%m%d%H%M%S")
                    for i, path in enumerate(img_paths):
                        with open(path, "rb") as f:
                            data_bytes = f.read()
                        ext = os.path.splitext(path)[1].lower()
                        if ext == ".jfif":
                            ext = ".jpg"
                        url = upload_bytes_to_github(data_bytes, f"nv_{stamp}_{i}{ext}", github_cfg)
                        image_urls.append(url)
                        self.log(f"  이미지 업로드: {os.path.basename(path)}")
                except Exception as e:
                    messagebox.showerror("이미지 업로드 실패", str(e), parent=win)
                    return
                body = insert_images_into_body(body, image_urls)

            naver_queue.add_post(title, body, tags, image_urls)
            self.log(f"[발행 관리] 글 세트 등록: {title} (이미지 {len(image_urls)}장)")
            refresh()

        def schedule_selected():
            import naver_queue as nq
            selected = list(tree.selection())
            if not selected:
                messagebox.showinfo("안내", "발행할 글을 목록에서 선택하세요 (Ctrl+클릭으로 여러 개).", parent=win)
                return
            if len(selected) > nq.MAX_BATCH:
                messagebox.showerror("초과", f"한 번에 최대 {nq.MAX_BATCH}개까지만 등록할 수 있습니다.", parent=win)
                return

            assigned = nq.assign_schedule_dates(selected)
            if not assigned:
                messagebox.showinfo("안내", "선택한 글 중 '대기' 상태인 글이 없습니다.", parent=win)
                return
            plan = "\n".join(f"· {e['title'][:30]} → {dt.strftime('%m/%d %H:%M')}" for e, dt in assigned)
            if not messagebox.askyesno("예약 확인",
                                       f"아래 일정으로 네이버 예약발행을 등록할까요?\n\n{plan}\n\n"
                                       "(Chrome 창이 뜨면 끝날 때까지 건드리지 마세요)", parent=win):
                for e, _ in assigned:
                    nq.unassign(e["id"])
                refresh()
                return
            refresh()

            def job():
                import datetime as _dt
                from naver_publish import batch_register_scheduled
                entries = []
                for e, dt in assigned:
                    body = nq.get_post_body(e)

                    def make_cb(pid):
                        def cb(ok, url):
                            if ok:
                                nq.mark_registered(pid, url)
                            else:
                                nq.unassign(pid)
                        return cb
                    entries.append((e["title"], body, e["tags"], dt, make_cb(e["id"])))
                batch_register_scheduled(entries, log=self.log)
                self.log("[발행 관리] 예약 등록 작업 종료 — 목록 새로고침 버튼을 눌러 확인하세요.")

            self._run_job(job)

        btns = tk.Frame(win)
        btns.pack(pady=5)
        tk.Button(btns, text="글 세트 등록 (글파일+이미지)", width=25, command=add_set).grid(row=0, column=0, padx=5)
        tk.Button(btns, text="선택 글 발행 예약 (하루 1개씩 자동 배정)", width=32, command=schedule_selected).grid(row=0, column=1, padx=5)
        tk.Button(btns, text="새로고침", width=10, command=refresh).grid(row=0, column=2, padx=5)

        refresh()

    def run_naver_export(self):
        # 다이얼로그는 tkinter 메인 스레드에서만 띄울 수 있으므로 여기서 먼저 묻고,
        # 실제 변환 작업만 백그라운드로 넘긴다.
        keyword = simpledialog.askstring(
            "네이버 내보내기",
            "내보낼 글 제목에 포함된 키워드를 입력하세요.\n(빈칸으로 두면 전체 글을 내보냅니다)",
            parent=self.root)
        if keyword is None:  # 취소
            return
        use_gemini = messagebox.askyesno(
            "브릿지 글 생성",
            "Gemini로 네이버용 브릿지 글을 새로 쓸까요?\n\n"
            "예: 주부 페르소나 1인칭 글을 독립 작성 — 목차/비교표 없이,\n"
            "    마지막에 방구석 약국 연결 링크만 포함 (권장·확정 방식)\n"
            "아니오: 블로그스팟 원문 서식만 정리해서 내보냅니다",
            parent=self.root)
        self._run_job(lambda: self.naver_export_posts(keyword.strip(), use_gemini))

    def naver_export_posts(self, keyword, use_gemini=False):
        """제목 키워드로 글을 찾아 네이버 발행 준비 폴더(naver_export/<슬러그>/)를 만든다.

        use_gemini=True면 Blogspot 글의 사실관계만 참고해서 주부 페르소나의
        1인칭 브릿지 글을 독립적으로 새로 쓴다 (변환 아님 — 2026-07-09 확정 방식).
        네이버 글은 트래픽을 Blogspot 비교표로 보내는 브릿지 역할만 한다.
        내보낸 글이 1개면 클립보드에도 자동 복사 — 네이버 에디터에 바로 Ctrl+V 하면 됨.
        """
        self.log(f"=== 네이버 내보내기 시작 (키워드: '{keyword or '전체'}', 브릿지 글 생성: {'예' if use_gemini else '아니오'}) ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)
            posts = fetch_all_posts(service, blog_id, log=self.log)

            keyword_norm = keyword.replace(" ", "")
            if keyword_norm:
                targets = [p for p in posts if keyword_norm in p["title"].replace(" ", "")]
            else:
                targets = posts

            if not targets:
                self.log(f"제목에 '{keyword}'가 포함된 글이 없습니다.")
                return

            last_fragment = None
            for post in targets:
                export_post = post
                if use_gemini:
                    from gemini_client import write_bridge_post
                    cleaned = convert_content_for_naver(post["content"])
                    new_title, new_body = write_bridge_post(
                        post["title"], cleaned, post["url"], log=self.log)
                    export_post = dict(post)
                    export_post["title"] = new_title
                    export_post["content"] = new_body
                    self.log(f"  브릿지 글 제목: {new_title}")

                out_dir = export_post_for_naver(export_post, log=self.log)
                last_fragment = convert_content_for_naver(export_post["content"])
                self.log(f"내보내기 완료: {export_post['title']}\n  -> {out_dir}")

                # 이미지 프롬프트 6개(썸네일1+본문5)도 함께 뽑아둔다 — 사용자가 직접 생성 후
                # 이 폴더에 저장하면 됨 (이미지 API는 유료라 프롬프트만 제공)
                try:
                    from gemini_client import write_image_prompts_file
                    write_image_prompts_file(export_post["title"], out_dir,
                                             html_content=export_post["content"], log=self.log)
                except Exception as e:
                    self.log(f"  이미지 프롬프트 생성 실패: {e}")

            if len(targets) == 1 and last_fragment:
                try:
                    copy_html_to_clipboard(last_fragment)
                    self.log("본문이 클립보드에 복사됐습니다 — 네이버 에디터에서 바로 Ctrl+V 하세요.")
                except Exception as e:
                    self.log(f"클립보드 복사 실패 (naver.html을 직접 복사하세요): {e}")

            self.log(f"=== 네이버 내보내기 종료: {len(targets)}개 글 ===")
            self.log("제목/태그는 각 폴더의 meta.txt에 있습니다.\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def hide_coupang_all(self):
        """전체 글의 쿠팡 카드/링크/고지문구를 HTML 주석으로 숨긴다 (애드센스 심사용)."""
        self.log("=== 쿠팡 링크/고지문구 숨김 시작 (심사용) ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)
            posts = fetch_all_posts(service, blog_id, log=self.log)
            updated = 0
            for post in posts:
                content = post["content"]
                hidden = hide_coupang_content(content)
                if hidden == content:
                    continue
                # 안전검사: 숨긴 결과를 복원하면 반드시 원본과 같아야 발행한다
                if restore_coupang_content(hidden) != restore_coupang_content(content):
                    self.log(f"!! 안전검사 실패, 건너뜀: {post['title']}")
                    continue
                execute_with_retry(service.posts().update(
                    blogId=blog_id, postId=post["id"],
                    body={"title": post["title"], "content": hidden, "labels": post.get("labels", [])}
                ), log=self.log)
                updated += 1
                self.log(f"숨김 완료: {post['title']}")
            self.log(f"=== 숨김 종료: {updated}개 글 수정 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def restore_coupang_all(self):
        """숨겨둔 쿠팡 카드/링크/고지문구를 원상복구한다 (애드센스 승인 후 사용)."""
        self.log("=== 쿠팡 링크/고지문구 복원 시작 (승인 후) ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)
            posts = fetch_all_posts(service, blog_id, log=self.log)
            updated = 0
            for post in posts:
                content = post["content"]
                restored = restore_coupang_content(content)
                if restored == content:
                    continue
                execute_with_retry(service.posts().update(
                    blogId=blog_id, postId=post["id"],
                    body={"title": post["title"], "content": restored, "labels": post.get("labels", [])}
                ), log=self.log)
                updated += 1
                self.log(f"복원 완료: {post['title']}")
            self.log(f"=== 복원 종료: {updated}개 글 수정 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def publish_temp_posts(self):
        """temp_publish 폴더의 파일로 '임시N' 글을 덮어쓰고, SCHEDULE이 있으면 예약 발행한다.

        신규 글 insert()가 스팸 차단에 걸려 있어서 확립된 워크플로우
        (대시보드에서 '임시N' 수동 등록 → API로 덮어쓰기 → 예약 발행)를 버튼으로 공식화한 것.

        파일 형식 (temp_publish/임시1.txt):
            TITLE: 실제 제목
            LABELS: 라벨1, 라벨2
            SCHEDULE: 2026-07-08T06:00:00+09:00   (선택 — 없으면 즉시 발행 상태 유지)
            ---
            <본문 HTML>
        """
        self.log("=== 임시글 덮어쓰기 + 예약발행 시작 (temp_publish 폴더) ===")
        try:
            if not os.path.exists(TEMP_PUBLISH_FOLDER):
                os.makedirs(TEMP_PUBLISH_FOLDER)
                self.log(f"{TEMP_PUBLISH_FOLDER} 폴더가 없어서 새로 만들었습니다. "
                         f"임시1.txt 형식의 파일을 넣고 다시 실행해주세요.")
                return
            if not os.path.exists(TEMP_PUBLISHED_FOLDER):
                os.makedirs(TEMP_PUBLISHED_FOLDER)

            files = sorted(glob.glob(os.path.join(TEMP_PUBLISH_FOLDER, "*.txt")))
            if not files:
                self.log(f"{TEMP_PUBLISH_FOLDER} 폴더에 처리할 파일이 없습니다.")
                return

            service = get_service()
            blog_id = get_blog_id(service)
            posts = fetch_all_posts(service, blog_id, statuses=["LIVE", "DRAFT", "SCHEDULED"], log=self.log)

            for filepath in files:
                temp_name = os.path.splitext(os.path.basename(filepath))[0].strip()  # 예: "임시1"
                matches = [p for p in posts if p["title"] == temp_name]
                if not matches:
                    self.log(f"매칭 실패 (제목이 '{temp_name}'인 글 없음 — 대시보드에서 먼저 수동 등록 필요): {filepath}")
                    continue
                post = matches[0]

                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
                header, _, body = raw.partition("---")
                title, labels, schedule = "", [], ""
                for line in header.strip().split("\n"):
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("LABELS:"):
                        labels = [l.strip() for l in line.replace("LABELS:", "").split(",")]
                    elif line.startswith("SCHEDULE:"):
                        schedule = line.replace("SCHEDULE:", "").strip()
                body = body.strip()
                if not title or not body:
                    self.log(f"건너뜀 (TITLE 또는 본문 없음): {filepath}")
                    continue

                if not body.startswith(MOBILE_CSS_MARKER):
                    body = MOBILE_CSS_BLOCK + body

                execute_with_retry(service.posts().update(
                    blogId=blog_id, postId=post["id"],
                    body={"title": title, "content": body, "labels": labels}
                ), log=self.log)
                self.log(f"덮어쓰기 완료: {temp_name} -> {title}")

                if schedule:
                    execute_with_retry(service.posts().revert(blogId=blog_id, postId=post["id"]), log=self.log)
                    result = execute_with_retry(
                        service.posts().publish(blogId=blog_id, postId=post["id"], publishDate=schedule),
                        log=self.log)
                    self.log(f"  예약발행 설정: {schedule} (상태: {result.get('status')})")

                shutil.move(filepath, os.path.join(TEMP_PUBLISHED_FOLDER, os.path.basename(filepath)))

            self.log("=== 임시글 덮어쓰기 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def insert_product_cards(self):
        self.log("=== GitHub 업로드 + 카드형 상품 삽입 시작 ===")
        try:
            if not os.path.exists(CARD_INSERTS_FOLDER):
                os.makedirs(CARD_INSERTS_FOLDER)
                self.log(f"{CARD_INSERTS_FOLDER} 폴더가 없어서 새로 만들었습니다. 파일을 넣고 다시 실행해주세요.")
                return
            if not os.path.exists(CARD_INSERTED_FOLDER):
                os.makedirs(CARD_INSERTED_FOLDER)

            try:
                github_cfg = load_github_config()
            except Exception as e:
                self.log(f"GitHub 설정 오류: {e}")
                return

            files = sorted(glob.glob(os.path.join(CARD_INSERTS_FOLDER, "*.txt")))
            if not files:
                self.log(f"{CARD_INSERTS_FOLDER} 폴더에 처리할 파일이 없습니다.")
                return

            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            PLACEHOLDER = "(쿠팡 파트너스 상품 링크/위젯 삽입 영역)"

            for filepath in files:
                slug, image_dir, products = parse_card_file(filepath)
                if not slug or not products:
                    self.log(f"건너뜀 (형식 오류): {filepath}")
                    continue

                matched_post = None
                for post in posts:
                    if slug in post["url"]:
                        matched_post = post
                        break
                if not matched_post:
                    self.log(f"매칭 실패 (해당 URL 슬러그를 가진 글 없음): {slug}")
                    continue

                content = matched_post["content"]

                cards_html = []
                ok = True
                for product in products:
                    image_value = product.get("IMAGE", "")
                    if not image_value:
                        self.log(f"  IMAGE 값 없음 (상품: {product.get('NAME')})")
                        ok = False
                        break

                    try:
                        if image_value.startswith("http://") or image_value.startswith("https://"):
                            self.log(f"  원본 이미지 다운로드 중: {image_value}")
                            image_url = download_and_upload_to_github(image_value, github_cfg)
                        else:
                            local_image_path = os.path.join(image_dir, image_value) if image_dir else image_value
                            if not os.path.exists(local_image_path):
                                self.log(f"  이미지 파일 없음: {local_image_path} (상품: {product.get('NAME')})")
                                ok = False
                                break
                            self.log(f"  GitHub 업로드 중: {local_image_path}")
                            image_url = upload_to_github(local_image_path, github_cfg)
                        self.log(f"  업로드 완료 -> {image_url}")
                    except Exception as e:
                        self.log(f"  이미지 처리 실패: {image_value} / 오류: {e}")
                        ok = False
                        break
                    cards_html.append((product, build_product_card_html(product, image_url)))

                if not ok:
                    self.log(f"건너뜀 (이미지 업로드 문제로 카드 미삽입): {matched_post['title']}")
                    continue

                new_content = content
                changed_count = 0

                # SECTION이 지정된 상품은 "...영역 - {SECTION}" 형태의 전용
                # 플레이스홀더에 나눠 넣는다 (한 글에 목적별로 카드 삽입 위치가 여러 개인 경우용).
                section_groups = {}
                flat_cards = []
                for product, card_html in cards_html:
                    section = product.get("SECTION", "").strip()
                    if section:
                        section_groups.setdefault(section, []).append(card_html)
                    else:
                        flat_cards.append((product, card_html))

                for section, htmls in section_groups.items():
                    section_placeholder = f"(쿠팡 파트너스 상품 링크/위젯 삽입 영역 - {section})"
                    if section_placeholder in new_content:
                        new_content = new_content.replace(section_placeholder, "\n".join(htmls))
                        changed_count += len(htmls)
                    else:
                        self.log(f"  섹션 플레이스홀더를 찾지 못함 ('{section}'): {matched_post['title']}")

                use_placeholder = bool(flat_cards) and PLACEHOLDER in new_content

                if use_placeholder:
                    combined_html = "\n".join(html for _, html in flat_cards)
                    new_content = new_content.replace(PLACEHOLDER, combined_html)
                    changed_count += len(flat_cards)
                elif flat_cards:
                    # 플레이스홀더가 없는 경우: 두 가지 케이스를 순서대로 시도한다.
                    # (1) 이미 새 카드(PRODCARD 마커 포함)가 들어가 있으면 통째로 교체 (템플릿 업데이트용)
                    # (2) 그게 없으면, 처음 상태 그대로인 옛 다이나믹 배너를 링크 기준으로 찾아 교체
                    for product, card_html in flat_cards:
                        link = product.get("LINK", "")
                        name = product.get("NAME", "")
                        if not link:
                            continue

                        escaped_link = re.escape(link)

                        # (0) 예전 잘못된 부분교체로 남았을 수 있는 고아 텍스트 블록/중복 소개문단은
                        #     PRODCARD 매칭 여부와 관계없이 항상 먼저 청소한다.
                        if name:
                            escaped_name = re.escape(name)

                            orphan_div_pattern = re.compile(
                                r'<div[^>]*flex:\s*1[^>]*>\s*<p[^>]*>\s*<strong>' + escaped_name +
                                r'</strong>.*?</div>\s*',
                                re.DOTALL
                            )
                            new_content, removed_orphan = orphan_div_pattern.subn('', new_content, count=1)
                            if removed_orphan:
                                self.log(f"  고아 텍스트 블록 제거: {name}")

                            intro_pattern = re.compile(
                                r'<p[^>]*>\s*<strong>' + escaped_name + r'</strong>.*?</p>\s*',
                                re.DOTALL
                            )
                            new_content, removed_intro = intro_pattern.subn('', new_content, count=1)
                            if removed_intro:
                                self.log(f"  중복 소개 문단 제거: {name}")

                        # (1) 기존 PRODCARD 블록이 있는 경우: 마커 기준으로 통째로 교체
                        prodcard_pattern = re.compile(
                            r'<!-- PRODCARD:' + escaped_link + r' -->.*?<!-- /PRODCARD -->',
                            re.DOTALL
                        )
                        new_content, n = prodcard_pattern.subn(card_html, new_content, count=1)
                        if n > 0:
                            changed_count += 1
                            continue

                        old_block_pattern = re.compile(
                            r'<div[^>]*>\s*<a[^>]*href="' + escaped_link + r'"[^>]*>.*?</a>\s*</div>',
                            re.DOTALL
                        )
                        new_content, n = old_block_pattern.subn(card_html, new_content, count=1)
                        if n > 0:
                            changed_count += 1
                            continue

                        # (2) 위 두 가지 다 해당 안 되면: 완전히 새로운 상품이라는 뜻이므로
                        #     기존 글은 건드리지 않고, 카드를 글 끝부분(테스트구매 유도문구/고지문구 앞)에 추가한다.
                        insertion_marker = None
                        for marker in (TEST_PURCHASE_NOTE_MARKER, COUPANG_DISCLOSURE_SMALL):
                            if marker in new_content:
                                insertion_marker = marker
                                break
                        if insertion_marker:
                            new_content = new_content.replace(insertion_marker, card_html + "\n" + insertion_marker, 1)
                        else:
                            new_content = new_content.strip() + "\n" + card_html
                        changed_count += 1
                        self.log(f"  신규 카드로 글 끝부분에 추가: {product.get('NAME')}")

                if changed_count == 0:
                    self.log(f"건너뜀 (교체할 대상을 찾지 못함): {matched_post['title']}")
                    continue

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=matched_post["id"],
                        body={
                            "kind": "blogger#post",
                            "title": matched_post["title"],
                            "content": new_content,
                            "labels": matched_post.get("labels", []),
                        }
                        ), log=self.log)
                    self.log(f"카드 삽입/교체 완료 ({changed_count}개 상품): {matched_post['title']}")
                    shutil.move(filepath, os.path.join(CARD_INSERTED_FOLDER, os.path.basename(filepath)))
                except Exception as e:
                    self.log(f"업데이트 실패: {matched_post['title']} / 오류: {e}")

            self.log("=== GitHub 업로드 + 카드형 상품 삽입 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def add_mobile_css(self):
        self.log("=== 모바일 폰트 확대 CSS 적용 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            old_block_pattern = re.compile(
                re.escape(MOBILE_CSS_MARKER) + r'<style>.*?</style>',
                re.DOTALL
            )

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]

                if MOBILE_CSS_MARKER in content:
                    new_content, n = old_block_pattern.subn(MOBILE_CSS_BLOCK, content, count=1)
                    if n == 0 or new_content == content:
                        self.log(f"건너뜀 (이미 최신 상태): {title}")
                        continue
                else:
                    new_content = MOBILE_CSS_BLOCK + content

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                        body={"kind": "blogger#post", "title": title, "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                    self.log(f"CSS 적용 완료: {title}")
                except Exception as e:
                    self.log(f"업데이트 실패: {title} / 오류: {e}")

            self.log("=== 모바일 폰트 확대 CSS 적용 종료 ===\n")
            self.log("참고: 새 글을 발행할 때는 이 CSS가 자동으로 들어가지 않으니, 새 글 발행 후 이 버튼을 다시 눌러주세요.\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def add_test_purchase_note(self):
        self.log("=== 테스트구매 유도문구 추가 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]

                if COUPANG_HIDDEN_OPEN in content:
                    self.log(f"건너뜀 (쿠팡 숨김 상태 — 심사 중에는 눈에 보이는 유도문구를 추가하지 않음): {title}")
                    continue

                if TEST_PURCHASE_NOTE_MARKER in content:
                    self.log(f"건너뜀 (이미 적용됨): {title}")
                    continue

                # 쿠팡 파트너스 고지문구(COUPANG_DISCLOSURE_SMALL) 바로 앞에 삽입,
                # 고지문구가 없는 글이면 그냥 맨 끝에 삽입한다.
                if COUPANG_DISCLOSURE_SMALL in content:
                    new_content = content.replace(
                        COUPANG_DISCLOSURE_SMALL,
                        TEST_PURCHASE_NOTE_HTML + COUPANG_DISCLOSURE_SMALL
                    )
                else:
                    new_content = content.strip() + "\n\n" + TEST_PURCHASE_NOTE_HTML

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                        body={"kind": "blogger#post", "title": title, "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                    self.log(f"유도문구 추가 완료: {title}")
                except Exception as e:
                    self.log(f"업데이트 실패: {title} / 오류: {e}")

            self.log("=== 테스트구매 유도문구 추가 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def remove_hashtags(self):
        self.log("=== 해시태그 줄 제거 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]

                # 1) <p>#태그,#태그,...#태그</p> 형태로 통째로 감싸진 줄 제거
                new_content, n1 = HASHTAG_BLOCK_PATTERN.subn('', content)
                # 2) <p> 태그 없이 본문 중간에 남은 "#태그,#태그,..." 나열도 제거
                new_content, n2 = HASHTAG_INLINE_PATTERN.subn('', new_content)

                total = n1 + n2
                if total == 0:
                    self.log(f"건너뜀 (해시태그 없음): {title}")
                    continue

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                        body={"kind": "blogger#post", "title": title, "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                    self.log(f"해시태그 {total}곳 제거 완료: {title}")
                except Exception as e:
                    self.log(f"업데이트 실패: {title} / 오류: {e}")

            self.log("=== 해시태그 줄 제거 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def add_hashtag_labels(self):
        self.log("=== 해시태그를 라벨로 재등록 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]
                existing_labels = post.get("labels", [])

                merged_labels = list(existing_labels)
                added = []
                for label in DEFAULT_HASHTAG_LABELS:
                    if label not in merged_labels:
                        merged_labels.append(label)
                        added.append(label)

                if not added:
                    self.log(f"건너뜀 (이미 라벨 있음): {title}")
                    continue

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                        body={
                            "kind": "blogger#post",
                            "title": title,
                            "content": content,
                            "labels": merged_labels,
                        }
                        ), log=self.log)
                    self.log(f"라벨 추가 완료 ({', '.join(added)}): {title}")
                except Exception as e:
                    self.log(f"업데이트 실패: {title} / 오류: {e}")

            self.log("=== 해시태그를 라벨로 재등록 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def insert_thumbnails(self):
        self.log("=== 대표이미지 삽입 시작 (thumbnails 폴더) ===")
        try:
            if not os.path.exists(THUMBNAILS_FOLDER):
                os.makedirs(THUMBNAILS_FOLDER)
                self.log(f"{THUMBNAILS_FOLDER} 폴더가 없어서 새로 만들었습니다. "
                         f"이미지를 넣고(파일명=제목 키워드) 다시 실행해주세요.")
                return
            if not os.path.exists(THUMBNAILS_DONE_FOLDER):
                os.makedirs(THUMBNAILS_DONE_FOLDER)

            try:
                github_cfg = load_github_config()
            except Exception as e:
                self.log(f"GitHub 설정 오류: {e}")
                return

            files = []
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                files.extend(glob.glob(os.path.join(THUMBNAILS_FOLDER, ext)))
            files.sort()
            if not files:
                self.log(f"{THUMBNAILS_FOLDER} 폴더에 처리할 이미지가 없습니다.")
                return

            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            thumb_block_pattern = re.compile(
                re.escape(THUMBNAIL_MARKER) + r'.*?</div>',
                re.DOTALL
            )

            for filepath in files:
                keyword = os.path.splitext(os.path.basename(filepath))[0].strip()
                keyword_norm = keyword.replace(" ", "")

                matches = [p for p in posts if keyword_norm in p["title"].replace(" ", "")]
                if not matches:
                    self.log(f"매칭 실패 (제목에 '{keyword}' 포함된 글 없음): {filepath}")
                    continue
                if len(matches) > 1:
                    titles = ", ".join(m["title"] for m in matches)
                    self.log(f"매칭 모호함 ('{keyword}'가 {len(matches)}개 글에 포함됨, 더 구체적인 키워드로 파일명 변경 필요): {titles}")
                    continue

                post = matches[0]
                try:
                    self.log(f"GitHub 업로드 중: {filepath}")
                    slug = os.path.splitext(post["url"].rstrip("/").split("/")[-1])[0]
                    ext = os.path.splitext(filepath)[1]
                    with open(filepath, "rb") as f:
                        image_bytes = f.read()
                    image_url = upload_bytes_to_github(image_bytes, f"thumb_{slug}{ext}", github_cfg)
                    self.log(f"  업로드 완료 -> {image_url}")
                except Exception as e:
                    self.log(f"  이미지 업로드 실패: {filepath} / 오류: {e}")
                    continue

                thumb_html = (
                    THUMBNAIL_MARKER +
                    '<div style="text-align:center; margin-bottom:20px;">'
                    f'<img src="{image_url}" alt="{post["title"]}" '
                    'style="max-width:100%; height:auto; border-radius:8px;">'
                    '</div>'
                )

                content = post["content"]
                if THUMBNAIL_MARKER in content:
                    new_content, n = thumb_block_pattern.subn(thumb_html, content, count=1)
                    if n == 0:
                        new_content = thumb_html + content
                else:
                    insert_at = 0
                    if content.startswith(MOBILE_CSS_MARKER):
                        idx = content.find("</style>")
                        if idx != -1:
                            insert_at = idx + len("</style>")
                    new_content = content[:insert_at] + thumb_html + content[insert_at:]

                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post["id"],
                        body={"kind": "blogger#post", "title": post["title"], "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                    self.log(f"대표이미지 삽입 완료: {post['title']}")
                except Exception as e:
                    self.log(f"업데이트 실패: {post['title']} / 오류: {e}")
                    continue

                base_name = os.path.basename(filepath)
                dest_path = os.path.join(THUMBNAILS_DONE_FOLDER, base_name)
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(base_name)
                    suffix = 2
                    while os.path.exists(os.path.join(THUMBNAILS_DONE_FOLDER, f"{name}_{suffix}{ext}")):
                        suffix += 1
                    dest_path = os.path.join(THUMBNAILS_DONE_FOLDER, f"{name}_{suffix}{ext}")
                try:
                    shutil.move(filepath, dest_path)
                except Exception as e:
                    self.log(f"경고: 글 수정은 성공했지만 파일 이동 실패 ({filepath} -> {dest_path}) / 오류: {e}")

            self.log("=== 대표이미지 삽입 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def fix_images(self):
        self.log("=== 쿠팡 이미지 표시 오류 수정 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            # coupangcdn.com 이미지를 가진 <img> 태그 중 referrerpolicy가 없는 것을 찾아 추가
            img_pattern = re.compile(r'<img\s+([^>]*coupangcdn\.com[^>]*)>', re.IGNORECASE)

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]

                def fix_tag(match):
                    attrs = match.group(1)
                    if "referrerpolicy" in attrs.lower():
                        return match.group(0)
                    return f'<img {attrs} referrerpolicy="unsafe-url">'

                new_content, count = img_pattern.subn(fix_tag, content)

                if count > 0 and new_content != content:
                    try:
                        execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                            body={"kind": "blogger#post", "title": title, "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                        self.log(f"이미지 {count}개 수정 완료: {title}")
                    except Exception as e:
                        self.log(f"업데이트 실패: {title} / 오류: {e}")
                else:
                    self.log(f"건너뜀 (수정 대상 없음): {title}")

            self.log("=== 쿠팡 이미지 표시 오류 수정 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def insert_products(self):
        self.log("=== 쿠팡 상품 삽입 시작 (inserts 폴더) ===")
        try:
            INSERTS_FOLDER = "inserts"
            INSERTED_FOLDER = "inserted"
            if not os.path.exists(INSERTS_FOLDER):
                os.makedirs(INSERTS_FOLDER)
                self.log("inserts 폴더가 없어서 새로 만들었습니다. 파일을 넣고 다시 실행해주세요.")
                return
            if not os.path.exists(INSERTED_FOLDER):
                os.makedirs(INSERTED_FOLDER)

            files = sorted(glob.glob(os.path.join(INSERTS_FOLDER, "*.txt")))
            if not files:
                self.log("inserts 폴더에 처리할 파일이 없습니다.")
                return

            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            PLACEHOLDER = "(쿠팡 파트너스 상품 링크/위젯 삽입 영역)"

            for filepath in files:
                slug = os.path.splitext(os.path.basename(filepath))[0]
                with open(filepath, "r", encoding="utf-8") as f:
                    insert_html = f.read()

                matched_post = None
                for post in posts:
                    if slug in post["url"]:
                        matched_post = post
                        break

                if not matched_post:
                    self.log(f"매칭 실패 (해당 URL 슬러그를 가진 글 없음): {slug}")
                    continue

                content = matched_post["content"]
                if PLACEHOLDER not in content:
                    self.log(f"건너뜀 (플레이스홀더 없음, 이미 처리됐을 수 있음): {matched_post['title']}")
                    continue

                new_content = content.replace(PLACEHOLDER, insert_html)
                try:
                    execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=matched_post["id"],
                        body={"kind": "blogger#post", "title": matched_post["title"], "content": new_content, "labels": matched_post.get("labels", [])}
                        ), log=self.log)
                    self.log(f"삽입 완료: {matched_post['title']}")
                    shutil.move(filepath, os.path.join(INSERTED_FOLDER, os.path.basename(filepath)))
                except Exception as e:
                    self.log(f"업데이트 실패: {matched_post['title']} / 오류: {e}")

            self.log("=== 쿠팡 상품 삽입 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def auto_link(self):
        self.log("=== 관련 글 링크 자동 연결 시작 (고정 매핑표 사용) ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            # 실제 발행된 URL을 여기서 확인해서 매핑 (본인 블로그 주소 기준으로 이미 채워둠)
            base = "https://bangpharmacy.blogspot.com/2026/07/"
            LINK_MAP = {
                "유산균 먹으면 좋은 점 총정리 - 효능, 부작용, 연령별·성별 고르는 법": base + "blog-post_04.html",
                "프로바이오틱스(유산균) 완전정리 - 효능, 부작용, 고르는 법": base + "blog-post_04.html",
                "연령별 프로바이오틱스 완전정리": base + "blog-post_675.html",
                "연령별 프로바이오틱스(유산균) 완전정리": base + "blog-post_675.html",
                "성별 프로바이오틱스 완전정리": base + "blog-post_350.html",
                "성별 프로바이오틱스(유산균) 완전정리": base + "blog-post_350.html",
                "키즈 유산균 브랜드별 CFU 함량·가격 비교": base + "cfu.html",
                "키즈 유산균 브랜드별 CFU·가격 비교": base + "cfu.html",
                "청소년(주니어) 유산균 비교": base + "blog-post_676.html",
                "청소년 유산균 추천": base + "blog-post_676.html",
                "성인 유산균 비교": base + "blog-post_447.html",
                "성인 유산균 고르는 법": base + "blog-post_447.html",
                "시니어 유산균 비교": base + "4060.html",
                "시니어(부모님) 유산균 추천": base + "4060.html",
                "임산부·수유부 유산균 비교": base + "blog-post_92.html",
                "임산부·수유부 유산균": base + "blog-post_92.html",
                "갱년기 여성 유산균 비교": base + "yt1.html",
                "갱년기 여성 유산균": base + "yt1.html",
                "여성 질건강 유산균 비교": base + "urex.html",
                "여성 질건강 유산균": base + "urex.html",
                "다이어트 유산균 비교": base + "bnr17-vs-hy7601ky1032.html",
                "남성 건강 유산균 비교": base + "blog-post_730.html",
                "남성 건강 유산균": base + "blog-post_730.html",
            }

            suffixes = [" (링크 삽입)", " (링크, 준비중)", " (링크)"]

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]
                original_content = content

                for phrase, url in LINK_MAP.items():
                    for suffix in suffixes:
                        target = phrase + suffix
                        if target in content:
                            replacement = f'<a href="{url}">{phrase}</a>'
                            content = content.replace(target, replacement)

                if content != original_content:
                    try:
                        execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                            body={"kind": "blogger#post", "title": title, "content": content, "labels": post.get("labels", [])}
                        ), log=self.log)
                        self.log(f"링크 연결 완료: {title}")
                    except Exception as e:
                        self.log(f"업데이트 실패: {title} / 오류: {e}")
                else:
                    self.log(f"변경 없음 (링크 대상 텍스트 없음): {title}")

            self.log("=== 관련 글 링크 자동 연결 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def list_posts(self):
        self.log("=== 전체 글 목록 조회 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, fetch_bodies=False, log=self.log)

            # 게시일 오래된 순으로 정렬 (먼저 쓴 글이 위로)
            posts.sort(key=lambda p: p.get("published", ""))

            self.log(f"전체 글 {len(posts)}개\n")
            lines = []
            for i, post in enumerate(posts, 1):
                title = post["title"]
                url = post["url"]
                line = f"{i}. {title}\n   {url}"
                self.log(line)
                lines.append(line)

            # 파일로도 저장
            with open("post_list.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.log("\npost_list.txt 파일로도 저장했습니다.")
            self.log("=== 전체 글 목록 조회 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def publish_posts(self):
        self.log("=== 새 글 발행 시작 ===")
        try:
            if not os.path.exists(POSTED_FOLDER):
                os.makedirs(POSTED_FOLDER)
            service = get_service()
            blog_id = get_blog_id(service)
            self.log(f"블로그 ID 확인 완료: {blog_id}")

            files = sorted(glob.glob(os.path.join(POSTS_FOLDER, "*.txt")))
            if not files:
                self.log("발행할 글이 posts 폴더에 없습니다.")
                return

            for i, filepath in enumerate(files):
                title, labels, body = parse_post_file(filepath)
                if not title or not body:
                    self.log(f"건너뜀 (형식 오류): {filepath}")
                    continue
                if i > 0:
                    self.log(f"({PUBLISH_DELAY_SECONDS}초 대기 중... 연속 발행으로 인한 스팸 차단 방지)")
                    time.sleep(PUBLISH_DELAY_SECONDS)
                try:
                    post_body = {
                        "kind": "blogger#post",
                        "title": title,
                        "content": body,
                        "labels": labels,
                    }
                    result = execute_with_retry(service.posts().insert(blogId=blog_id, body=post_body, isDraft=False), log=self.log)
                    url = result.get("url")
                    self.log(f"발행 완료: {title}\n  -> {url}")
                    shutil.move(filepath, os.path.join(POSTED_FOLDER, os.path.basename(filepath)))
                except Exception as e:
                    self.log(f"발행 실패: {title}\n  오류: {e}")
            self.log("=== 새 글 발행 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")

    def fix_disclosure(self):
        self.log("=== 쿠팡 문구 위치 수정 시작 ===")
        try:
            service = get_service()
            blog_id = get_blog_id(service)

            posts = fetch_all_posts(service, blog_id, log=self.log)

            self.log(f"전체 글 {len(posts)}개 확인됨")

            for post in posts:
                post_id = post["id"]
                title = post["title"]
                content = post["content"]

                if COUPANG_HIDDEN_OPEN in content:
                    self.log(f"건너뜀 (쿠팡 숨김 상태 — 심사 중에는 고지문구를 다시 추가하지 않음): {title}")
                    continue

                # 기존 쿠팡 고지 문구 패턴들을 찾아서 제거
                changed = False
                markers = [
                    "이 포스팅은 쿠팡 파트너스 활동의 일환으로",
                ]
                new_content = content
                for marker in markers:
                    if marker in new_content:
                        # <p>...marker...</p> 형태를 통째로 제거 시도
                        start = new_content.find("<p>", max(new_content.find(marker) - 10, 0))
                        end = new_content.find("</p>", new_content.find(marker))
                        if start != -1 and end != -1 and start < new_content.find(marker):
                            new_content = new_content[:start] + new_content[end + 4:]
                            changed = True
                        elif "<div" in new_content[:new_content.find(marker)][-200:]:
                            # 이미 div로 감싸진 경우는 건드리지 않음 (이미 처리됨으로 간주)
                            pass

                if changed:
                    new_content = new_content.strip() + "\n\n" + COUPANG_DISCLOSURE_SMALL
                    try:
                        execute_with_retry(service.posts().update(
                            blogId=blog_id, postId=post_id,
                            body={"kind": "blogger#post", "title": title, "content": new_content, "labels": post.get("labels", [])}
                        ), log=self.log)
                        self.log(f"수정 완료: {title}")
                    except Exception as e:
                        self.log(f"수정 실패: {title} / 오류: {e}")
                else:
                    self.log(f"건너뜀 (해당 없음 또는 이미 처리됨): {title}")

            self.log("=== 쿠팡 문구 위치 수정 종료 ===\n")
        except Exception as e:
            self.log(f"전체 오류: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
