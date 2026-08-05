# -*- coding: utf-8 -*-
"""메뉴별 **재료 후보를 레시피 사이트에서** 근거와 함께 모은다. 2026-07-26

🔴 왜 필요한가 (대표 지시)
   *"재료도 받은 메뉴를 가지고 임의 설계가 아닌 블로그레시피나 후기나 홈페이지 등을 보고 재료도 만들고
     모르겠으면 환각으로 지어내지 말고 아는것까지만 정확히 재료를 나내주면 될듯"*
   *"재료가 알아야 단가가 나오고 그래야 흐름이 이루어짐"*

   브랜드 홈페이지 상세페이지에는 **가격·중량**은 있어도 **재료**가 없다(BBQ 40쪽 확인).
   재료는 레시피 글에서 온다. 만개의레시피는 재료 블록이 구조화돼 있어 기계로 읽힌다.

⛔ 여기서 나온 문장을 **그대로** 저장한다. 요약·추측·보충 금지.
   DB 반영은 사람이 보고 고른 것만 한다(`ingredients-evidence-only`).

    python scripts/menu_recipe_crawl.py --brand BBQ치킨
    python scripts/menu_recipe_crawl.py --top 30      # 상위 30 브랜드의 모든 메뉴
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "menu_recipes")
REPORT = os.path.join(BASE, "data", "research", "menu_recipes.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "8000"
WORKERS = 3            # 상세 수집기와 같이 돌 수 있으니 낮게
PER_MENU = 3           # 메뉴당 볼 레시피 수

SEARCH = "https://www.10000recipe.com/recipe/list.html?q=%s"
RX_RECIPE = re.compile(r"/recipe/(\d{5,})")
JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")


def render(url):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,3000",
             "--virtual-time-budget=" + BUDGET, "--dump-dom", url],
            capture_output=True, timeout=70)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def to_text(dom):
    s = JUNK_TAG.sub(" ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


SKIP = ("구매", "계량법 안내", "계량법", "재료 추가", "쿠팡", "광고",
        # 🔴 재료가 아닌 것들 — 만개의레시피 재료 블록 뒤에 붙어 들어온다(2026-07-26 확인)
        "조리도구", "노하우", "궁중팬", "이쁜접시", "프라이팬", "냄비", "웍", "도마", "칼",
        "저울", "계량컵", "계량스푼", "집게", "국자", "뒤집개", "채반", "믹싱볼",
        "동영상", "사진", "레시피", "만개의레시피")
# `▶ 고추장 조리법` 처럼 화살표로 시작하는 팁 줄도 재료가 아니다
RX_NOTINGREDIENT = re.compile(r"^[▶▷▪■◆●※\-*]|조리법$|보관법$|손질법$|고르는\s*법$|대체$")
# 분량으로 보이는 줄 — 재료명 다음 줄에 따로 나온다
RX_QTY = re.compile(r"^(?:[\d/.,]+\s*)?(?:개|장|대|컵|큰술|작은술|스푼|g|kg|ml|L|줌|톨|쪽|봉|팩|알|마리|공기|T|t)\b"
                    r"|^[\d/.,]+$|^(?:약간|조금|취향껏|적당량|한줌|조금씩)$", re.I)


def ingredients(text):
    """'재료' 블록을 **원문 그대로** 뜨고, 쪼개진 재료명+분량만 붙인다.
    🔴 요약·추측·보충 금지(`ingredients-evidence-only`). 노이즈만 걷어낸다 —
       만개의레시피는 줄마다 '구매' 버튼 글자와 '계량법 안내'가 섞여 나온다."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    raw, on, group = [], False, ""
    for l in lines:
        if re.match(r"^(재료|주재료|[가-힣 ]*재료)\s*$", l) or re.match(r"^재료\b", l):
            on = True
            continue
        if not on:
            continue
        if re.match(r"^(조리순서|만드는\s*법|요리순서|레시피|Step|팁|후기|댓글|이런 조리|관련)", l):
            break
        if len(l) > 60 or len(raw) >= 80:
            break
        if l in SKIP or not re.search(r"[가-힣\d]", l):
            continue
        if RX_NOTINGREDIENT.search(l):
            continue
        m = re.match(r"^\[(.+?)\]$", l)          # [주재료] [양념장] 같은 묶음 표시
        if m:
            group = m.group(1)
            continue
        raw.append({"group": group, "line": l})
    # 재료명 + 다음 줄 분량 붙이기
    out = []
    i = 0
    while i < len(raw):
        name = raw[i]["line"]
        qty = ""
        if i + 1 < len(raw) and RX_QTY.match(raw[i + 1]["line"]):
            qty = raw[i + 1]["line"]
            i += 1
        if not RX_QTY.match(name):
            out.append({"group": raw[i]["group"], "name": name, "qty": qty})
        i += 1
    return out[:40]


# 메뉴명에서 그 메뉴를 남과 구분해 주는 낱말 — 흔한 말은 뺀다
COMMON = ("떡볶이", "치킨", "피자", "김밥", "버거", "국밥", "덮밥", "세트", "단품", "메뉴",
          "오리지널", "기본", "한마리", "반마리", "인분", "정식", "반상", "한상")


