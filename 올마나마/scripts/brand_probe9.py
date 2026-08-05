# -*- coding: utf-8 -*-
"""대표가 준 브랜드 9곳 — **어떤 방식으로 뚫리는지** 조사만 한다. 2026-07-28

    python scripts/brand_probe9.py            # 조사 결과만
    python scripts/brand_probe9.py --dump 멕시카나치킨   # 그 브랜드 원문 줄 보기

🔴 조사 항목 (버거킹에서 배운 것)
   · `innerText`(보이는 글자) 말고 **DOM 전체**를 본다 — 숨은 탭에 메뉴가 있다
   · 가격이 «23,000원» 한 덩어리인지, «23,000» + «원» 으로 쪼개졌는지
   · 전역 JS 배열(`var pList=[...]`)·`__NEXT_DATA__` 가 있는지
   · DOM 에 적힌 API 주소가 있는지

⛔ 여기서는 **저장하지 않는다.** 어느 길로 갈지 정하는 게 목적이다.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# (브랜드, 주소, 대표가 말한 기대치)
SITES = [
    ("멕시카나치킨", "https://www.mexicana.co.kr/menu/product.asp?catecode=1000001", "가격포함"),
    ("호식이지두마리치킨", "https://www.9922.co.kr/chicken", "메뉴명만"),
    ("지코바치킨", "http://www.gcova.co.kr/", "가격포함"),
    ("피자마루", "https://www.pizzamaru.co.kr/menu/10", "가격포함"),
    ("59쌀피자", "https://xn--2e0b622b4gcxwb8x8a.kr/menu/list?ca_id=01", "가격포함"),
    ("프랭크버거", "https://frankburger.co.kr/html/menu_1.html", "메뉴만"),
    ("청년피자", "https://www.youngmanpizza.co.kr/sub01/menu.php", "가격포함"),
    ("원할머니보쌈", "https://wonandone.co.kr/bossam/menu.asp", "메뉴만"),
    # DB 에 주소가 있던 나머지 — 대표가 주소를 안 준 곳도 같이 본다
    ("노랑통닭", "https://www.norangtongdak.co.kr/", "메뉴명만"),
    ("가장맛있는족발", "http://www.jogbal.co.kr/", "?"),
    ("땅스부대찌개", "https://tsbudae.com/", "?"),
    ("탕화쿵푸마라탕", "https://www.tanghuokungfu.co.kr/", "?"),
]

RX_WON = re.compile(r"[\d]{1,3}(?:,[\d]{3})+\s*원")
RX_NUM = re.compile(r">\s*[\d]{1,3}(?:,[\d]{3})+\s*<")     # 숫자만 든 태그
RX_GLOBAL = re.compile(r"(?:var|let|const)\s+(\w+)\s*=\s*\[\s*\{")
RX_API = re.compile(r"""["'](/?(?:api|json)/[\w/\-{}.]{2,60})["']""")


def render(url, budget=15000):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,6000",
             "--virtual-time-budget=%d" % budget, "--dump-dom", url],
            capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", "replace")
    except Exception as e:
        return "__ERR__" + str(e)[:60]


def to_lines(dom):
    s = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd|strong|em)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return [x.strip() for x in re.sub(r"[ \t　]+", " ", s).split("\n") if x.strip()]


def probe(item):
    name, url, expect = item
    dom = render(url)
    if dom.startswith("__ERR__"):
        return (name, expect, "렌더실패", dom[7:], 0, 0)
    won = len(RX_WON.findall(dom))
    split = len(RX_NUM.findall(dom))
    lines = to_lines(dom)
    # 줄 단위로 «숫자»+«원» 이 갈린 경우도 센다
    merged = 0
    for i, t in enumerate(lines[:-1]):
        if re.match(r"^\d{1,3}(?:,\d{3})+$", t) and lines[i + 1].strip() == "원":
            merged += 1
    hints = []
    g = [m.group(1) for m in RX_GLOBAL.finditer(dom)]
    if g:
        hints.append("전역배열 " + ",".join(dict.fromkeys(g))[:30])
    if "__NEXT_DATA__" in dom:
        hints.append("__NEXT_DATA__")
    if "__NUXT__" in dom:
        hints.append("__NUXT__")
    api = list(dict.fromkeys(m.group(1) for m in RX_API.finditer(dom)))[:3]
    if api:
        hints.append("API " + " ".join(api))
    verdict = ("가격 있음" if won >= 3 else
               "가격 쪼개짐" if (split >= 3 or merged >= 3) else
               "가격 없음")
    return (name, expect, verdict, " · ".join(hints)[:70], won, split + merged)


def main():
    if "--dump" in sys.argv:
        want = sys.argv[sys.argv.index("--dump") + 1]
        for name, url, _ in SITES:
            if want not in name:
                continue
            lines = to_lines(render(url))
            print("● %s — 줄 %d개" % (name, len(lines)))
            for t in lines[:80]:
                print("   %s" % t[:70])
        return

    print("%-16s %-8s %-12s %-8s %s" % ("브랜드", "기대", "판정", "원/쪼갬", "실마리"))
    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, expect, verdict, hints, won, split in ex.map(probe, SITES):
            print("  %-14s %-8s %-12s %3d/%-4d %s"
                  % (name[:14], expect, verdict, won, split, hints), flush=True)


if __name__ == "__main__":
    main()
