# -*- coding: utf-8 -*-
"""훌랄라참숯바베큐(hoolala) 메뉴판 수집 — 전용 스크립트.

    python scripts/brand_hoolala.py

만드는 것: data/brand_menu_list/hoolala.json  (DB 는 건드리지 않는다)

── 어떻게 뚫었나 ─────────────────────────────────────────────────────────
홈(http://www.hoolala.co.kr/)은 그누보드 껍데기이고 게시판 링크만 잔뜩 나온다.
주석을 지운 홈 HTML 의 <nav id="gnb"> 안에 실제 메뉴판 주소가 그대로 있었다:

    /renewal/menu/{cignature,represent,popularity,premium,barbecue,fried,chibap}.php

이 7개가 화면의 「MENU」 탭(.tnb_wr .fix_tab) 순서와 같다. 주소를 조합해 찍은 게 아니라
네비게이션에서 읽은 것이다. 페이징은 없다(탭 7개가 전부, page 파라미터 없음).

── 페이지 구조 ───────────────────────────────────────────────────────────
6개 페이지: <ul class="m_row3_list"> 안의 <figure> 하나가 메뉴 하나.
            이름 = <p class="subject">, 사진 = <img src>
chibap:     <ul class="b_row6_list"> 안의 <figure>, 이름 = <figcaption>

⚠️ 치밥 페이지는 홈페이지가 실제로 같은 이름을 두 번 진열한다
   (menu_b01/menu_b04 = 「참숯 간장 치밥」, menu_b02/menu_b05 = 「참숯 닭갈비 치밥」).
   사진은 서로 다른데 캡션이 같다. 홈페이지 그대로 두 자리를 다 기록하고,
   menus 는 이름 기준 한 줄로 합쳤다. 이름을 임의로 바꾸지 않았다.

── 가격 · 원산지 ─────────────────────────────────────────────────────────
가격: 사이트 어디에도 없다. 메뉴 페이지에 숫자 자체가 없다  → 전부 price=null
원산지: 없다. 확인한 곳 —
   · 메뉴 7개 페이지 본문 · 홈 · 푸터
   · /renewal/brand/about.php  /renewal/startup/why.php
     (why.php 의 「국내산 참숯」은 숯 이야기지 닭고기 원산지가 아니다 — 쓰지 않았다)
   · /renewal/lovehoolala/domestic.php → 「사랑의 역사 국내활동」(밥차·장학금)이지 원산지 아님
   · 게시판 자체 검색(sfl=wr_subject||wr_content, stx=원산지) → notice 0건
   · 메뉴 사진을 눈으로 열어봄(menu_b01/b02/b04/b05, cignature1) → 글자 없는 음식 사진
   · main.js 의 .playbtn 상세팝업 핸들러는 통째로 주석 처리돼 있다 = 상세페이지가 없다
   → origin_note = null. 짐작해서 채우지 않았다.
"""
import io
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://www.hoolala.co.kr"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# 화면 「MENU」 탭 순서 그대로 (홈 <nav id="gnb"> 에서 읽은 것)
TABS = [
    ("시그니처 메뉴",   "/renewal/menu/cignature.php"),
    ("대표 메뉴",       "/renewal/menu/represent.php"),
    ("인기 메뉴",       "/renewal/menu/popularity.php"),
    ("프리미엄 메뉴",   "/renewal/menu/premium.php"),
    ("숯불바베큐 메뉴", "/renewal/menu/barbecue.php"),
    ("후라이드 메뉴",   "/renewal/menu/fried.php"),
    ("치밥 메뉴",       "/renewal/menu/chibap.php"),
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "brand_menu_list", "hoolala.json")


