# -*- coding: utf-8 -*-
"""
스타벅스(slug: starbucks) 메뉴판 수집 → data/brand_menu_list/starbucks.json 한 장만 만든다.
DB 는 건드리지 않는다 (import 도 하지 않는다).

────────────────────────────────────────────────────────────────────────
■ 어떻게 뚫었나 — 다음 사람이 재현하도록 남긴다 (2026-07-28)

① APK (com.starbucks.co, 폰에서 pull)
   D:\\Android\\Sdk\\platform-tools\\adb.exe -s 172.30.1.59:44737 shell pm path com.starbucks.co
   → /data/app/~~A_RGuc2B6s1stFYiIKDTxQ==/com.starbucks.co-4SxyBz_lwHqOsCIKb-zpqA==/base.apk (107MB)

   APK 에서 나온 주소 (res/8GD.xml = network-security-config, resources.arsc):
       www.istarbucks.co.kr / starbucks.co.kr / www.starbucks.co.kr
       (istarbucks.co.kr 는 www.starbucks.co.kr 로 301 리다이렉트된다 — 같은 사이트다)
   설빙처럼 "그냥 열면 되는 WEBVIEW_URL" 은 **없었다.**
   dex 안의 .do 엔드포인트는 전부 사이렌오더/결제용이라 로그인이 필요하다:
       /wholecake/skuList.do  /gift/prodList.do  /customSkuList.do  /addOptionSkuList.do ...
   → 메뉴판 용도로는 못 쓴다. 그래서 ② 홈페이지로 넘어갔다.

② 홈페이지 (여기가 정답 — 로그인·크롬 불필요, urllib 로 끝난다)
   목록 페이지        https://www.starbucks.co.kr/menu/drink_list.do   (음료)
                      https://www.starbucks.co.kr/menu/food_list.do    (푸드)
   위 페이지들은 껍데기고, 상품은 JS 가 **정적 JSON** 을 받아서 그린다:
       https://www.starbucks.co.kr/upload/json/menu/{CATE_CD}.js   ← {"list":[...]}
   CATE_CD 는 목록 페이지 안 getCateCodeCng() 에 박혀 있다 (아래 _cate_codes 가 그걸 파싱한다).
   테마 탭은 배너 <img data-sbseq="W0000563"> 의 값이 그대로 CATE_CD 다.
   상세(알레르기·용량)는 상세페이지에 통째로 인라인돼 있다:
       /menu/drink_view.do?product_cd=  →  var drinkData = { view: remapView({...}) }
       /menu/food_view.do?product_cd=   →  var foodData  = { view: remapView({...}) }
   ※ POST /menu/productListAjax.do 도 살아있지만 위 정적 .js 로 충분하다.

■ 가격
   스타벅스는 홈페이지에 가격을 걸지 않는다. 목록 JSON 의 price, 상세의 PRICE 가 **전부 빈 문자열**이다.
   → price=null 로 둔다. 가격은 나중에 네이버 플레이스로 따로 채운다. (이번 범위 아님)

■ 담지 않은 것
   /menu/product_list.do (머그·텀블러·원두패키지 등 MD 상품) 와 /menu/card_list.do (카드) 는
   먹는 메뉴가 아니라서 뺐다. 필요해지면 아래 PAGES 에 한 줄 추가하면 그대로 붙는다.
       상품: W0000030 머그 / W0000164 글라스 / W0000031 플라스틱 텀블러 / W0000035 스테인리스 텀블러
             W0000067 보온병 / W0000068 액세서리 / W0000421 선물세트 / W0000034 커피 용품
             W0000184 패키지 티(티바나) / W0000431 시럽
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import html
import json
import os
import re
import time
import urllib.request

BASE = "https://www.starbucks.co.kr"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": BASE + "/menu/drink_list.do",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "starbucks.json")

# 사이트의 MENU 네비 순서 그대로. (탭 이름, 목록페이지, 상세페이지)
PAGES = [
    ("음료", "/menu/drink_list.do", "/menu/drink_view.do"),
    ("푸드", "/menu/food_list.do", "/menu/food_view.do"),
]

SLEEP = 0.6      # 상세 320여 장을 연속으로 받는다. 더 줄이면 중간에 막힌다.


def get(path, tries=4):
    """상세를 300개 넘게 받으면 중간에 WinError 10060(연결 끊김)이 난다.
    사이트가 잠깐 막는 것이라 기다렸다 다시 부르면 그냥 된다. 병렬로 두드리지 말 것."""
    url = BASE + path if path.startswith("/") else path
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(5 * (i + 1))
    raise last


def _cate_codes(page):
    """목록 페이지에서 «화면에 보이는 카테고리» 를 순서 그대로 뽑는다.
    반환: [(표시명, CATE_CD, 종류)]  종류 = 'cate' | 'theme'
    """
    # ① 체크박스 라벨 = 화면 순서
    labels = []
    for m in re.finditer(r'id="(product_[A-Za-z0-9_]+)"[^>]*>\s*<label for="\1">([^<]+)</label>', page):
        labels.append((m.group(1), html.unescape(m.group(2)).strip()))

    # ② getCateCodeCng() 안의 id → CATE_CD
    seg = page[page.find("function getCateCodeCng"):][:4000]
    codes = dict(re.findall(r'tmp_cate\s*==\s*"(product_[A-Za-z0-9_]+)"\)\s*\{\s*result\s*=\s*"([A-Za-z0-9]+)"', seg))

    out = []
    for pid, name in labels:
        cd = codes.get(pid, "")
        if not cd or cd == "0":      # product_all(전체 상품보기) 은 탭이 아니라 필터다
            continue
        out.append((name, cd, "cate"))

    # ③ 테마 탭 배너 — data-sbseq 가 그대로 CATE_CD
    for m in re.finditer(r'<img[^>]*data-sbseq="([A-Za-z0-9]+)"[^>]*>', page):
        tag = m.group(0)
        cd = m.group(1)
        alt = re.search(r'alt="([^"]*)"', tag)
        name = html.unescape(alt.group(1)).strip() if alt else cd
        if cd and cd not in [c for _, c, _ in out]:
            out.append((name, cd, "theme"))
    return out


def _cate_json(cate_cd):
    txt = get("/upload/json/menu/%s.js" % cate_cd)
    return json.loads(txt).get("list", [])


_DETAIL_CACHE = {}
DETAIL_FAIL = []


def _detail(view_path, product_cd):
    """상세페이지에 인라인된 remapView({...}) 를 그대로 뜯는다."""
    key = (view_path, product_cd)
    if key in _DETAIL_CACHE:
        return _DETAIL_CACHE[key]
    v = {}
    for attempt in range(3):          # 간헐적 WinError 10060 이 난다 — 재시도한다
        try:
            t = get("%s?product_cd=%s" % (view_path, product_cd))
            i = t.find("remapView(")
            if i < 0:
                break
            i += len("remapView(")
            depth, j = 0, i
            while j < len(t):
                if t[j] == "{":
                    depth += 1
                elif t[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            v = json.loads(t[i:j + 1])
            break
        except Exception as e:
            if attempt == 2:
                print("   ! 상세 실패(3회) %s : %s" % (product_cd, e))
                DETAIL_FAIL.append(product_cd)
            else:
                time.sleep(2 + attempt * 3)
    _DETAIL_CACHE[key] = v
    return v


def _blank(v):
    v = (v or "").strip()
    return v or None


def main():
    cats = []          # {"name","parent","ext_id"}
    cat_paths = set()
    menus = {}         # product_CD -> menu dict
    order = []         # product_CD 등장 순서
    dropped = []
    flagged = []

    for top_name, list_path, view_path in PAGES:
        print("== %s (%s)" % (top_name, list_path))
        page = get(list_path)
        cats.append({"name": top_name, "parent": None, "ext_id": None})
        cat_paths.add(top_name)

        subs = _cate_codes(page)
        print("   카테고리 %d개: %s" % (len(subs), " · ".join(n for n, _, _ in subs)))

        top_seq = 0                      # 상위 탭 안에서의 자리
        seen_in_top = set()

        for sub_name, cate_cd, kind in subs:
            path = "%s/%s" % (top_name, sub_name)
            if path in cat_paths:
                continue
            cats.append({"name": sub_name, "parent": top_name, "ext_id": cate_cd})
            cat_paths.add(path)

            try:
                rows = _cate_json(cate_cd)
            except Exception as e:
                print("   ! %s(%s) JSON 실패: %s" % (sub_name, cate_cd, e))
                continue
            time.sleep(SLEEP)

            sub_seq = 0
            for r in rows:
                name = (r.get("product_NM") or "").strip()
                pcd = (r.get("product_CD") or "").strip()
                if not name or not pcd:
                    dropped.append((name or "(이름없음)", "product_NM/product_CD 비었음"))
                    continue

                # 메뉴가 아닌 것 거르기
                if re.search(r"[.!?…]$", name) or name in ("상품명", "정상가", "가격"):
                    dropped.append((name, "문장부호로 끝나거나 UI 문자열"))
                    continue
                # ⚠️ «카테고리 이름과 같으면 버린다» 는 규칙은 스타벅스에 쓰면 안 된다.
                #    `브루드 커피`·`에스프레소` 는 같은 이름의 **실제 상품**이 따로 있다(product_CD 있음).
                #    상품 JSON 에서 온 행은 전부 진짜 상품이라 이름만으로 버리지 않고 표시만 한다.
                if name == sub_name or name == top_name:
                    flagged.append((name, "카테고리와 같은 이름이지만 실제 상품(product_CD %s)" % pcd))
                # 길다고 버리지는 않는다 — 스타벅스 음료명은 원래 길다. 눈으로만 확인.
                if len(name) >= 18:
                    flagged.append((name, "%d자" % len(name)))

                if pcd not in menus:
                    v = _detail(view_path, pcd)
                    time.sleep(SLEEP)
                    std = (v.get("STANDARD") or "").strip()
                    unit = (v.get("UNIT") or "").strip()
                    weight = "%s%s" % (std, unit) if (std and std != "0" and unit) else None
                    allergy = (v.get("ALLERGY") or "").strip()
                    allergy = allergy.replace(",", " /").replace("@", " / ") if allergy else None
                    img = (r.get("img_UPLOAD_PATH") or "") + (r.get("file_PATH") or "")
                    menus[pcd] = {
                        "name": name,
                        "price": None,                 # 스타벅스는 홈페이지에 가격이 없다
                        "price_source": None,
                        "weight_raw": weight,
                        "origin_raw": None,            # 사이트에 원산지 표기 없음
                        "allergy_raw": allergy,
                        "compose_raw": _blank(v.get("CONTENT") or r.get("content")),
                        "detail_url": "%s%s?product_cd=%s" % (BASE, view_path, pcd),
                        "image_url": img or None,
                        "ext_id": pcd,
                        "cats": [],
                    }
                    order.append(pcd)

                if pcd not in seen_in_top:
                    menus[pcd]["cats"].append([top_name, top_seq])
                    seen_in_top.add(pcd)
                    top_seq += 1
                menus[pcd]["cats"].append([path, sub_seq])
                sub_seq += 1

            print("   - %-22s %-10s %3d개%s" % (sub_name, cate_cd, sub_seq, "  (테마)" if kind == "theme" else ""))

    items = [menus[p] for p in order]
    if not items:
        print("메뉴 0개 — 파일을 저장하지 않는다.")
        return 1

    doc = {
        "brand": "스타벅스",
        "slug": "starbucks",
        "source": ("홈페이지 www.starbucks.co.kr — /menu/drink_list.do·/menu/food_list.do 의 "
                   "getCateCodeCng() 에서 CATE_CD 를 뽑아 /upload/json/menu/{CATE_CD}.js 를 받고, "
                   "알레르기·용량은 /menu/{drink|food}_view.do?product_cd= 상세페이지에 인라인된 "
                   "remapView({...}) 에서 읽었다. urllib 만 사용(로그인·브라우저 불필요). "
                   "APK(com.starbucks.co)에서는 www.istarbucks.co.kr 도메인만 나왔고 "
                   "메뉴 API 는 전부 사이렌오더용이라 로그인이 필요해 쓰지 않았다."),
        "collected_at": time.strftime("%Y-%m-%d"),
        "cats": cats,
        "menus": items,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    sub_n = sum(1 for c in cats if c["parent"])
    priced = sum(1 for m in items if m["price"])
    print()
    print("카테고리 %d개(상위 %d · 하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (len(cats), len(cats) - sub_n, sub_n, len(items), priced))
    print("연결(중복 진열 포함) %d건" % sum(len(m["cats"]) for m in items))
    print("용량 있는 것 %d · 알레르기 있는 것 %d · 설명 있는 것 %d"
          % (sum(1 for m in items if m["weight_raw"]),
             sum(1 for m in items if m["allergy_raw"]),
             sum(1 for m in items if m["compose_raw"])))
    print("→", OUT)

    if dropped:
        print("\n[버린 줄 %d개]" % len(dropped))
        for n, why in dropped:
            print("  -", n, "|", why)
    else:
        print("\n[버린 줄 없음]")

    if flagged:
        print("\n[규칙에 걸렸지만 **버리지 않은** 진짜 메뉴 %d개]" % len(flagged))
        for n, why in flagged:
            print("  ·", n, "|", why)

    if DETAIL_FAIL:
        print("\n[상세(용량·알레르기) 못 받은 %d개 — 이름·카테고리는 정상]" % len(DETAIL_FAIL))
        for p in DETAIL_FAIL:
            print("  ·", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
