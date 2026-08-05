# -*- coding: utf-8 -*-
# 정보 코너 — _posts/*.md → _preview/info.html(목록) + info_{slug}.html(글)
#  2026-07-24 통합지시서 §B1·B4.
#
#  왜 만들었나
#   ① 쇼츠·인스타 카드뉴스의 **상세 버전**을 수납할 곳이 없었다.
#      채널 분업: 쇼츠·인스타 = 훅 하나만 / 사이트 = 전체 + 자세한 설명 → "자세한 건 사이트에서"
#   ② "배달 즉시할인" 같은 검색어 유입
#   ③ 애드센스 "자동생성 비중" 리스크 희석 — 사람이 쓴 팩트 기반 글
#
#  🔴 게시판이 아니다. 글쓴이는 운영자뿐이라 댓글·로그인·서버가 필요 없다
#     → 나머지 페이지와 똑같이 **정적 생성**한다. theme.py 토큰·WRAP_CSS·P2_CSS를 그대로 쓴다.
#
#  글 소스: _posts/*.md  (front-matter + 본문)
#    ---
#    title: 제목
#    date: 2026-07-24
#    cat: 원가              # 배달앱 / 외식 구조 / 원가 / 재료 상식
#    summary: 한 줄 요약
#    shorts: 치킨 1편        # 연관 쇼츠·카드뉴스 (선택)
#    links:                 # 관련 내부링크 (선택) — "라벨|주소"
#      - 뿌링클 원가 보기|menu_12.html
#    ---
#    본문(마크다운 일부만 지원: ## 소제목 · **굵게** · 목록 · 문단)
import os, re, html, json, io
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE, clean_urls
from theme import (CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, SHARE_BTM, HEAD_TAGS,
                   FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_TOP, ADFIT_MID, ADFIT_CSS, SOURCES, SOURCES_CSS,
                   GNAV_CSS, gnav, WRAP_CSS, P2_CSS, BODY_CSS, TYPO_CSS)

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
SRC = os.path.join(BASE, "_posts")
OUT = os.path.join(BASE, "_preview")
os.makedirs(SRC, exist_ok=True)

def esc(s): return html.escape(str(s)) if s is not None else ""
def _clip(t, n=155):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n - 1] + "…"

# 갈래 — 칩 필터. 레시피 목록의 dchip과 같은 패턴.
CATS = ["배달앱", "외식 구조", "원가", "재료 상식"]

# ── front-matter 파서 ───────────────────────────────────────────
def parse(path):
    raw = io.open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        return None
    head, body = m.group(1), m.group(2)
    meta, key = {}, None
    for line in head.split("\n"):
        if re.match(r"^\s*-\s+", line) and key:          # 목록 항목
            meta.setdefault(key, []).append(line.strip()[1:].strip())
            continue
        mm = re.match(r"^(\w+):\s*(.*)$", line.strip())
        if mm:
            key, val = mm.group(1), mm.group(2).strip()
            meta[key] = val if val else []
    meta["body"] = body.strip()
    meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    return meta

