# -*- coding: utf-8 -*-
"""받아둔 홈페이지 텍스트로 **브랜드별 메뉴 ↔ 우리 DB** 대조표를 만든다. 2026-07-26

🔴 왜 이걸 먼저 하나 (대표 지적)
   *"너가 브랜드랑 메뉴를 알아야 할거 아니야 그래야 할수 있다고"*
   양념을 쪼개든 기성품을 붙이든, **그 브랜드가 무슨 메뉴를 파는지**부터 알아야 한다.
   큰맘할매순대국 한 곳만 봐도 공식 17개 중 우리 DB에 7개뿐이었다.

새로 긁지 않는다 — `scripts/brand_site_crawl.py` 가 저장한 `data/brand_pages/*.txt` 를 읽는다.

판정은 두 갈래만 한다(자동 추측 금지)
  ① 우리 DB 메뉴가 홈페이지 텍스트에 **있나/없나**
  ② 홈페이지에 있는데 DB에 없는 **메뉴 후보** — 사람이 보고 고른다

    python scripts/brand_menu_compare.py
"""
import io
import json
import os
import re
import sqlite3
import html
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
# 🔴 렌더링본을 읽는다(2026-07-26). urllib 원문(brand_pages)은 JS 메뉴가 빠져 있어
#    "홈페이지에 내용 없음"이라는 오보를 만들었다. 정본은 brand_pages_rendered 다.
PAGES = os.path.join(BASE, "data", "brand_pages_rendered")
SIGJSON = os.path.join(BASE, "data", "research", "brand_render_signals.json")
OUT = os.path.join(BASE, "data", "research", "brand_menu_compare.html")

# 메뉴 후보로 볼 낱말 — 음식 이름에 흔히 붙는 말
FOODWORD = ("치킨", "피자", "버거", "떡볶이", "김밥", "국밥", "덮밥", "돈까스", "라면", "우동",
            "국수", "쌀국수", "짜장", "짬뽕", "탕수육", "마라탕", "마라샹궈", "곱창", "막창",
            "족발", "보쌈", "순대", "찌개", "전골", "구이", "볶음", "튀김", "샐러드", "포케",
            "커피", "라떼", "아메리카노", "스무디", "빙수", "와플", "핫도그", "초밥", "회",
            "설렁탕", "육개장", "해장국", "갈비", "삼겹", "제육", "불고기", "닭갈비", "강정",
            "도시락", "정식", "반상", "한상", "세트", "콤보", "만두", "튀김", "샌드위치",
            "브레드", "케이크", "도넛", "빵", "스테이크", "파스타", "리조또", "냉면", "메밀")
BADWORD = ("로그인", "회원", "쿠키", "개인정보", "이용약관", "고객센터", "가맹", "채용", "공지",
           "이벤트", "다운로드", "바로가기", "더보기", "사업자", "대표이사", "주소", "전화",
           "copyright", "all rights", "메뉴보기", "전체메뉴", "홈으로")


def norm(s):
    return re.sub(r"[\s·,\-_.()\[\]/]+", "", s or "").lower()


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    brands = [dict(r) for r in c.execute("""
        SELECT b.id, b.name, b.slug, b.published, b.homepage_url u
        FROM brands b WHERE (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) DESC""")]
    dbmenus = defaultdict(list)
    for r in c.execute("SELECT brand_id, id, name, sell_price FROM menus ORDER BY sort_order"):
        dbmenus[r["brand_id"]].append(dict(r))

    sig = {}
    if os.path.exists(SIGJSON):
        for x in json.load(io.open(SIGJSON, encoding="utf-8")):
            sig[x["brand"]] = x

    rows = []
    for b in brands:
        fp = os.path.join(PAGES, "%s.txt" % (b["slug"] or b["name"]))
        text = io.open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""
        flat = norm(text)
        found, missing = [], []
        for m in dbmenus[b["id"]]:
            (found if norm(m["name"]) in flat else missing).append(m)
        # 홈페이지에 있는데 DB에 없는 메뉴 후보
        dbset = {norm(m["name"]) for m in dbmenus[b["id"]]}
        cand, seen = [], set()
        for line in text.split("\n"):
            t = line.strip()
            if not (2 <= len(t) <= 24):
                continue
            low = t.lower()
            if any(w in low for w in BADWORD):
                continue
            if not any(w in t for w in FOODWORD):
                continue
            n = norm(t)
            if n in dbset or n in seen:
                continue
            seen.add(n)
            cand.append(t)
        rows.append({"b": b, "found": found, "missing": missing,
                     "cand": cand[:30], "chars": len(text),
                     "sig": (sig.get(b["name"]) or {}).get("signals") or {}})

    # ── 콘솔 요약 ─────────────────────────────────────────
    print("브랜드 %d곳" % len(rows))
    print()
    print("%-16s %4s %4s %4s %5s %6s %s" % ("브랜드", "DB", "확인", "못찾", "후보", "본문", "공급신호"))
    print("-" * 92)
    for r in rows:
        s = " ".join("%s%d" % (k, len(v)) for k, v in r["sig"].items()) or "-"
        print("%-16s %3d %4d %4d %5d %6d %s" % (
            r["b"]["name"][:16], len(r["found"]) + len(r["missing"]),
            len(r["found"]), len(r["missing"]), len(r["cand"]), r["chars"], s))

    # ── 화면 ─────────────────────────────────────────────
    CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#6f6f6f;--line:#e6e6e6;--card:#fafafa;--ok:#1e7a4d;--no:#c0392b;--new:#0f5f7a}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eaeaea;--mut:#9a9a9a;--line:#2c2c2c;--card:#1c1c1c;--ok:#4cc38a;--no:#e57368;--new:#5bb8d4}}
