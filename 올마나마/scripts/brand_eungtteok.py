# -*- coding: utf-8 -*-
"""응급실국물떡볶이 메뉴 수집 — 공식 홈페이지(그누보드). 2026-07-31 새로 씀

    python scripts/brand_eungtteok.py

🔴 **공식 주소는 한글 도메인이다.**
    http://xn--3e0boln8q87fglcewot4hgi.kr   (= 응급실국물떡볶이.kr)

   ⚠️ 이 파일의 옛 버전은 DB 에 적혀 있던 `eungtteok.grp.kr` 만 보고
      «판매용(parked) 도메인 — 브랜드 사이트 없음» 으로 결론 내고 끝냈다.
      그 판단이 **틀렸다.** 도메인이 만료돼 GoDaddy 판매 페이지로 넘어갔을 뿐,
      브랜드는 한글 도메인으로 멀쩡히 살아 있었다(2026-07-31 확인).
      → **주소가 죽었으면 «사이트가 없다» 가 아니라 «주소가 바뀌었나» 를 먼저 본다.**

경로 (화면 링크에서 그대로 읽은 것. 추측 아님)
    /bbs/board.php?bo_table=tteok_menu&sca={분류}
    분류: 메인메뉴 · 밥메뉴 · 사이드메뉴 · 튀김메뉴

DOM: 이름이 «한우대창로제 떡볶이 / (2-3인분)» 두 줄로 온다.
     인분은 이름에서 떼어 `compose_raw` 로 옮긴다 — 메뉴명에 규격을 붙이면 검색이 안 걸린다.
🔴 **가격이 없다.** 공식은 이름만 싣는다 → 가격은 뒤 단계에서.

결과: data/brand_menu_list/eungtteok.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
ROOT = "http://xn--3e0boln8q87fglcewot4hgi.kr"
CATS = ["메인메뉴", "밥메뉴", "사이드메뉴", "튀김메뉴"]
GAP = 1.1
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

# 🔴 실제 마크업 (2026-07-31 확인) — 이름이 span 으로 **쪼개져** 있다:
#    <div class="title"><span class="red">한우대창로제</span> 떡볶이 <span class="inbun">(2-3인분)</span></div>
#    그래서 «줄 단위» 로 읽으면 이름이 조각나거나 아예 안 잡힌다. div.title 을 통째로 읽는다.
RX_TITLE = re.compile(r'<div[^>]*class="title"[^>]*>(.*?)</div>', re.S | re.I)
RX_INBUN = re.compile(r'<span[^>]*class="inbun"[^>]*>(.*?)</span>', re.S | re.I)


def get(path):
    req = urllib.request.Request(ROOT + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|td|tr|span|dt|dd|a)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return (s.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))


def items_of(html):
    """`div.title` 하나가 메뉴 하나다. 인분 표기는 이름에서 떼어 따로 돌려준다."""
    out = []
    for blk in RX_TITLE.findall(html):
        mi = RX_INBUN.search(blk)
        serve = strip_tags(mi.group(1)).strip().strip("()") if mi else ""
        name = strip_tags(RX_INBUN.sub(" ", blk))
        name = re.sub(r"\s+", " ", name).strip()
        if 2 <= len(name) <= 30:
            out.append((name, serve))
    seen, res = set(), []
    for n, s in out:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, s))
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for cname in CATS:
        q = "/bbs/board.php?bo_table=tteok_menu&sca=" + urllib.parse.quote(cname)
        got = items_of(get(q))
        if not got:
            print("   - %-10s 0개" % cname)
            time.sleep(GAP)
            continue
        cats.append({"name": cname, "parent": None, "ext_id": cname})
        for i, (n, serve) in enumerate(got):
            nm = n if n not in seen else "%s (%s)" % (n, cname)
            seen.add(nm)
            menus.append({"name": nm, "price": None, "price_source": None,
                          "compose_raw": serve, "cats": [[cname, i]]})
        print("   · %-10s %2d개" % (cname, len(got)))
        time.sleep(GAP)

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스 빈 JSON 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 화면 구조를 확인할 것.")
        return 1
    p = os.path.join(OUT, "eungtteok.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "응급실국물떡볶이", "slug": "eungtteok",
           "source": ROOT + "/bbs/board.php?bo_table=tteok_menu",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지(한글도메인 응급실국물떡볶이.kr). **가격은 공식에 없다** — 이름만. "
                   "인분 표기는 compose_raw 로 옮겼다. "
                   "⚠️ 옛 주소 eungtteok.grp.kr 은 도메인 만료로 판매 페이지가 뜬다.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
