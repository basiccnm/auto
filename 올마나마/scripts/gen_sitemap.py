# -*- coding: utf-8 -*-
# sitemap.xml + robots.txt 생성 (2026-07-17)
#  ★ 이 사이트의 자산은 검색 노출인데 sitemap도 robots도 없었다 = 구글이 489개 페이지를 알 방법이 없다.
#  ★ meta description도 489개 중 488개가 비어 있었다(검색결과 스니펫이 안 나옴) → 각 생성기에서 채우도록 수정함.
#  배포 도메인이 확정되면 SITE만 바꾸면 된다. 각 생성기의 SITE 상수도 같이 맞출 것.
#  사용법: python scripts/gen_sitemap.py   (다른 생성기들 다음에 마지막으로)
import os, glob, sqlite3
from datetime import datetime, timezone

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
OUT = os.path.join(BASE, "_preview")
# 배포 주소는 site_config.py 한 곳에서만 관리(= wrangler.toml의 SITE_ORIGIN)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE


# 우선순위: 홈 > 카테고리/사전 허브 > 브랜드/요리 > 메뉴
def priority(fn):
    if fn == "index.html": return "1.0", "daily"
    if fn in ("categories.html", "dishes.html", "prices.html", "malatang-price.html", "info.html"): return "0.9", "daily"
    if fn.startswith("info_"): return "0.8", "monthly"   # 정보 글 (2026-07-24 §B1)
    # 재료별 시세 페이지 — 매일 값이 바뀌므로 daily (2026-07-24 신설)
    if fn.startswith("price_"): return "0.7", "daily"
    if fn.startswith("cat_"): return "0.8", "weekly"
    if fn.startswith("dish_"): return "0.8", "weekly"
    if fn.startswith("brand_"): return "0.7", "weekly"
    return "0.6", "weekly"   # menu_*

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
# 검수용(_로 시작)은 발행 대상이 아니다 → sitemap에도 robots에도 넣지 않는다.
# 회원 전용 화면(2026-07-27)도 뺀다 — 개인별 내용이라 색인 대상이 아니고,
# 페이지 자체에도 <meta name="robots" content="noindex">가 들어 있다(gen_auth_pages.py).
NOINDEX = {"login.html", "mypage.html", "charge.html"}
pages = sorted(os.path.basename(f) for f in glob.glob(os.path.join(OUT, "*.html"))
               if not os.path.basename(f).startswith("_")
               and os.path.basename(f) not in NOINDEX)

urls = ""
for fn in pages:
    pr, cf = priority(fn)
    # 정식 URL = 확장자 없는 주소 (2026-07-19). .html은 307 리다이렉트라 sitemap에 넣으면 안 된다.
    loc = f"{SITE}/" if fn == "index.html" else f"{SITE}/{fn[:-5]}"
    urls += (f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n'
             f'    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>\n')

sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemap.org/schemas/sitemap/0.9">\n'.replace("sitemap.org", "sitemaps.org")
           + urls + "</urlset>\n")
open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(sitemap)

# 🔴 색인 스위치 — 2026-07-19 오픈 (URL 통일·도메인·법적 페이지 완료 후).
#    닫아야 하면 False 로 바꾸고 gen_sitemap → build_dist → deploy.
INDEXABLE = True

if INDEXABLE:
    robots = f"""User-agent: *
Allow: /

# 검수용 페이지는 색인 제외 (_logo_audit, _menu_audit 등 내부 확인용)
Disallow: /_

Sitemap: {SITE}/sitemap.xml
"""
else:
    robots = """User-agent: *
Disallow: /
"""
open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(robots)

# ads.txt — 애드센스 판매자 확인 파일 (2026-07-19). 없으면 승인·수익에 불이익.
open(os.path.join(OUT, "ads.txt"), "w", encoding="utf-8").write(
    "google.com, pub-9423286569078244, DIRECT, f08c47fec0942fa0\n")

db = sqlite3.connect(os.path.join(BASE, "data", "eolmanama.db"))
print(f"sitemap.xml: {len(pages)}개 URL")
for pfx, label in (("menu_", "메뉴"), ("brand_", "브랜드"), ("cat_", "카테고리"), ("dish_", "요리")):
    print(f"   {label}: {sum(1 for p in pages if p.startswith(pfx))}개")
print(f"   기타(홈·허브): {sum(1 for p in pages if not any(p.startswith(x) for x in ('menu_','brand_','cat_','dish_')))}개")
print(f"robots.txt: 검수용 /_ 차단 · sitemap 링크")
print(f"\n⚠️ 배포 도메인 확정 시 SITE 상수를 gen_sitemap.py · gen_preview_html.py · gen_dishes.py · gen_prices_page.py 4곳에서 함께 바꿀 것")
