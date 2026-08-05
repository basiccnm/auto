# -*- coding: utf-8 -*-
"""또래오래(toreore) 메뉴판 수집 — 게시판형(board_list.php / board_view.php)

- 카테고리 탭: board_list.php 의 .tabMenu 에서 화면 순서대로 (category_seq)
- 메뉴 목록: 카테고리별 board_list.php?category_seq=N 의 .galleryTypeBoard li
- 상세: board_view.php?board_seq=&category_seq= 에서 원산지/알레르기/설명
- 가격: 공식 홈페이지에 공개하지 않음 → price=null

DB 를 건드리지 않는다. 결과는 data/brand_menu_list/toreore.json 하나.
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.toreore.com"
LIST = BASE + "/board/menu/board_list.php"
VIEW = BASE + "/board/menu/board_view.php"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "toreore.json")
TODAY = "2026-07-28"

_last = [0.0]


def get(url):
    """1.5초 이상 간격."""
    wait = 1.6 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30, context=CTX).read()
    _last[0] = time.time()
    return d.decode("utf-8", "replace")


def strip_comments(h):
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&hearts;", ""))
    return re.sub(r"\s+", " ", s).strip()


def tabs(html):
    """탭 이름 ↔ category_seq, 화면 순서 그대로. 「전체」는 집계 탭이라 제외."""
    m = re.search(r'<div class="tabMenu[^"]*">(.*?)</div>\s*<div', html, re.S)
    if not m:
        m = re.search(r'<div class="tabMenu[^"]*">(.*?)</ul>', html, re.S)
    blk = m.group(1)
    out = []
    for a in re.finditer(r'<a href="[^"]*?category_seq=(\d+)"[^>]*>(.*?)</a>', blk, re.S):
        out.append((a.group(1), txt(a.group(2))))
    return out


def parse_list(html):
    """.galleryTypeBoard 안의 li 를 화면 순서대로."""
    m = re.search(r'<div class="galleryTypeBoard[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S)
    blk = m.group(1) if m else html
    out = []
    for li in re.finditer(r"<li[^>]*>(.*?)</li>", blk, re.S):
        b = li.group(1)
        if "board_view.php" not in b:
            continue
        seq = re.search(r"board_seq=(\d+)", b)
        cs = re.search(r"board_seq=\d+&(?:amp;)?category_seq=(\d+)", b)
        nm = re.search(r'<div class="menu_name">(.*?)</div>', b, re.S)
        des = re.search(r'<div class="menu_des">(.*?)</div>', b, re.S)
        img = re.search(r'<img src="([^"]+)"', b)
        if not (seq and nm):
            continue
        out.append({
            "ext_id": seq.group(1),
            "name": txt(nm.group(1)),
            "kind": txt(des.group(1)) if des else None,
            "image_url": (BASE + img.group(1)) if img and img.group(1).startswith("/") else (img.group(1) if img else None),
            "detail_cs": cs.group(1) if cs else None,
        })
    return out


def parse_view(html):
    h = strip_comments(html)
    m = re.search(r'<div class="bvInfo">(.*?)</div>\s*</div>', h, re.S)
    blk = m.group(1) if m else h
    out = {"name_kor": None, "kind": None, "origin_raw": None, "allergy_raw": None,
           "price": None, "weight_raw": None}
    k = re.search(r'<div class="menuName_kor">(.*?)</div>', blk, re.S)
    if k:
        out["name_kor"] = txt(k.group(1))
    kd = re.search(r'<div class="menuKind">(.*?)</div>', blk, re.S)
    if kd:
        out["kind"] = txt(kd.group(1)) or None
    for lbl, key in (("원산지 정보", "origin_raw"), ("알레르기 정보", "allergy_raw"),
                     ("중량 정보", "weight_raw")):
        mm = re.search(r'<div class="titTxt">\s*' + lbl + r'\s*</div>\s*(.*?)(?=<div class="titTxt">|$)',
                       blk, re.S)
        if mm:
            v = txt(mm.group(1))
            out[key] = v or None
    # 가격이 어디 적혀 있는지 확인용 (현재 공식 상세엔 없음)
    p = re.search(r"([0-9][0-9,]{2,})\s*원", txt(blk))
    if p:
        out["price"] = int(p.group(1).replace(",", ""))
    return out


BAD = re.compile(r"(글쓰기|목록|이전글|다음글|전체)$")


def is_menu(name, catnames):
    if not name:
        return False, "빈 이름"
    if name in catnames:
        return False, "카테고리 이름과 같음"
    if BAD.match(name):
        return False, "게시판 UI"
    if re.search(r"[.!?]$", name):
        return False, "문장부호로 끝남"
    if len(name) >= 18:
        return False, "18자 이상"
    return True, None


def main():
    home = strip_comments(get(LIST))
    cts = tabs(home)
    print("탭:", cts)
    catnames = {n for _, n in cts}

    cats = [{"name": n, "parent": None, "ext_id": cs} for cs, n in cts]

    menus = {}          # name -> dict
    order = []          # name 순서 (첫 등장)
    dropped = []
    for cs, cname in cts:
        html = strip_comments(get(LIST + "?category_seq=" + cs))
        rows = parse_list(html)
        print("  %s(%s) %d건" % (cname, cs, len(rows)))
        pos = 0
        for r in rows:
            ok, why = is_menu(r["name"], catnames)
            if not ok:
                dropped.append((r["name"], why, cname))
                continue
            m = menus.get(r["name"])
            if not m:
                m = {"name": r["name"], "price": None, "price_source": "official",
                     "price_note": None, "weight_raw": None, "origin_raw": None,
                     "allergy_raw": None, "detail_url": None, "image_url": r["image_url"],
                     "ext_id": r["ext_id"], "cats": []}
                menus[r["name"]] = m
                order.append(r["name"])
            m["cats"].append([cname, pos])
            if not m["image_url"]:
                m["image_url"] = r["image_url"]
            if m["detail_url"] is None:
                m["detail_url"] = "%s?board_seq=%s&category_seq=%s" % (VIEW, r["ext_id"], cs)
            pos += 1

    # 상세 — board_seq 당 한 번만
    seen = set()
    for name in order:
        m = menus[name]
        if m["ext_id"] in seen:
            continue
        seen.add(m["ext_id"])
        d = parse_view(get(m["detail_url"]))
        m["origin_raw"] = d["origin_raw"]
        m["allergy_raw"] = d["allergy_raw"]
        m["weight_raw"] = d["weight_raw"]
        if d["price"]:
            m["price"] = d["price"]
            m["price_note"] = "공식 상세페이지"
        print("   ·", name, "| 원산지:", d["origin_raw"], "| 가격:", d["price"])

    if not menus:
        print("메뉴 0건 — 저장하지 않음")
        return

    if dropped:
        print("\n버린 줄:")
        for n, why, c in dropped:
            print("  -", n, "|", why, "|", c)

    doc = {
        "brand": "또래오래", "slug": "toreore", "source": LIST,
        "collected_at": TODAY,
        "origin_note": None,
        "cats": cats,
        "menus": [menus[n] for n in order],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("\n저장:", OUT)
    print("카테고리 %d · 메뉴 %d · 가격 %d"
          % (len(cats), len(doc["menus"]), sum(1 for m in doc["menus"] if m["price"])))


if __name__ == "__main__":
    main()