:root[data-theme=dark]{--bg:#141414;--fg:#eaeaea;--mut:#9a9a9a;--line:#2c2c2c;--card:#1c1c1c;--ok:#4cc38a;--no:#e57368;--new:#5bb8d4}
:root[data-theme=light]{--bg:#fff;--fg:#1a1a1a;--mut:#6f6f6f;--line:#e6e6e6;--card:#fafafa;--ok:#1e7a4d;--no:#c0392b;--new:#0f5f7a}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,'Malgun Gothic',sans-serif;margin:0;padding:16px}
h1{font-size:19px;margin:0 0 3px}.sub{color:var(--mut);font-size:12.5px;margin-bottom:14px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.tab{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:15px;padding:5px 12px;font-size:12.5px;cursor:pointer}
.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.g{border:1px solid var(--line);border-radius:9px;padding:11px 13px;margin-bottom:11px;background:var(--card)}
.g h2{font-size:15px;margin:0 0 4px}
.g h2 small{font-weight:400;color:var(--mut);font-size:12px;margin-left:6px}
.sg{font-size:12.5px;border-left:3px solid var(--ok);padding:3px 9px;margin:6px 0;background:var(--bg)}
.sg b{color:var(--ok)}
.rw{font-size:12.5px;margin-top:6px}
.rw .lb{color:var(--mut);font-size:11.5px;display:block}
.chip{display:inline-block;border:1px solid var(--line);border-radius:4px;padding:1px 6px;margin:2px 3px 0 0;font-size:12px;background:var(--bg)}
.chip.no{border-color:var(--no);color:var(--no)}
.chip.new{border-color:var(--new);color:var(--new)}
.warn{color:var(--no);font-weight:600}
"""
    out = [u'<title>브랜드 메뉴 대조표</title><style>%s</style>' % CSS]
    out.append(u'<h1>브랜드별 메뉴 ↔ 우리 DB 대조</h1>')
    out.append(u'<div class=sub>홈페이지에서 받은 텍스트로 맞춰봤습니다 · 2026-07-26 · '
               u'<b>못찾음</b>=DB에 있는데 홈페이지에서 확인 안 됨 · <b>후보</b>=홈페이지에 있는데 DB에 없음</div>')
    out.append(u'<div class=tabs><button class="tab on" data-f=all>전체</button>'
               u'<button class=tab data-f=sig>공급신호 있음</button>'
               u'<button class=tab data-f=miss>못찾음 많음</button>'
               u'<button class=tab data-f=thin>본문 없음</button></div>')
    for r in rows:
        b = r["b"]
        fl = []
        if r["sig"]:
            fl.append("sig")
        if len(r["missing"]) > len(r["found"]):
            fl.append("miss")
        if r["chars"] < 2000:
            fl.append("thin")
        out.append(u'<div class=g data-f="%s"><h2>%s <small>· DB %d개 · 확인 %d · 못찾음 %d%s</small></h2>' % (
            " ".join(fl), html.escape(b["name"]), len(r["found"]) + len(r["missing"]),
            len(r["found"]), len(r["missing"]),
            " · <span class=warn>홈페이지 내용 거의 없음</span>" if r["chars"] < 2000 else ""))
        for kind, hs in r["sig"].items():
            for h in hs:
                out.append(u'<div class=sg><b>%s</b> — %s</div>' % (kind, html.escape(h["line"])))
        if r["found"]:
            out.append(u'<div class=rw><span class=lb>홈페이지에서 확인된 DB 메뉴</span>%s</div>' %
                       "".join('<span class=chip>%s</span>' % html.escape(m["name"]) for m in r["found"]))
        if r["missing"]:
            out.append(u'<div class=rw><span class=lb>DB에 있는데 홈페이지에서 못 찾음</span>%s</div>' %
                       "".join('<span class="chip no">%s</span>' % html.escape(m["name"]) for m in r["missing"]))
        if r["cand"]:
            out.append(u'<div class=rw><span class=lb>홈페이지에 있는데 DB에 없는 메뉴 후보</span>%s</div>' %
                       "".join('<span class="chip new">%s</span>' % html.escape(t) for t in r["cand"]))
        out.append(u'</div>')
    out.append(u'<script>var G=[].slice.call(document.querySelectorAll(".g")),'
               u'B=[].slice.call(document.querySelectorAll(".tab"));'
               u'B.forEach(function(b){b.onclick=function(){B.forEach(function(x){x.classList.remove("on")});'
               u'b.classList.add("on");var f=b.dataset.f;G.forEach(function(g){'
               u'g.style.display=(f=="all"||g.dataset.f.indexOf(f)>=0)?"":"none"})}})</script>')
    io.open(OUT, "w", encoding="utf-8").write(u"".join(out))
    print()
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
