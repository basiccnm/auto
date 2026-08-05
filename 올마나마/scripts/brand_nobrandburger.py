# -*- coding: utf-8 -*-
"""노브랜드버거 메뉴 수집 — 공식(신세계푸드) 한 장. 2026-07-31 신설

    python scripts/brand_nobrandburger.py

경로 (2026-07-31 확인)
    https://www.shinsegaefood.com/nobrandburger/index.sf
    ※ `nobrandburger.com` 으로 가면 위 주소로 넘어간다.

구조 — **한 페이지에 전 메뉴가 다 들어 있다.** 탭은 화면 전환일 뿐 요청이 없다.
    button.menu_tab_btn      탭 이름 (맨 앞 «전체» 는 뺀다)
    div.menu_group           탭별 묶음 — 화면 순서가 탭 순서와 같다
    button.menu_anch         메뉴 하나
        data-name   메뉴명 (`&lt;/br&gt;` 뒤에 영문명이 붙어 있어 **첫 줄만** 쓴다)
        data-story  설명 (인라인 style 태그가 섞여 들어와 태그를 걷어낸다)

🔴 **가격이 없다.** 공식은 이름·설명만 싣는다 → 이름만 넣고 가격은 뒤 단계에서.
🔴 단품/세트 구분도 공식에 없다. 세트 가격은 뒤 단계에서 따로 받는다.

결과: data/brand_menu_list/nobrandburger.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
URL = "https://www.shinsegaefood.com/nobrandburger/index.sf"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

RX_TAB = re.compile(r'<button[^>]*class="[^"]*menu_tab_btn[^"]*"[^>]*>(.*?)</button>', re.S | re.I)
# 🔴 `id` 가 class 앞에 온다(`<div id="cate_218" class="menu_group">`). 순서를 가정하지 않는다.
#    🔴 카테고리 이름은 그룹 안 `em.menu_group_title` 에 **직접 적혀 있다.**
#       탭 버튼 순서와 그룹 순서가 같으리라 기대하지 말고 이걸 쓴다(2026-07-31).
RX_GROUP_OPEN = re.compile(r'<div[^>]*class="[^"]*menu_group[^"]*"[^>]*>', re.I)
RX_ID = re.compile(r'id="([^"]*)"', re.I)
RX_GTITLE = re.compile(r'<em[^>]*class="[^"]*menu_group_title[^"]*"[^>]*>(.*?)</em>', re.S | re.I)
# 🔴 **여는 태그를 «>» 로 잘라내면 안 된다** (2026-07-31 실제로 0개가 나온 원인).
#    data-name 값 안에 «</br>» 가 들어 있다 — 즉 **속성 값 안에 > 가 있다.**
#    그래서 태그를 > 로 자르면 data-name 이 중간에 끊겨 짝이 안 맞는다.
#    → 태그를 자르지 말고 data-name="..." 을 본문에서 직접 찾는다.
RX_NAME = re.compile(r'data-name="([^"]*)"', re.S | re.I)
RX_STORY = re.compile(r'data-story="([^"]*)"', re.S | re.I)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def first_line(s):
    """`data-name` 은 «한글명</br>\n영문명» 이다. 첫 줄(한글명)만 쓴다."""
    s = (s or "").replace("&lt;/br&gt;", "\n").replace("&lt;br&gt;", "\n")
    s = re.sub(r"(?i)</?br\s*/?>", "\n", s)
    return strip_tags(s.split("\n")[0])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=25) as r:
        html = r.read().decode("utf-8", "replace")

    tabs = [strip_tags(x) for x in RX_TAB.findall(html)]
    tabs = [t for t in tabs if t and t != "전체"]
    # menu_group 여는 태그 위치를 찾아 **다음 그룹 직전까지**를 그 그룹의 몸통으로 자른다.
    opens = [(m.start(), m.group(0)) for m in RX_GROUP_OPEN.finditer(html)]
    groups = []
    for k, (pos, tag) in enumerate(opens):
        # 🔴 마지막 그룹은 «다음 그룹» 이 없어 페이지 끝까지 먹는다 —
        #    그러면 매장안내·팝업까지 삼켜 「음료 284개」 같은 헛수가 나온다(2026-07-31).
        #    끝은 `ul.menu_list` 가 닫히는 지점으로 자른다.
        end = opens[k + 1][0] if k + 1 < len(opens) else len(html)
        body = html[pos:end]
        stop = body.find("</ul>")
        if stop > 0:
            body = body[:stop]
        if "menu_anch" not in body:
            continue
        m = RX_ID.search(tag)
        groups.append((m.group(1) if m else "g%d" % k, body))

    cats, menus, seen = [], [], set()
    for gi, (gid, body) in enumerate(groups):
        mt = RX_GTITLE.search(body)
        cname = strip_tags(mt.group(1)) if mt else (
            tabs[gi] if gi < len(tabs) else "카테고리%d" % (gi + 1))
        items = []
        for mn in RX_NAME.finditer(body):
            nm = first_line(mn.group(1))
            if not nm:
                continue
            # 같은 버튼의 data-story 는 data-name 바로 뒤에 온다 — 그 구간에서만 찾는다
            ms = RX_STORY.search(body, mn.end(), mn.end() + 1200)
            items.append((nm, strip_tags(ms.group(1))[:150] if ms else ""))
        if not items:
            continue
        cats.append({"name": cname, "parent": None, "ext_id": gid})
        for i, (nm, story) in enumerate(items):
            key = nm if nm not in seen else "%s (%s)" % (nm, cname)
            seen.add(key)
            menus.append({"name": key, "price": None, "price_source": None,
                          "compose_raw": story, "cats": [[cname, i]]})
        print("   · %-16s %2d개" % (cname[:16], len(items)))

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스 빈 JSON 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 화면 구조를 확인할 것.")
        return 1
    p = os.path.join(OUT, "nobrandburger.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "노브랜드버거", "slug": "nobrandburger", "source": URL,
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식(신세계푸드) 한 장에 전 메뉴가 있다. **가격·세트 구분은 공식에 없다** — "
                   "이름만. 세트 가격은 뒤 단계에서 따로 받을 것.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