def key_words(menu):
    s = re.sub(r"\([^)]*\)|\d+", " ", menu)
    toks = [t for t in re.split(r"[\s·,/]+", s) if len(t) >= 2]
    out = []
    for t in toks:
        v = t
        for cw in COMMON:
            v = v.replace(cw, "")
        if len(v) >= 2:
            out.append(v)
    return out


def do_menu(job):
    """🔴 만개의레시피는 **흐릿하게 검색**한다(2026-07-26 확인).
    '삼첩분식 바질크림떡볶이' 로 찾았는데 백종원 일반 떡볶이 레시피가 나와
    바질크림·로제 두 메뉴에 **같은 레시피**가 붙었다.
    그래서 제목에 메뉴의 구분 낱말(바질·크림·로제)이 없으면 `weak=True` 로 표시한다.
    버리지는 않는다 — 사람이 보고 고른다."""
    brand, menu, mid = job["brand"], job["menu"], job["id"]
    kws = key_words(menu)
    recipes = []
    for q in ("%s %s" % (brand, menu), menu):
        dom = render(SEARCH % urllib.parse.quote(q))
        ids = list(dict.fromkeys(RX_RECIPE.findall(dom)))[:PER_MENU]
        for rid in ids:
            u = "https://www.10000recipe.com/recipe/%s" % rid
            d2 = render(u)
            if not d2:
                continue
            t = to_text(d2)
            ing = ingredients(t)
            if not ing:
                continue
            title = ""
            m = re.search(r"(?is)<title[^>]*>(.*?)</title>", d2)
            if m:
                title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()[:80]
            flat = re.sub(r"\s+", "", title)
            weak = bool(kws) and not any(k in flat for k in kws)
            recipes.append({"q": q, "url": u, "title": title, "weak": weak,
                            "ingredients": ing})
        if recipes:
            break
    rec = {"menu_id": mid, "brand": brand, "menu": menu, "recipes": recipes}
    nw = sum(1 for r in recipes if r.get("weak"))
    print("  %-14s %-24s 레시피 %d개(약함 %d) · 재료 %d종" % (
        brand[:14], menu[:24], len(recipes), nw,
        sum(len(r["ingredients"]) for r in recipes)), flush=True)
    return rec


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    only = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    # --brand 를 주면 순위 제한을 걸지 않는다(2026-07-26: 삼첩분식이 35위라 --top 30 에 걸려 0곳이었다)
    lim = 999 if only else top
    brands = [dict(r) for r in c.execute("""
        SELECT b.id, b.name FROM brands b WHERE b.published=1
          AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?""", (lim,))]
    if only:
        brands = [b for b in brands if only in b["name"]]
    jobs = []
    for b in brands:
        for m in c.execute("SELECT id, name FROM menus WHERE brand_id=? ORDER BY sort_order",
                           (b["id"],)):
            jobs.append({"brand": b["name"], "menu": m["name"], "id": m["id"]})
    print("브랜드 %d곳 · 메뉴 %d개 레시피 수집" % (len(brands), len(jobs)), flush=True)
    print("", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_menu, jobs))
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    got = sum(1 for r in res if r["recipes"])

    # 🔴 레시피 못 찾은 메뉴는 **빈 채로 두고 목록에 적는다**(대표 지시 2026-07-26).
    #    억지로 채우지 않는다. 이 목록이 곧 "대체 완제품·유사 기성품을 붙일 대상"이 된다.
    miss = [{"menu_id": r["menu_id"], "brand": r["brand"], "menu": r["menu"]}
            for r in res if not r["recipes"]]
    mp = os.path.join(BASE, "data", "research", "recipe_missing.json")
    io.open(mp, "w", encoding="utf-8").write(json.dumps(miss, ensure_ascii=False, indent=1))

    # 같은 레시피가 여러 메뉴에 붙은 것 — 검색어가 브랜드 특성을 못 살린 신호
    from collections import defaultdict
    byurl = defaultdict(list)
    for r in res:
        for x in r["recipes"]:
            byurl[x["url"]].append("%s/%s" % (r["brand"], r["menu"]))
    dup = {u: v for u, v in byurl.items() if len(v) > 1}

    print("", flush=True)
    print("끝. 재료 후보 확보 %d/%d 메뉴 · 못 찾음 %d개 → %s" % (got, len(res), len(miss), REPORT), flush=True)
    if miss:
        print("   못 찾은 메뉴는 %s 에 적었다(대체품 붙일 대상)" % mp, flush=True)
    if dup:
        print("   ⚠️ 같은 레시피가 여러 메뉴에 붙음 %d건 — 검색어를 좁혀야 한다" % len(dup), flush=True)
        for u, v in list(dup.items())[:8]:
            print("      %s ← %s" % (u.split("/")[-1], " / ".join(v[:4])), flush=True)


if __name__ == "__main__":
    main()