# ── 최소 마크다운 → HTML ────────────────────────────────────────
#  글은 우리가 쓰는 것이라 문법을 다 지원할 필요가 없다. 쓰는 것만 변환한다.
def md(body):
    # 🔴 2026-07-24 추가 — **표**와 **이미지**를 지원한다.
    #    표: 기존 글 4편이 이미 마크다운 표를 쓰고 있었는데 변환기가 몰라서
    #        `| 기본 제공 | 소스 10종 |---|---|` 처럼 파이프가 그대로 노출됐다(실서비스에 그 상태로 나가 있었다).
    #    이미지: 쇼츠·카드뉴스 이미지를 글 안에 넣으려면 필요하다. 문법은 마크다운 그대로 `![캡션](주소)`.
    out, buf, in_ul, tbl = [], [], False, []
    def flush():
        if buf:
            out.append("<p>" + " ".join(buf) + "</p>")
            buf.clear()
    def closeul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>"); in_ul = False
    def closetbl():
        # 첫 줄 = 머리글, `|---|` 구분줄은 버린다
        if not tbl:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl]
        rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in r)]
        tbl.clear()
        if not rows:
            return
        head, body_rows = rows[0], rows[1:]
        h = "".join(f"<th>{_inline(c)}</th>" for c in head)
        b = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body_rows)
        out.append(f'<div class="ptabwrap"><table class="ptab"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
    for line in body.split("\n"):
        t = line.rstrip()
        if t.strip().startswith("|"):
            flush(); closeul()
            tbl.append(t.strip()); continue
        closetbl()
        if not t.strip():
            flush(); closeul(); continue
        if t.startswith("## "):
            flush(); closeul()
            out.append(f'<h2 class="psec">{esc(t[3:].strip())}</h2>'); continue
        m_img = re.match(r"^!\[(.*?)\]\((\S+?)\)\s*$", t.strip())
        if m_img:
            flush(); closeul()
            cap, src = m_img.group(1).strip(), m_img.group(2).strip()
            figcap = f'<figcaption>{esc(cap)}</figcaption>' if cap else ""
            out.append(f'<figure class="pfig"><img src="{esc(src)}" alt="{esc(cap)}" loading="lazy">{figcap}</figure>')
            continue
        if re.match(r"^\s*[-*]\s+", t):
            flush()
            if not in_ul:
                out.append("<ul class=\"plist2\">"); in_ul = True
            out.append("<li>" + _inline(re.sub(r"^\s*[-*]\s+", "", t)) + "</li>"); continue
        closeul()
        buf.append(_inline(t.strip()))
    closetbl(); flush(); closeul()
    return "".join(out)

def _inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t

STYLE = f"""<style>{CSS_VARS}
{FOOTER_CSS}{ADFIT_CSS}{SOURCES_CSS}{GNAV_CSS}
*{{box-sizing:border-box;margin:0;padding:0}}
{BODY_CSS}
{TYPO_CSS}
{WRAP_CSS}
{P2_CSS}
header.top{{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}}
.logo{{font-weight:800;font-size:18px;color:var(--ink);text-decoration:none}}
.logo small{{color:var(--muted);font-weight:500;font-size:12px;margin-left:8px;padding-left:8px;border-left:1px solid var(--line)}}
.crumb{{font-size:12px;color:var(--muted);padding:12px 0 0}}
.crumb a{{color:var(--muted);text-decoration:none}}
h1{{margin:8px 0 6px}}
.psub{{font-size:13px;color:var(--muted);margin-bottom:4px}}
.pchips{{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0 4px}}
.pchip2{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:7px 14px;
font-size:13px;font-weight:700;color:var(--muted);cursor:pointer;font-family:inherit}}
.pchip2.on{{background:var(--ink);color:var(--card);border-color:transparent}}
/* 목록 카드 */
.pcards{{display:flex;flex-direction:column;gap:10px;margin-top:14px}}
@media(min-width:840px){{.pcards{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}}}
.pcard2{{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:15px 16px;text-decoration:none;color:inherit}}
.pcard2:hover{{border-color:var(--accent)}}
.pcard2 .pc-cat{{font-size:11.5px;font-weight:800;color:var(--accent)}}
.pcard2 .pc-t{{font-size:15.5px;font-weight:800;margin:5px 0 4px;line-height:1.4}}
.pcard2 .pc-s{{font-size:13px;color:var(--muted);line-height:1.6}}
.pcard2 .pc-d{{font-size:12px;color:var(--faint);margin-top:7px}}
/* 글 본문 */
.pbody{{font-size:15px;line-height:1.85;margin-top:16px}}
.pbody p{{margin:0 0 14px}}
.pbody b{{font-weight:800}}
.psec{{font-size:17px;font-weight:800;margin:26px 0 10px;letter-spacing:-.01em}}
.plist2{{margin:0 0 14px 20px}} .plist2 li{{margin-bottom:6px}}
/* 표 — 좁은 폰에서 가로로만 스크롤되게 감싼다(본문이 통째로 밀리면 안 된다) */
.ptabwrap{{overflow-x:auto;margin:0 0 16px;-webkit-overflow-scrolling:touch}}
.ptab{{width:100%;border-collapse:collapse;font-size:14px;min-width:320px}}
.ptab th,.ptab td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;
vertical-align:top;line-height:1.6;white-space:nowrap}}
.ptab th{{font-weight:800;background:var(--panel);color:var(--muted);font-size:13px}}
.ptab td:first-child,.ptab th:first-child{{white-space:normal}}
.ptab tbody tr:last-child td{{border-bottom:0}}
/* 카드 묶음 — 글 맨 위에 3개씩 두 줄. 누르면 원본이 새 탭에서 열린다 */
.pgal{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:16px 0 4px}}
.pgcell{{display:block;line-height:0;border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.pgcell:hover{{border-color:var(--accent)}}
.pgcell img{{width:100%;height:auto;display:block}}
@media(min-width:840px){{.pgal{{gap:10px;max-width:560px}}}}
/* 본문 이미지 — 카드뉴스가 정사각이라 폭을 다 쓰면 너무 커진다. 460px에서 멈춘다 */
.pfig{{margin:0 0 18px}}
.pfig img{{display:block;width:100%;max-width:460px;margin:0 auto;height:auto;
border:1px solid var(--line);border-radius:14px}}
.pfig figcaption{{font-size:12.5px;color:var(--faint);text-align:center;margin-top:8px;line-height:1.6}}
/* 관련 내부링크 박스 */
.prel{{margin:22px 0 6px;padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:13px}}
.prel .prt{{font-size:13px;font-weight:800;margin-bottom:9px}}
.prel a{{display:flex;align-items:center;gap:8px;padding:9px 0;border-top:1px solid var(--line);
font-size:13.5px;font-weight:700;color:var(--ink);text-decoration:none}}
.prel a:first-of-type{{border-top:0}}
.prel a:hover{{color:var(--accent)}}
.prel a::after{{content:"›";margin-left:auto;color:var(--faint)}}
.pmeta{{font-size:12.5px;color:var(--faint);margin-top:4px}}
.disc{{margin:18px 0 4px;font-size:11.5px;color:var(--muted);line-height:1.6}}
</style>"""

def head(title, desc, path, here, jsonld=""):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<meta name="description" content="{esc(_clip(desc))}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(_clip(desc))}">
<meta property="og:type" content="article"><meta property="og:image" content="{SITE}/og/share.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/og/share.png">
<link rel="canonical" href="{SITE}/{path}">
{HEAD_TAGS}{HEAD_SCRIPT}{STYLE}{jsonld}</head>
<body><header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{SHARE_BTN}{BTN}{AUTH_BTN}{gnav(here)}</div></header>
<div class="wrap">"""

# 🔴 정보글은 광고가 **하단 1개뿐**이라 스크롤을 안 내리면 아예 안 보였다(2026-07-25).
#    본문 중간에 하나 더 넣는다. 두 개까지가 읽기 흐름을 안 깨는 선이다.
#    넣는 자리 우선순위: ① 첫 표 다음 ② 두 번째 소제목 앞 ③ 못 넣으면 그냥 둔다
def mid_ad(html):
    # 🔴 "두 번째 h2 앞"으로 잡았더니 상단 광고 바로 두 문단 뒤에 붙었다(2026-07-27 지적).
    #    글마다 소제목 간격이 달라서 **순서**로 자리를 잡으면 이렇게 몰린다.
    #    → **글 길이의 절반을 넘긴 뒤** 처음 나오는 자리에 넣는다. 짧은 글이면 아예 안 넣는다.
    if not ADFIT_MID:
        return html          # 중간 자리 광고단위가 없으면 넣지 않는다(중복 게재 금지)
    half = len(html) // 2
    if len(html) < 4000:
        return html          # 짧은 글에 두 개는 과하다 — 하단 하나로 충분하다
    for m in re.finditer(r"<h2", html):
        if m.start() > half:
            return html[:m.start()] + ADFIT_MID + html[m.start():]
    i = html.find("</table>", half)
    if i != -1:
        i += len("</table>")
        return html[:i] + ADFIT_MID + html[i:]
    i = html.find("</p>", half)
    if i != -1:
        i += len("</p>")
        return html[:i] + ADFIT_MID + html[i:]
    return html


FOOT = (ADFIT + SHARE_BTM
        + '<div class="disc">※ 글에 나오는 원가·시세는 공공데이터와 실거래 조사에 기반한 <b>추정치</b>입니다. '
          '실제 매장의 공급가와 다를 수 있습니다.</div>'
        + SOURCES + FOOTER_LINKS + '</div>' + TOGGLE_JS + '</body></html>')

# ── 글 읽기 ─────────────────────────────────────────────────────
posts = []
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith(".md"):
        continue
    p = parse(os.path.join(SRC, fn))
    if p and p.get("title"):
        posts.append(p)
# 🔴 새 글이 항상 맨 위로 온다(2026-07-25 지시).
#    날짜만으로 정렬하면 **같은 날 쓴 글끼리 순서가 안 잡힌다** — 실제로 6편이 전부
#    같은 날짜라 새 글이 중간에 파묻혔다. 날짜가 같으면 **파일 수정시각이 늦은 것**을 위로 올린다.
def _mtime(p):
    try:
        return os.path.getmtime(os.path.join(SRC, p["slug"] + ".md"))
    except OSError:
        return 0


posts.sort(key=lambda x: (str(x.get("date", "")), _mtime(x)), reverse=True)

# ── 글 페이지 ───────────────────────────────────────────────────
for p in posts:
    slug, title = p["slug"], p["title"]
    cat = p.get("cat", "원가")
    summ = p.get("summary", "")
    links = p.get("links") or []
    rel = ""
    if links:
        items = ""
        for L in links:
            if "|" in L:
                lab, href = L.split("|", 1)
                items += f'<a href="{esc(href.strip())}">{esc(lab.strip())}</a>'
        if items:
            rel = f'<div class="prel"><div class="prt">같이 보면 좋은 것</div>{items}</div>'
    # 🔴 카드 묶음(2026-07-24 지시) — 카드뉴스 이미지를 본문 중간에 흩지 않고
    #    **글 맨 위에 3개씩 작게** 모아 보여준다. 먼저 그림으로 훑고 본문으로 내려가는 흐름.
    #    front-matter: cards:  - /cards/anchor-0.jpg|캡션
    gal = ""
    cards = p.get("cards") or []
    if cards:
        cells = ""
        for c in cards:
            src, capt = (c.split("|", 1) + [""])[:2] if "|" in c else (c, "")
            cells += (f'<a class="pgcell" href="{esc(src.strip())}" target="_blank" rel="noopener">'
                      f'<img src="{esc(src.strip())}" alt="{esc(capt.strip())}" loading="lazy"></a>')
        gal = f'<div class="pgal">{cells}</div>'
    shorts = p.get("shorts", "")
    meta_line = f'<div class="pmeta">{esc(cat)} · {esc(p.get("date",""))}' + \
                (f' · 관련 영상 {esc(shorts)}' if shorts else '') + '</div>'
    # Article JSON-LD (지시서 §B1) — 신설 페이지는 SEO를 처음부터 갖춘다.
    ld = {"@context": "https://schema.org", "@type": "Article",
          "headline": title, "description": summ or _clip(re.sub(r"<[^>]+>", " ", md(p["body"]))),
          "datePublished": p.get("date", ""), "dateModified": p.get("date", ""),
          "author": {"@type": "Organization", "name": "올마나마", "url": SITE},
          "publisher": {"@type": "Organization", "name": "올마나마",
                        "logo": {"@type": "ImageObject", "url": f"{SITE}/apple-touch-icon.png"}},
          "image": [f"{SITE}/og/share.png"],
          "mainEntityOfPage": {"@type": "WebPage", "@id": f"{SITE}/info_{slug}.html"},
          "articleSection": cat, "inLanguage": "ko"}
    jsonld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>'
    body = (f'<div class="crumb"><a href="index.html">홈</a> › <a href="info.html">정보</a> › {esc(cat)}</div>'
            f'<h1>{esc(title)}</h1>'
            + (f'<p class="psub">{esc(summ)}</p>' if summ else '')
            + meta_line
            + ADFIT_TOP
            + gal
            + f'<div class="pbody">{mid_ad(md(p["body"]))}</div>'
            + rel)
    io.open(os.path.join(OUT, f"info_{slug}.html"), "w", encoding="utf-8").write(
        clean_urls(head(f"{title} · 올마나마", summ or title, f"info_{slug}.html", "info", jsonld)
                   + body + FOOT))

# ── 목록 페이지 ─────────────────────────────────────────────────
#  §B4: 마라탕 단가표를 '원가' 갈래에 항목으로 노출한다.
#   🔴 URL은 /malatang-price 그대로 — 색인·공유 링크가 이미 걸려 있어 절대 안 바꾼다.
EXTRA = [{"cat": "원가", "title": "마라탕 셀프바 재료 62종 단가표",
          "summary": "마라탕 셀프바에 들어가는 재료 62종의 100g당 원가. 실거래가 기준.",
          "date": "2026-07-23", "href": "malatang-price.html"}]

cards = ""
for it in EXTRA + [{"cat": p.get("cat", "원가"), "title": p["title"],
                    "summary": p.get("summary", ""), "date": p.get("date", ""),
                    "href": f'info_{p["slug"]}.html'} for p in posts]:
    cards += (f'<a class="pcard2" href="{esc(it["href"])}" data-c="{esc(it["cat"])}">'
              f'<div class="pc-cat">{esc(it["cat"])}</div>'
              f'<div class="pc-t">{esc(it["title"])}</div>'
              + (f'<div class="pc-s">{esc(_clip(it["summary"], 90))}</div>' if it["summary"] else '')
              + f'<div class="pc-d">{esc(it["date"])}</div></a>')

chips = '<button class="pchip2 on" data-c="전체">전체</button>' + "".join(
    f'<button class="pchip2" data-c="{esc(c)}">{esc(c)}</button>' for c in CATS)
chips_js = """<script>
document.querySelector('.pchips').addEventListener('click',function(e){
  var b=e.target.closest('.pchip2'); if(!b)return;
  document.querySelectorAll('.pchip2').forEach(function(x){x.classList.remove('on')});
  b.classList.add('on');
  var c=b.dataset.c;
  document.querySelectorAll('.pcard2').forEach(function(k){
    k.style.display=(c==='전체'||k.dataset.c===c)?'':'none';});
});
</script>"""

# 🔴 «원가율이란?» 설명은 **여기 정보 코너에 둔다**(2026-07-31 대표 지시).
#    전엔 홈 우측에 붙어 있었는데, 홈이 «메뉴판» 중심으로 바뀌면서 자리가 안 맞았다.
#    원가 이야기를 보러 온 사람이 읽는 자리가 맞다.
COST_BOX = ('<div class="costwhat"><div class="t">원가율이란?</div>'
            '<div class="d">판매가 대비 <b>재료비(도매 추정)</b> 비중입니다. '
            '임대료·인건비·배달수수료·본사 로열티는 <b>포함되지 않아요</b> — '
            '나머지에서 그 비용을 내고 마진이 남습니다.</div></div>')
COST_CSS = ("""<style>.costwhat{background:var(--card);border:1px solid var(--line);
border-radius:14px;padding:14px 16px;margin:14px 0 18px}
.costwhat .t{font-weight:800;font-size:14.5px;margin-bottom:6px}
.costwhat .d{font-size:13.5px;line-height:1.65;color:var(--muted)}
.costwhat b{color:var(--accent);font-weight:800}</style>""")

n = len(posts) + len(EXTRA)
list_body = (f'{COST_CSS}<div class="crumb"><a href="index.html">홈</a> › 정보</div>'
             f'<h1>프랜차이즈 원가 이야기</h1>'
             f'<p class="psub">배달앱·외식 구조·원가에 대해 현장에서 확인한 것들을 정리합니다. 전체 {n}개</p>'
             f'{COST_BOX}'
             f'<div class="pchips">{chips}</div>'
             f'<div class="pcards">{cards}</div>')
io.open(os.path.join(OUT, "info.html"), "w", encoding="utf-8").write(
    clean_urls(head("프랜차이즈 원가 이야기 · 배달앱 수수료 · 외식 물가",
                    "치킨·피자·떡볶이 프랜차이즈 메뉴의 재료비를 뜯어보고, 배달앱 수수료와 외식 물가 구조를 "
                    "현장에서 확인한 숫자로 정리합니다.",
                    "info.html", "info")
               + list_body + FOOT.replace(TOGGLE_JS, TOGGLE_JS + chips_js)))

print(f"정보 코너: info.html + 글 {len(posts)}개 (목록 항목 {n}개)")
