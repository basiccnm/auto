# -*- coding: utf-8 -*-
"""메가MGC커피 메뉴판 — **앱 API**(정본)에서 카테고리·메뉴·가격을 받고,
공식 홈페이지에서 «컵용량·설명»만 보태 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_megamgc.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/megamgccoffee.json` 뿐이다.
   `brand_menu_store` 를 import 하지 않는다.

━━━ ① 앱(APK) — **여기가 정본이다** ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
폰에 깔린 APK 를 뽑아 dex 문자열에서 주소를 읽었다(외부에서 받지 않았다):

    adb -s <기기> shell pm path co.kr.waldlust.megacoffee
    adb -s <기기> pull .../base.apk

    classes2.dex 안의 문자열 →  https://app.annhouse.co.kr/api/     (베이스)
                                menu/general/list · menu/option · store/list · common/init  (경로)
                                GeneralMenuRequest(store_cd=…)                              (요청 모델)

    🔴 POST https://app.annhouse.co.kr/api/menu/general/list
       Content-Type: application/json     body {"store_cd": ""}
       → {"all":{"upper_ctg_list":[{upper_ctg_cd, upper_ctg_nm,
                                    ctg_list:[{ctg_cd, ctg_nm, item_list:[…]}]}],
                 "allergy_list":[…]}}
       한 번에 **상위 8 · 하위 27 · 상품 296(진열 363자리) · 가격 전부** 가 온다.
       `GET` 은 405 다 — 반드시 POST.

    `store_cd:""` = 매장을 고르기 전 앱이 보여주는 **기준가**(가맹점별로 다를 수 있다).

    ⚠️ HOT/ICE 는 `temperature` 한 칸이다 — `HOT`·`ICE`·`BOTH`·`NONE`.
       `BOTH`(아메리카노 1,700)는 **HOT·ICE 가 같은 값 하나**라 앱에도 한 줄이다 → 쪼개지 않는다.
       값이 다른 것들은 브랜드가 **이름에 직접** `(ICE)할메가커피` 처럼 적어놨다. 그대로 둔다.

    ⚠️ 같은 이름이 `item_cd` 만 다르게 두 번 등록된 게 12쌍 있다(콜라보 탭 전용 사본, 값은 같다).
       브랜드가 그렇게 등록한 것이므로 **합치지 않는다.**

━━━ ② 홈페이지 — 보태기만 한다 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`https://www.mega-mgccoffee.com/menu/` 의 `<ul id="menu_list">` 는 비어 있고,
그 페이지 안의 `function menu(page)` 가 `menu.php` 를 부른다(추측한 주소가 아니다).
여기엔 **가격이 없고** 대신 `컵용량`·`설명`·`영문명`이 있다 → 이름이 맞는 것에만 채운다.

원산지 표기는 **앱에도 홈페이지에도 없다** → `origin_raw` 는 전부 비운다(빈칸이 가짜보다 낫다).
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "megamgccoffee.json")

BRAND = "메가MGC커피"
SLUG = "megamgccoffee"

API = "https://app.annhouse.co.kr/api/menu/general/list"          # APK classes2.dex
API_HDR = {"Content-Type": "application/json; charset=utf-8",
           "Accept": "application/json", "User-Agent": "okhttp/4.12.0"}

ROOT = "https://www.mega-mgccoffee.com"
MENU_PAGE = ROOT + "/menu/"
LIST_API = ROOT + "/menu/menu.php"           # /menu/ 안의 function menu(page) 가 부르는 주소

SOURCE = ("① 앱 APK(co.kr.waldlust.megacoffee, adb 로 폰에서 추출) classes2.dex 문자열에서 얻은 "
          "POST %s  body {\"store_cd\":\"\"} — 카테고리·메뉴·가격 정본. "
          "② 보강: 공식 홈페이지 %s 가 부르는 %s — 컵용량·설명·영문명만(가격 없음)"
          % (API, MENU_PAGE, LIST_API))
COLLECTED_AT = time.strftime("%Y-%m-%d")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": MENU_PAGE}
GAP = 0.8

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_TOP = re.compile(r"/menu/\?menu_category1=(\d+)&menu_category2=(\d+)\">\s*([^<]*?)\s*</a>")
RX_LAST = re.compile(r"board_page_last board_page_link' data-page='(\d+)'")
RX_ITEM = re.compile(r"(?s)<li>\s*<a class=\"inner_modal_open\">(.*?)</li>")
RX_LABEL = re.compile(r"cont_gallery_list_label\d\">\s*(.*?)\s*</div>")
RX_NAME = re.compile(r"(?s)cont_text_title\">\s*<div class=\"text text1\">\s*<b>(.*?)</b>")
RX_ENG = re.compile(r"(?s)cont_text_info\">\s*<div class=\"text text1\">\s*(.*?)\s*</div>")
RX_DESC = re.compile(r"(?s)<div class=\"text text2\">\s*(.*?)\s*</div>")
RX_MODAL = re.compile(r"(?s)<div class=\"inner_modal\">(.*)")
RX_INNER = re.compile(r"(?s)<div class=\"cont_text_inner\">\s*(.*?)</div>")

# 매칭용 정규화 — 앞머리 표식 `(ICE)`·`(할인)`·`(NEW)` 를 떼고 공백·괄호를 지운다
RX_PREFIX = re.compile(r"^\s*\((?:ICE|HOT|할인|NEW|공식)\)\s*", re.I)


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def blank(v):
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—", ":") else v


def key_of(name):
    return re.sub(r"[\s()]+", "", RX_PREFIX.sub("", name or "")).upper()


# ─────────────────────────────── ① 앱 API ───────────────────────────────
def app_menu():
    req = urllib.request.Request(API, data=json.dumps({"store_cd": ""}).encode(),
                                 headers=API_HDR, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=40))


# ─────────────────────────────── ② 홈페이지 ───────────────────────────────
def get(url):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    return RX_COMMENT.sub("", raw)          # 주석 먼저 걷어낸다 (죽은 메뉴·숨은 탭이 섞인다)


def parse_cards(html):
    rows = []
    for m in RX_ITEM.finditer(html):
        b = m.group(1)
        nm = RX_NAME.search(b)
        name = strip(nm.group(1)) if nm else ""
        if not name:
            continue
        lab = RX_LABEL.search(b)
        eng = RX_ENG.search(b)
        desc = RX_DESC.search(b)
        weight = None
        mo = RX_MODAL.search(b)
        for inner in RX_INNER.findall(mo.group(1) if mo else ""):
            t = strip(inner)
            if ("컵용량" in t or "중량" in t or "용량" in t) and ":" in t:
                weight = blank(t.split(":", 1)[1])
                break
        rows.append({"name": name,
                     "label": strip(lab.group(1)) if lab else None,
                     "eng": blank(strip(eng.group(1))) if eng else None,
                     "desc": blank(strip(desc.group(1))) if desc else None,
                     "weight": weight})
    return rows


def site_extra():
    """홈페이지 카드 → {정규화이름: [{label, weight, desc, eng}]}"""
    home = get(MENU_PAGE)
    tops, seen = [], set()
    for c1, c2, nm in RX_TOP.findall(home):
        nm = strip(nm)
        if nm and (c1, c2) not in seen:
            seen.add((c1, c2))
            tops.append((c1, c2, nm))
    out, n = {}, 0
    for c1, c2, nm in tops:
        p, last = 1, 1
        while p <= last:
            url = ("%s?page=%d&menu_category1=%s&menu_category2=%s&category=&list_checkbox_all=all"
                   % (LIST_API, p, c1, c2))
            html = get(url)
            if p == 1:
                m = RX_LAST.search(html)
                last = int(m.group(1)) if m else 1
            for r in parse_cards(html):
                out.setdefault(key_of(r["name"]), []).append(r)
                n += 1
            p += 1
            time.sleep(GAP)
        print("  홈페이지 %-6s 누적 %3d장" % (nm, n), flush=True)
    return out, n


# ─────────────────────────────── 본체 ───────────────────────────────
def main():
    print("① 앱 API — POST %s" % API)
    try:
        doc = app_menu()
    except Exception as e:
        print("🔴 앱 API 실패: %s — 파일을 쓰지 않는다" % e)
        return
    root = doc.get("all") or {}
    uppers = root.get("upper_ctg_list") or []
    if not uppers:
        print("🔴 카테고리 0개 — **응답 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return

    cats, items, order, placements = [], {}, [], 0
    for u in uppers:
        un = strip(u["upper_ctg_nm"])
        cats.append({"name": un, "parent": None, "ext_id": u.get("upper_ctg_cd")})
        for c in u.get("ctg_list") or []:
            cn = strip(c["ctg_nm"])
            path = "%s/%s" % (un, cn)
            cats.append({"name": cn, "parent": un, "ext_id": c.get("ctg_cd")})
            for i, it in enumerate(c.get("item_list") or []):
                cd = it["item_cd"]
                cur = items.get(cd)
                if cur is None:
                    price = it.get("price")
                    org = it.get("org_price")
                    cur = {"name": strip(it["item_nm"]),
                           "price": int(price) if str(price).isdigit() else None,
                           "price_source": "app",
                           "weight_raw": None, "origin_raw": None,
                           "allergy_raw": ", ".join(it.get("allergy_list") or []) or None,
                           "compose_raw": None,
                           "detail_url": None,
                           "image_url": it.get("img") or None,
                           "ext_id": cd,
                           "temperature": it.get("temperature") or None,
                           "org_price": int(org) if str(org).isdigit() else None,
                           "badge_raw": ", ".join(it.get("badge_list") or []) or None,
                           "sold_out": bool(it.get("sold_out")),
                           "eng_name": None,
                           "cats": []}
                    items[cd] = cur
                    order.append(cd)
                cur["cats"].append([path, i])
                placements += 1
        print("  %-8s %-4s %s" % (un, u.get("upper_ctg_cd"),
                                  " · ".join("%s(%s)%d" % (strip(c["ctg_nm"]), c.get("ctg_cd"),
                                                           len(c.get("item_list") or []))
                                             for c in u.get("ctg_list") or [])), flush=True)

    if not order:
        print("🔴 메뉴 0건 — 조용히 빈 JSON 을 쓰지 않는다")
        return

    # ─── ② 홈페이지에서 컵용량·설명·영문명만 보탠다 ───
    print("② 홈페이지 보강 — %s" % LIST_API)
    n_w = n_c = n_e = 0
    try:
        extra, n_card = site_extra()
    except Exception as e:
        extra, n_card = {}, 0
        print("  ⚠️ 홈페이지 보강 실패(앱 데이터는 그대로 쓴다): %s" % e)
    for cd in order:
        it = items[cd]
        got = extra.get(key_of(it["name"]))
        if not got:
            continue
        ws = [g["weight"] for g in got if g["weight"]]
        if ws:
            uniq = list(dict.fromkeys(ws))
            if len(uniq) == 1:
                it["weight_raw"] = uniq[0]
            else:   # HOT·ICE 컵이 다르면 배지를 붙여 **둘 다** 남긴다
                it["weight_raw"] = " / ".join(("%s %s" % (g["label"] or "", g["weight"])).strip()
                                              for g in got if g["weight"])
            n_w += 1
        ds = [g["desc"] for g in got if g["desc"]]
        if ds:
            it["compose_raw"] = list(dict.fromkeys(ds))[0]
            n_c += 1
        es = [g["eng"] for g in got if g["eng"]]
        if es:
            it["eng_name"] = list(dict.fromkeys(es))[0]
            n_e += 1

    # ─── 메뉴가 아닌 것 걸러내기 (지우기 전에 목록으로 출력) ───
    cat_names = {c["name"] for c in cats}
    removed, flagged, kept = [], [], []
    for cd in order:
        it = items[cd]
        nm = it["name"]
        if nm in cat_names:
            removed.append((nm, "카테고리 이름과 같다"))
            continue
        # ⚠️ 문장부호·길이는 **지우지 않고 표시만** 한다.
        #    여기는 앱 API 의 `item_nm` 필드라 홍보문구가 섞일 자리가 없다.
        #    `RIIZE ODYSSEY MEGA SMini Ver.` 는 마침표로 끝나지만 진짜 MD 상품이고,
        #    18자 넘는 것들도 전부 진짜 메뉴다(`ARIH 포스트바이오틱 에너지 드링크 오렌지아워`).
        if re.search(r"[.!?~]$", nm):
            flagged.append((nm, "문장부호로 끝난다 — 앱 item_nm 이라 남겼다"))
        elif len(nm) >= 18:
            flagged.append((nm, "18자 이상 — 앱 item_nm 이라 남겼다"))
        kept.append(it)

    out = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "price_note": "앱 `menu/general/list` 의 store_cd:\"\" 기준가 — 가맹점별로 다를 수 있다. "
                         "홈페이지에는 가격이 없다",
           "temperature_note": "HOT/ICE 는 앱의 `temperature` 한 칸(HOT·ICE·BOTH·NONE). "
                               "BOTH 는 값이 같아 앱에도 한 줄이라 쪼개지 않았다",
           "cats": cats, "menus": kept}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ─── 요약 — **만든 파일을 다시 읽어서** 센다 ───
    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    n_a = sum(1 for m in chk["menus"] if m.get("allergy_raw"))
    links = sum(len(m["cats"]) for m in chk["menus"])
    temps = {}
    for m in chk["menus"]:
        temps[m.get("temperature")] = temps.get(m.get("temperature"), 0) + 1
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  경로: **앱 API**(정본) + 홈페이지(컵용량·설명)")
    print("  알레르기 %d · 컵용량 %d · 설명 %d · 영문명 %d · 원산지 0 (앱·홈페이지 어디에도 표기 없음)"
          % (n_a, n_w, n_c, n_e))
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  temperature: %s" % " · ".join("%s %d" % (k, v) for k, v in temps.items()))
    zero = [m["name"] for m in chk["menus"] if m.get("price") == 0]
    if zero:
        # 앱에 `price:0` 으로 등록된 항목(배너성 카드일 수 있다). 지우지 않고 **눈에 보이게** 알린다.
        print("  ⚠️ 가격이 0원인 항목 %d개 — 앱 등록값 그대로다: %s" % (len(zero), " · ".join(zero)))
    if removed:
        print("  ⛔ 지운 줄 %d개:" % len(removed))
        for nm, why in removed:
            print("     · %-40s %s" % (nm[:40], why))
    else:
        print("  ⛔ 지운 줄 없음")
    if flagged:
        print("  ⚠️ 규칙에 걸렸으나 **남긴** 이름 %d개 — 눈으로 볼 것:" % len(flagged))
        for nm, why in flagged:
            print("     · %-44s %s" % (nm[:44], why))
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
