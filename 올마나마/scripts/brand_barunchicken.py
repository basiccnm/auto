# -*- coding: utf-8 -*-
"""바른치킨(barunchicken) 메뉴판 전용 수집기.

- 카테고리 탭: /menu/index.php 의 `.menuItem[attr-seq]` (화면 순서 그대로)
- 목록: 페이지가 실제로 쓰는 AJAX — POST /itboard/front/product/product_list.ajax.php
        (page, limit, sh, shca) -> {"LIST":[{board_id,title,content,image_url,category}], "TOTAL":n}
        limit=9 라서 TOTAL 이 9 를 넘으면 page=2 를 반드시 따라간다.
- 상세: /menu/view.php?board_id=..&shca=..&page=.. -> 판매가(.costbx), 옵션문구(em)
- 원산지: 브랜드 공통 PDF /asset/document/원산지표시판.pdf (메뉴별 표)
- 알레르기: 브랜드 공통 PDF /asset/document/알레르기유발식품표시.pdf (매트릭스라 본문 미파싱)

DB 는 건드리지 않는다. 결과는 data/brand_menu_list/barunchicken.json 하나.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import os
import re
import time
import urllib.parse
import urllib.request

BASE = "https://barunchicken.com"
INDEX = BASE + "/menu/index.php"
AJAX = BASE + "/itboard/front/product/product_list.ajax.php"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "barunchicken.json")
GAP = 1.6

# 원산지표시판.pdf (2026년 7월 기준) 를 이미지로 읽어 옮긴 표. 원문 그대로.
ORIGIN_NOTE = (
    "원산지표시판 (https://barunchicken.com/asset/document/원산지표시판.pdf)\n"
    "※본 표시판은 2026년 7월 기준으로 작성했으며 해당 내용을 준수합니다.\n"
    "메뉴명 | 표시품목 | 원산지\n"
    "모든 치킨 메뉴 | 닭고기 | 국내산\n"
    "돈까스 | 돼지고기 | 국내산\n"
    "직화무뼈불닭발 | 닭발 | 국내산\n"
    "피데기오징어 | 오징어 | 원양산(국내가공)\n"
    "마른안주한판 | 명태 | 외국산(러시아)\n"
    "마른안주한판 | 오징어 | 외국산(중국)\n"
    "킬바사소세지 | 쇠고기 | 외국산(호주), 국내산 혼합\n"
    "킬바사소세지 | 돼지고기 | 국내산\n"
    "소세지한판구이 | 쇠고기 | 외국산(호주, 미국), 국내산 혼합\n"
    "소세지한판구이 | 돼지고기 | 국내산"
)

# 표시판의 「메뉴명」칸 -> 그 줄의 원산지 (원문 그대로)
ORIGIN_BY_NAME = {
    "직화무뼈불닭발": "닭발 국내산",
    "피데기오징어": "오징어 원양산(국내가공)",
    "마른안주한판": "명태 외국산(러시아), 오징어 외국산(중국)",
    "킬바사소세지": "쇠고기 외국산(호주), 국내산 혼합 / 돼지고기 국내산",
    "소세지한판구이": "쇠고기 외국산(호주, 미국), 국내산 혼합 / 돼지고기 국내산",
    "돈까스": "돼지고기 국내산",
}
# 표시판 첫 줄 「모든 치킨 메뉴 = 닭고기 국내산」이 걸리는 카테고리
CHICKEN_CATS = {"M001", "M002", "M004", "M005"}
ORIGIN_CHICKEN = "닭고기 국내산"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": INDEX})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")


def _post(shca, page, limit=9):
    body = urllib.parse.urlencode(
        {"page": str(page), "limit": str(limit), "sh": "", "shca": shca}).encode()
    req = urllib.request.Request(AJAX, data=body, headers={
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": INDEX,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))


def strip_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def cats_from_index():
    """탭 이름 + shca 코드를 화면에 찍힌 순서 그대로."""
    html = _get(INDEX)
    raw_n = len(re.findall(r"attr-seq=", html))
    body = strip_comments(html)
    got = re.findall(r'attr-tit="([^"]*)"\s+attr-seq="([^"]*)"', body)
    print("[탭] 주석 제거 전 attr-seq %d개 -> 제거 후 %d개" % (raw_n, len(got)))
    out = []
    seen = set()
    for tit, seq in got:
        tit = tit.strip()
        if seq in seen:
            continue
        seen.add(seq)
        out.append({"name": tit, "parent": None, "ext_id": seq})
        print("      %-5s %s" % (seq, tit))
    return out


def list_of(shca):
    """TOTAL 만큼 다 받을 때까지 page 를 따라간다."""
    rows, page, total = [], 1, None
    while True:
        j = _post(shca, page)
        total = int(j.get("TOTAL") or 0)
        got = j.get("LIST") or []
        rows.extend(got)
        print("      %s page=%d  +%d  (누적 %d / TOTAL %d)"
              % (shca, page, len(got), len(rows), total))
        if not got or len(rows) >= total or page > 12:
            break
        page += 1
        time.sleep(GAP)
    if len(rows) != total:
        print("      ⚠️ %s 개수 불일치: 받은 %d != TOTAL %d" % (shca, len(rows), total))
    return rows


def detail(board_id, shca, page):
    url = "%s/menu/view.php?board_id=%s&shca=%s&page=%s" % (BASE, board_id, shca, page)
    html = _get(url)
    price = note = None
    m = re.search(r'<div class="costbx">(.*?)</div>', html, re.S)
    if m:
        blk = m.group(1)
        notes = []
        b = re.search(r"<b>(.*?)</b>", blk, re.S)
        if b:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b.group(1))).strip()
            if re.fullmatch(r"[\d,]+", t):
                price = int(t.replace(",", ""))
            elif t:
                # 「반마리 : 20,900원 / 한마리 : 30,800원」처럼 값이 여러 개인 칸.
                # 하나를 고르면 추측이 되므로 price 는 비우고 원문만 남긴다.
                notes.append(t)
        e = re.search(r"<em>(.*?)</em>", blk, re.S)
        if e:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", e.group(1))).strip()
            if t:
                notes.append(t)
        note = " / ".join(notes) or None
    docs = re.findall(r'href="(/asset/document/[^"]+)"', strip_comments(html))
    return url, price, note, docs


# 메뉴 아닌 줄 걸러내기 — 지우기 전에 반드시 출력한다
def looks_not_menu(name, cat_names):
    why = []
    if re.search(r"[.!?~…]$", name):
        why.append("문장부호로 끝남")
    if len(name) >= 18:
        why.append("18자 이상")
    if name in cat_names:
        why.append("카테고리 이름과 같음")
    if name.startswith("#"):
        why.append("해시태그")
    return why


def main():
    cats = cats_from_index()
    if not cats:
        print("탭 0개 — 중단"); return
    cat_names = {c["name"] for c in cats}

    menus = {}          # name -> record
    order = []          # 이름 등장 순서
    flagged = []
    doc_links = set()

    for c in cats:
        shca, cname = c["ext_id"], c["name"]
        print("[목록] %s (%s)" % (cname, shca))
        rows = list_of(shca)
        time.sleep(GAP)
        for idx, r in enumerate(rows):
            name = (r.get("title") or "").strip()
            if not name:
                continue
            why = looks_not_menu(name, cat_names)
            if why:
                flagged.append((cname, name, why))
            rec = menus.get(name)
            if rec is None:
                rec = {
                    "name": name,
                    "price": None, "price_source": None, "price_note": None,
                    "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": None, "image_url": None,
                    "ext_id": str(r.get("board_id") or "") or None,
                    "cats": [],
                    "_shca": [],
                }
                img = r.get("image_url")
                if img:
                    rec["image_url"] = BASE + img
                menus[name] = rec
                order.append(name)
            rec["cats"].append([cname, idx])
            rec["_shca"].append(shca)

    print("\n[걸린 줄] %d개" % len(flagged))
    for cname, name, why in flagged:
        print("   - [%s] %r  <- %s" % (cname, name, ", ".join(why)))
    print("   (전부 공식 상품목록 API 의 title 필드라 실제 메뉴다 — 지우지 않는다)")

    # 상세 = 가격
    print("\n[상세] %d건" % len(order))
    for i, name in enumerate(order, 1):
        rec = menus[name]
        if not rec["ext_id"]:
            continue
        try:
            url, price, note, docs = detail(rec["ext_id"], rec["_shca"][0], 1)
        except Exception as e:
            print("   %3d/%d %-28s ERR %s" % (i, len(order), name, e))
            time.sleep(GAP)
            continue
        rec["detail_url"] = url
        if price:
            rec["price"] = price
            rec["price_source"] = "official"
        if note:
            rec["price_note"] = note
        doc_links.update(docs)
        print("   %3d/%d %-30s %s  %s"
              % (i, len(order), name, price if price else "-", note or ""))
        time.sleep(GAP)

    # 원산지 (브랜드 공통 표시판)
    for name, rec in menus.items():
        if name in ORIGIN_BY_NAME:
            rec["origin_raw"] = ORIGIN_BY_NAME[name]
        elif set(rec["_shca"]) & CHICKEN_CATS or "치킨" in name:
            # 표시판 첫 줄 「모든 치킨 메뉴 = 닭고기 국내산」
            rec["origin_raw"] = ORIGIN_CHICKEN

    for rec in menus.values():
        rec.pop("_shca", None)

    data = {
        "brand": "바른치킨",
        "slug": "barunchicken",
        "source": INDEX + " + " + AJAX + " (POST shca/page) + /menu/view.php",
        "collected_at": "2026-07-28",
        "origin_note": ORIGIN_NOTE,
        "cats": cats,
        "menus": [menus[n] for n in order],
    }
    if not data["menus"]:
        print("메뉴 0개 — 저장하지 않는다"); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("\n[문서 링크] %s" % sorted(doc_links))
    print("[저장] %s" % OUT)
    print("카테고리 %d개 · 메뉴 %d개 · 가격 %d개 · 원산지 %d개"
          % (len(cats), len(data["menus"]),
             sum(1 for m in data["menus"] if m["price"]),
             sum(1 for m in data["menus"] if m["origin_raw"])))


if __name__ == "__main__":
    main()
