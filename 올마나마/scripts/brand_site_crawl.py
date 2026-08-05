# -*- coding: utf-8 -*-
"""브랜드 공식 홈페이지를 긁어 **공급 방식(완제품/반제품/원물)과 공식 메뉴**를 모은다. 2026-07-26

왜 이걸 먼저 하나 — 사장이 알아야 하는 건 "이 메뉴를 완제품으로 받는가"이고,
그 답을 **본사가 자기 홈페이지에 직접 써놓는다.**
  큰맘할매순대국: "순대국 업계 최초 **전제품 완조리 공급 시스템** 구축"  ← 이 한 줄이면 판별 끝
정보공개서에는 식재료가 아예 없다(2026-07-26 확인: 무공돈까스 본문 109만자에 '등심' 0회).

하는 일
  ① 홈페이지를 받아 텍스트로 저장 (data/brand_pages/<slug>.txt)
  ② 같은 도메인에서 메뉴·브랜드·물류 관련 링크를 최대 4개 더 따라간다
  ③ 공급방식 낱말을 세어 신호를 남긴다 — 판정은 사람이 한다(자동 판정 금지)

⚠️ 판정을 코드가 내리지 않는다. 낱말이 나온 **문장을 그대로** 남겨서 근거로 쓴다.
   근거 없이 "완제품이다"라고 쓰면 안 된다.

    python scripts/brand_site_crawl.py            # 전체
    python scripts/brand_site_crawl.py --only 큰맘 # 이름에 그 말이 든 브랜드만
"""
import io
import json
import os
import re
import socket
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "brand_pages")
REPORT = os.path.join(BASE, "data", "research", "brand_supply_signals.json")
SLEEP = 0.4
TIMEOUT = 12
socket.setdefaulttimeout(TIMEOUT)
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 공급 방식 신호 — 어느 쪽 낱말이 나오는지만 센다
SIG = {
    "완제품": ("완조리", "완제품", "완전조리", "조리완료", "데우", "원팩", "일품요리",
             "레토르트", "간편조리", "조리 없이"),
    "반제품": ("반조리", "반제품", "소스 공급", "양념 공급", "1차 가공", "전처리",
             "손질 완료", "밀키트"),
    "원물": ("매장에서 직접", "매일 손질", "직접 손질", "당일 조리", "수제", "생면",
            "매일 아침", "국내산 원육", "직접 반죽"),
    "물류": ("물류센터", "자체공장", "생산공장", "제조시설", "HACCP", "직배송",
            "물류시스템", "물류 시스템", "중앙집중", "센트럴키친", "센트럴 키친"),
}
LINKWORD = ("메뉴", "menu", "brand", "브랜드", "물류", "system", "시스템",
            "franchise", "가맹", "about", "company", "회사", "제조", "공장")
JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>")


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    r = urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX)
    raw = r.read(3_000_000)
    if raw[:2] == b"\x1f\x8b":
        import gzip
        raw = gzip.decompress(raw)
    ct = r.headers.get("Content-Type") or ""
    enc = "utf-8"
    m = re.search(r"charset=([\w-]+)", ct, re.I)
    if m:
        enc = m.group(1)
    else:
        m2 = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000], re.I)
        if m2:
            enc = m2.group(1).decode("ascii", "ignore")
    return raw.decode(enc, "replace"), r.geturl()


def to_text(html_s):
    s = JUNK_TAG.sub(" ", html_s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


# 🔴 링크만 따라가면 놓친다(2026-07-26): 큰맘할매순대국의 "전제품 완조리 공급 시스템" 한 줄은
#    /html/brand.html 에 있는데 메인의 <a> 3개에는 없었다. 그래서 흔한 경로를 같이 시도한다.
GUESS_PATHS = ("html/brand.html", "html/menu.html", "menu.html", "menu", "brand.html",
               "brand", "sub/menu.html", "company.html", "system.html")


def links(html_s, base_url):
    out, seen = [], set()
    host = urllib.parse.urlparse(base_url).netloc
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_s):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        u = urllib.parse.urljoin(base_url, href)
        if urllib.parse.urlparse(u).netloc != host:
            continue
        if u in seen:
            continue
        blob = (href + " " + label).lower()
        if any(w.lower() in blob for w in LINKWORD):
            seen.add(u)
            out.append(u)
    # 메뉴·브랜드 쪽을 앞으로 (신호가 거기 있다)
    out.sort(key=lambda u: 0 if re.search(r"(menu|brand|메뉴|브랜드)", u, re.I) else 1)
    for p in GUESS_PATHS:
        u = urllib.parse.urljoin(base_url, p)
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:9]


def scan(text):
    """신호 낱말이 든 문장을 그대로 남긴다."""
    hits = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for kind, words in SIG.items():
        for w in words:
            for l in lines:
                if w in l and 6 <= len(l) <= 220:
                    hits.setdefault(kind, []).append({"word": w, "line": l})
                    break
    return hits


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    os.makedirs(OUT, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.name, b.slug, b.homepage_url u, b.published p,
               (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) n
        FROM brands b WHERE (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY n DESC""")]
    if only:
        rows = [r for r in rows if only in r["name"]]
    print("브랜드 %d개 홈페이지 수집 시작" % len(rows), flush=True)
    print("", flush=True)

    res = []
    ok = dead = 0
    for i, b in enumerate(rows, 1):
        rec = {"brand": b["name"], "slug": b["slug"], "url": b["u"],
               "menus": b["n"], "published": b["p"], "pages": [], "signals": {}, "error": None}
        try:
            html_s, real = fetch(b["u"])
        except Exception as e:
            rec["error"] = str(e)[:90]
            dead += 1
            print("  %3d/%d  ✗ %-16s %s" % (i, len(rows), b["name"][:16], rec["error"]), flush=True)
            res.append(rec)
            time.sleep(SLEEP)
            continue
        texts = [to_text(html_s)]
        rec["pages"].append(real)
        for u2 in links(html_s, real):
            try:
                h2, r2 = fetch(u2)
                texts.append(to_text(h2))
                rec["pages"].append(r2)
            except Exception:
                pass
            time.sleep(SLEEP)
        allt = "\n".join(texts)
        io.open(os.path.join(OUT, "%s.txt" % (b["slug"] or b["name"])), "w",
                encoding="utf-8").write(allt)
        rec["chars"] = len(allt)
        rec["signals"] = scan(allt)
        ok += 1
        tag = " ".join("%s%d" % (k, len(v)) for k, v in rec["signals"].items()) or "신호없음"
        print("  %3d/%d  ✓ %-16s %6d자  %-2d쪽  %s" % (
            i, len(rows), b["name"][:16], rec["chars"], len(rec["pages"]), tag), flush=True)
        res.append(rec)
        time.sleep(SLEEP)

    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("", flush=True)
    print("끝. 열림 %d개 · 실패 %d개 → %s" % (ok, dead, REPORT), flush=True)


if __name__ == "__main__":
    main()
