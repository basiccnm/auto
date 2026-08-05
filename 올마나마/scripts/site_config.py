# -*- coding: utf-8 -*-
# 사이트 공통 설정 — **배포 주소는 여기 한 곳에서만 관리한다** (2026-07-17)
#
# 🔴 왜 만들었나: SITE 상수를 생성기 4곳에 각각 박아놨더니 바로 사고가 났다.
#    wrangler.toml에는 실제 주소(eolmanama-site-renderer.dndmotor1.workers.dev)가 이미 있는데
#    생성기들에는 **존재하지도 않는 주소**(eolmanama.workers.dev)를 박아, canonical·sitemap 488개가
#    전부 틀린 도메인을 가리키고 있었다. 4곳을 손으로 맞추는 구조면 또 벌어진다.
#
# 도메인이 바뀌면 **이 파일만** 고치면 된다. wrangler.toml의 SITE_ORIGIN도 같이 맞출 것.
import os, re

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
_TOML = os.path.join(BASE, "workers", "site-renderer", "wrangler.toml")

def _from_wrangler():
    """wrangler.toml의 SITE_ORIGIN을 단일 출처로 삼는다. 배포 설정과 생성 HTML이 어긋나지 않게."""
    try:
        m = re.search(r'SITE_ORIGIN\s*=\s*"([^"]+)"', open(_TOML, encoding="utf-8").read())
        if m: return m.group(1).rstrip("/")
    except Exception:
        pass
    return None

SITE = _from_wrangler() or "https://eolmanama-site-renderer.dndmotor1.workers.dev"

def canon(path):
    return f"{SITE}/{path.lstrip('/')}"


# ── 재료 종수 — **단일 출처** (2026-07-24) ────────────────────────────
#  🔴 왜 만들었나: 같은 "재료 N종"이 페이지마다 다른 값으로 나가고 있었다.
#       about.html   280여 종  ← 하드코딩(근거 없음)
#       prices.html  352종     ← len(DATA)  (메뉴사용 or 참가격키 or live)
#       index.html   261종     ← price_kinds (menu_ingredients JOIN + manual_price>0 or live)
#     세는 쿼리가 세 곳에 따로 있었고 하나는 사람이 손으로 적은 숫자였다.
#     SITE 상수·CSS 폭에서 이미 겪은 "같은 값 두 곳 = 어긋남"의 반복이라 여기로 모은다.
#
#  기준: **시세 페이지(prices.html)에 실제로 실리는 재료 수**를 정본으로 삼는다.
#        그 페이지가 사용자가 눈으로 세어볼 수 있는 유일한 화면이기 때문이다.
#        → gen_prices_page.py의 DATA 필터와 같은 조건을 쓴다.
#          (메뉴에 실제 쓰임 OR 참가격 연동 OR 공공데이터 live) AND 표시할 가격이 있음
#          AND live_composite(실제로 살 수 없는 가중평균 지수)는 제외
_KINDS_SQL = """
SELECT COUNT(*) FROM (
  SELECT i.ingredient_key
  FROM ingredients i LEFT JOIN menu_ingredients mi ON mi.ingredient_key = i.ingredient_key
  WHERE i.type != 'live_composite'
    AND (i.manual_price > 0
         OR i.type = 'live'
         OR EXISTS (SELECT 1 FROM price_history ph
                    WHERE ph.ingredient_key = i.ingredient_key AND ph.retail_price > 0))
  GROUP BY i.ingredient_key
  HAVING COUNT(DISTINCT mi.menu_id) > 0
      OR i.chamgagyeok_key IS NOT NULL
      OR i.type = 'live'
)"""

def ingredient_kinds(cur):
    """시세 페이지에 실리는 재료 종수. 화면에 'N종'을 쓰는 곳은 전부 이 함수를 쓸 것."""
    return cur.execute(_KINDS_SQL).fetchone()[0]


# ── 정식 URL = 확장자 없는 주소 (2026-07-19) ─────────────────────────
#  왜: Cloudflare Assets(auto-trailing-slash)가 /menu_6.html 을 /menu_6 으로 **307 리다이렉트**한다.
#      canonical·sitemap이 .html 을 가리키면 구글봇이 '리다이렉트되는 canonical'을 보게 돼 색인이 지저분해진다.
#      실주소(/menu_6, 홈 /)로 통일하면 리다이렉트 0. 파일명은 menu_6.html 그대로(주소만 바뀜).
#  적용: 각 생성기가 페이지 HTML을 쓰기 직전에 clean_urls()를 통과시킨다.
# ⚠️ 한글 파일명(price_양파.html)도 처리해야 한다 — 영숫자만 잡으면 재료 페이지의
#    .html이 그대로 남아 307 리다이렉트를 타고, 링크 검사에서 624건이 걸린다(2026-07-24).
_HREF = re.compile(r'href="([^"/:?#]+)\.html(#[^"]*)?"')

def clean_urls(html):
    # 1) 홈 링크 → /
    html = html.replace('href="index.html"', 'href="/"')
    html = html.replace(f'{SITE}/index.html', f'{SITE}/')
    # 2) canonical 등 절대 URL의 .html 제거
    html = re.sub(re.escape(SITE) + r'/([A-Za-z0-9_\-]+)\.html', SITE + r'/\1', html)
    # 3) 정적 내부 링크의 .html 제거 (#앵커 보존)
    html = _HREF.sub(lambda m: f'href="{m.group(1)}{m.group(2) or ""}"', html)
    # 4) JS 링크 빌더('menu_'+id+'.html">') — 정적 링크를 먼저 처리했으므로 남은 .html">는 JS 문자열뿐
    html = html.replace('.html">', '">')
    return html

if __name__ == "__main__":
    print("SITE =", SITE)
    print("출처 =", "wrangler.toml" if _from_wrangler() else "폴백 상수")
    print("예시 =", canon("menu_6.html"))
