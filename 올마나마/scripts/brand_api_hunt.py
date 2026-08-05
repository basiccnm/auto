# -*- coding: utf-8 -*-
"""브랜드 홈페이지가 **어떤 방식**인지 한 번에 훑는다 — API 를 뚫을 실마리 찾기. 2026-07-28

    python scripts/brand_api_hunt.py --need          # 가격 없는 브랜드만
    python scripts/brand_api_hunt.py --only 미스터피자

무엇을 보나 (렌더링된 DOM 한 장만 받아서 판단한다)
  · **가격이 화면에 있나** — 있으면 화면 파싱으로 끝난다(본죽·롯데리아가 이 경우)
  · **전역 JS 배열** (`var pList = [...]`) — 롯데리아가 이랬다
  · **`__NEXT_DATA__` / `__NUXT__`** — 서버가 데이터를 통째로 심어준다
  · **JSON 을 부르는 주소 문자열** (`/api/...`) — 그게 곧 우리가 부를 API
  · 아무것도 없으면 → 앱/플레이스/블로그로 가야 한다

⛔ 경로를 조합해 찔러보지 않는다. **DOM 에 적혀 있는 주소만** 본다
   (2026-07-16 엔드포인트 14개 추측 → 웹방화벽 IP 차단).
"""
import os
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WORKERS = 3

RX_WON = re.compile(r"[\d]{1,3}(?:,[\d]{3})+\s*원")
RX_SPLIT = re.compile(r">[\d]{1,3}(?:,[\d]{3})+<")      # 숫자와 「원」이 태그로 갈린 경우
RX_GLOBAL = re.compile(r"(?:var|let|const)\s+(\w+)\s*=\s*\[\s*\{")
RX_APIPATH = re.compile(r"[\"'](/(?:api|json)/[\w/\-{}.]{2,60})[\"']")
RX_APIURL = re.compile(r"[\"'](https?://[\w.\-]+/(?:api|json)/[\w/\-{}.]{2,60})[\"']")


def render(url, budget=13000):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,5000",
             "--virtual-time-budget=%d" % budget, "--dump-dom", url],
            capture_output=True, timeout=110)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def probe(row):
    name, url = row["name"], row["u"]
    dom = render(url)
    if not dom:
        return (name, "렌더실패", "", 0, 0)
    won = len(RX_WON.findall(dom))
    split = len(RX_SPLIT.findall(dom))
    hints = []
    g = [m.group(1) for m in RX_GLOBAL.finditer(dom)]
    if g:
        hints.append("전역배열 " + ",".join(dict.fromkeys(g))[:40])
    if "__NEXT_DATA__" in dom:
        hints.append("__NEXT_DATA__")
    if "__NUXT__" in dom:
        hints.append("__NUXT__")
    paths = [m.group(1) for m in RX_APIPATH.finditer(dom)]
    urls = [m.group(1) for m in RX_APIURL.finditer(dom)]
    api = list(dict.fromkeys(urls + paths))[:4]
    if api:
        hints.append("API " + " ".join(api))
    verdict = ("화면에 가격 있음" if won >= 5 else
               "가격 태그 쪼개짐" if split >= 5 else
               "화면에 가격 없음")
    return (name, verdict, " · ".join(hints)[:120], won, split)


def main():
    c = sqlite3.connect(DB, timeout=60)
    c.row_factory = sqlite3.Row
    # 🔴 `--only` 로 이름을 집어줄 때는 **비공개도 본다** (2026-07-31).
    #    신규 등록 브랜드는 메뉴판을 채우기 전까지 비공개라, 공개만 보면 훑을 수가 없었다.
    only = "--only" in sys.argv
    q = """SELECT b.name, b.homepage_url u FROM brands b
           WHERE COALESCE(b.homepage_url,'')<>''"""
    if not only:
        q += " AND b.published=1"
    if "--need" in sys.argv:
        q += """ AND (SELECT COUNT(*) FROM brand_menu_official o
                      WHERE o.brand_id=b.id AND o.price>0) < 5"""
    q += " ORDER BY COALESCE(b.frcs_cnt,0) DESC"
    rows = [dict(r) for r in c.execute(q)]
    if "--only" in sys.argv:
        k = sys.argv[sys.argv.index("--only") + 1]
        rows = [r for r in rows if k in r["name"]]
    if "--top" in sys.argv:
        rows = rows[:int(sys.argv[sys.argv.index("--top") + 1])]
    print("브랜드 %d곳 훑기\n" % len(rows), flush=True)
    print("%-16s %-16s %s" % ("브랜드", "판정", "실마리"), flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for name, verdict, hints, won, split in ex.map(probe, rows):
            print("  %-14s %-16s %s" % (name[:14], verdict, hints), flush=True)


if __name__ == "__main__":
    main()