def fetch(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("euc-kr", "replace")


def body_of(html):
    """주석·스크립트를 걷어내고 <main> 안의 메뉴 섹션만 남긴다.

    ⚠️ 끝을 <footer> 로 자르면 그 앞에 있는 <aside class="quick"> 이 딸려 들어온다.
       거기에도 <figure><figcaption>매장찾기 / 창업문의</figcaption> 가 있어서
       페이지마다 메뉴가 2개씩 늘어난다(실제로 30개로 부풀었다). </main> 에서 자른다.
    """
    h = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    i = h.find('<section class="menu_sec')
    if i < 0:
        return ""
    j = h.find("</main>", i)
    if j < 0:
        j = h.find("<aside", i)
    if j < 0:
        j = h.find("<footer", i)
    return h[i:j if j > 0 else len(h)]


# 메뉴 아닌 줄을 걸러내는 기준 (문장부호로 끝남 / 18자 이상 / 카테고리 이름과 동일)
def is_junk(name, cat_names):
    if not name:
        return "빈 문자열"
    if len(name) >= 18:
        return "18자 이상"
    if name[-1] in ".!?~…,":
        return "문장부호로 끝남"
    if name in cat_names:
        return "카테고리 이름과 같음"
    return None


def collect():
    cat_names = [c for c, _ in TABS]
    cats = [{"name": c, "parent": None, "ext_id": None} for c, _ in TABS]

    by_name = {}     # 이름 -> 메뉴 dict (이름 기준 한 줄로 합침)
    order = []       # 처음 나온 순서 유지
    dropped = []

    for cat, path in TABS:
        body = body_of(fetch(path))
        if not body:
            print("  !! 본문 못 찾음:", path)
            continue

        # <figure> 하나 = 메뉴 하나. 이름은 .subject(6개 페이지) 또는 <figcaption>(치밥)
        figs = re.findall(r"<figure>(.*?)</figure>", body, re.S)
        idx = 0
        for fg in figs:
            m = re.search(r'<p class="subject">(.*?)</p>', fg, re.S)
            if not m:
                m = re.search(r"<figcaption>(.*?)</figcaption>", fg, re.S)
            if not m:
                continue
            name = re.sub(r"<[^>]+>", "", m.group(1))
            name = re.sub(r"\s+", " ", name).strip()

            why = is_junk(name, cat_names)
            if why:
                dropped.append((cat, name, why))
                continue

            im = re.search(r'<img src="([^"]+)"', fg)
            img = (BASE + im.group(1)) if im else None

            if name in by_name:
                by_name[name]["cats"].append([cat, idx])
                # 같은 이름이 두 번 진열되면 첫 사진을 유지한다
            else:
                by_name[name] = {
                    "name": name,
                    "price": None,
                    "price_source": None,
                    "price_note": None,
                    "weight_raw": None,
                    "origin_raw": None,
                    "allergy_raw": None,
                    "detail_url": BASE + path,
                    "image_url": img,
                    "ext_id": None,
                    "cats": [[cat, idx]],
                }
                order.append(name)
            idx += 1

        print("  %-12s %s  (자리 %d)" % (cat, path, idx))

    return cats, [by_name[n] for n in order], dropped


def main():
    print("훌랄라참숯바베큐 — 메뉴판 수집")
    cats, menus, dropped = collect()

    if not menus:
        print("메뉴 0개 — 파일을 저장하지 않는다.")
        return 1

    if dropped:
        print("\n버린 줄 (%d):" % len(dropped))
        for cat, name, why in dropped:
            print("  [%s] %r  ← %s" % (cat, name, why))
    else:
        print("\n버린 줄 없음")

    data = {
        "brand": "훌랄라참숯바베큐",
        "slug": "hoolala",
        "source": BASE + "/renewal/menu/cignature.php 외 6개 (MENU 탭 전부)",
        "collected_at": "2026-07-28",
        # 사이트 어디에도 원산지 표기가 없다 (스크립트 상단 주석에 확인한 곳 나열)
        "origin_note": None,
        "cats": cats,
        "menus": menus,
    }

    path = os.path.normpath(OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    n_price = sum(1 for m in menus if m["price"] is not None)
    n_org = sum(1 for m in menus if m["origin_raw"])
    print("\n저장: %s" % path)
    print("카테고리 %d개(하위 0) · 메뉴 %d개 · 가격 %d개 · 원산지 %d개"
          % (len(cats), len(menus), n_price, n_org))
    return 0


if __name__ == "__main__":
    sys.exit(main())
