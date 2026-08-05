# -*- coding: utf-8 -*-
"""
푸라닭치킨(slug=puradakchicken) 전용 메뉴판 수집기 — JSON 만 만든다. DB 는 건드리지 않는다.

## 어떻게 뚫었나 (2026-07-28)
- `https://puradakchicken.com/` 는 2KB 껍데기. canonical 이 `/main` 이라 `/main` 을 먼저 받았다.
- `/main` 의 네비게이션은 전부 `javascript:linkXXXX()` 라 href 가 없다.
  → `<script src="../common/js/link.js">` 를 받아 함수 본문을 읽었더니 실제 주소가 나왔다:
        link0200/0201 = menu/product.asp?sermode=0   (치킨 메뉴)
        link0202      = menu/product.asp?sermode=1   (사이드메뉴)
        link0203/0204 = sermode=2(푸레스트) · 3(P-피자)  ← 현재 0건이고 네비에서도 빠져 있다
        link0207      = menu/menuInfo.asp            (메뉴별 정보 = 알레르기/원산지 게시판)
- SPA 가 아니라 **평범한 ASP 서버렌더**다. 브라우저 없이 urllib 로 전부 읽힌다.
- 하위 카테고리는 목록 페이지의 `div.listTab` 에 `?sermode=0&sermode2=N` 으로 들어 있다.
- 가격은 목록에 없고 **상세(`menu/view.asp?idx=N`)의 `p.price`** 에만 있다.
  상세에 «표시된 가격은 권장 판매가이며 판매 가격은 매장별로 상이할 수 있습니다» → 배달가 아님(홀/권장가).
- 원산지는 `menu/menuInfo.asp` 게시판의 **JPG 포스터**(가맹점용 idx=19339 / 직영점용 idx=19338).
  텍스트가 아니라 이미지라 사람이 눈으로 읽어 아래 ORIGIN_NOTE 에 원문 그대로 옮겼다(자동 파싱 아님).

## 메뉴가 아닌 것 (여기서 걸러진다)
목록 li 안의 `img.best`(alt=NEW메뉴/베스트메뉴) · `img.hot`(alt=약간 매운맛/아주 매운맛) 은 **배지 이미지**다.
기존 DB 14~28행이 홍보문구·배지·카테고리명으로 채워진 원인이 이것들과 상세 본문(`p.photo_txt`)이었다.
이 스크립트는 `p.title.one`(목록) / `div.pro_name p.title`(상세) **한 곳만** 메뉴명으로 본다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://puradakchicken.com"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
GAP = 1.6  # 요청 간격(초)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "puradakchicken.json")

# link.js 에서 읽어낸 상위 카테고리. sermode 값과 목록 페이지 p.nTit 를 그대로 쓴다.
# 2·3(푸레스트·P-피자)은 상품 0건 + 네비게이션에서도 빠져 있어 담지 않는다(아래에서 실제로 재확인한다).
TOP_CATS = [(0, "치킨 메뉴"), (1, "사이드메뉴")]
PROBE_EMPTY = [2, 3]  # 매번 다시 확인 — 상품이 생기면 경고를 띄운다

# 원산지 — menu/menuInfo.asp 「푸라닭 치킨 원산지 포스터_가맹점용」(JPG, VER. 2604) 원문
ORIGIN_NOTE = (
    "원산지 표시판 [VER. 2604] (가맹점용)\n"
    "푸라닭 치킨의 모든 치킨 메뉴는 100% 국내산 닭고기만을 사용합니다.\n"
    "품목 | 원산지 | 메뉴\n"
    "닭고기 | 국내산 | 치킨(뼈/순(다리)살/윙콤보)\n"
    "닭고기 | 국내산 | 텐더 치바로우\n"
    "닭고기 | 국내산 | 지파이\n"
    "닭고기 | 태국산 | 3색 닭꼬치\n"
    "닭발 | 국내산 | 후라잉 닭발, 매콤 국물닭발\n"
    "돼지고기 | 국내산 | 수제 킬바사 소시지\n"
    "쇠고기 | 호주산, 국내산 | 수제 킬바사 소시지\n"
    "오징어 | 페루산 | 후라잉 진미채\n"
    "쌀 | 국내산 | 즉석밥 (즉석조리식품)\n"
    "다랑어 | 인도네시아산 | 타코볼 (가쓰오부시)\n"
    "\n"
    "※ 직영점용 포스터(idx=19338)는 2행만 다르다 — 「닭고기 | 국내산 | 나폴리 파스타」."
)
ORIGIN_SRC = BASE + "/menu/menuInfo.asp?mode=view&idx=19339&BBSCode=11"

# 알레르기 — 같은 게시판의 JPG 매트릭스(품목 × 20개 알레르겐 · 점 표시).
# 값을 채우지 않는다. 이유 둘:
#  ① 텍스트가 아니라 **이미지**라 20열짜리 점을 눈으로 옮겨 적어야 하고, 한 칸만 틀려도 가짜 정보가 된다
#  ② 행 이름이 「씬 후라이드 (뼈/순(다리)살/윙콤보)」처럼 **3개 메뉴를 묶은 이름**이라
#     우리 메뉴명(`씬 후라이드` · `순(다리)살 씬 후라이드` · `씬 후라이드 윙콤보`)과 정확히 맞지 않는다
# → 근거 없는 매핑 금지. 출처만 남긴다.
ALLERGY_NOTE = (
    "알레르기 유발 물질 정보는 이미지 표(JPG)로만 공개된다 — 텍스트 없음. 자동 판독하지 않았다.\n"
    "가맹점용 VER.260625B : " + BASE + "/menu/menuInfo.asp?mode=view&idx=44950&BBSCode=11\n"
    "가맹점용(딥블랙) VER.260625C : " + BASE + "/menu/menuInfo.asp?mode=view&idx=45501&BBSCode=11\n"
    "직영점용 VER.260625A : " + BASE + "/menu/menuInfo.asp?mode=view&idx=44949&BBSCode=11\n"
    "※ 표의 행 이름이 「메뉴명 (뼈/순(다리)살/윙콤보)」로 3개를 묶어 놓아 메뉴명과 1:1 로 맞지 않는다."
)

# 포스터 행 → 메뉴 매핑. **표에 이름이 그대로 적힌 것만** 넣는다(근거 없는 매핑 금지).
# 치킨 카테고리 전체는 표 1행(치킨(뼈/순(다리)살/윙콤보)) + 상단 문구(모든 치킨 메뉴 100% 국내산)가 근거다.
ORIGIN_CHICKEN = "닭고기 : 국내산"
ORIGIN_BY_NAME = {
    "지파이": "닭고기 : 국내산",
    "타코볼 (4구)": "다랑어 : 인도네시아산 (가쓰오부시)",
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
    time.sleep(GAP)
    return b if binary else b.decode("utf-8", "replace")


def strip_comments(h):
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


def txt(s):
    """태그 제거 + 엔티티 해제 + 공백 정리. innerText 가 아니라 textContent 기준."""
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()


def money(s):
    m = re.search(r"([\d,]{3,})\s*(?:<span>)?\s*원", s)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


# ---------- 목록 ----------
def list_page(sermode, sermode2=None):
    u = "%s/menu/product.asp?sermode=%d" % (BASE, sermode)
    if sermode2 is not None:
        u += "&sermode2=%d" % sermode2
    h = strip_comments(get(u))
    ntit = re.search(r'class="nTit">(.*?)</p>', h, re.S)
    ntit = txt(ntit.group(1)) if ntit else None
    subs = []
    tab = re.search(r'<div class="listTab">(.*?)</div>', h, re.S)
    if tab:
        for href, label in re.findall(
            r'<a href="\s*/menu/product\.asp\?sermode=\d+(?:&sermode2=(\d+))?"\s*><span>(.*?)</span>',
            tab.group(1), re.S):
            if href == "":
                continue  # 「전체」 탭 — 하위 카테고리가 아니다
            subs.append((int(href), txt(label)))
    items = []
    # 🔴 상세 주소는 조립하지 않는다 — 목록의 href 를 **그대로** 쓴다.
    #    href 에는 그 상품이 속한 sermode 가 들어 있고, sermode 를 0 으로 고정해 부르면
    #    사이드메뉴(sermode=1) 상세가 «제목 빈칸 · 가격 0원» 으로 돌아온다(실제로 겪음).
    for href, li in re.findall(r"<li>\s*<a href=\"(view\.asp\?[^\"]+)\">(.*?)</li>", h, re.S):
        idx = re.search(r"idx=(\d+)", href)
        name = re.search(r'<p class="title one">(.*?)</p>', li, re.S)
        eng = re.search(r'<p class="txt">(.*?)</p>', li, re.S)
        img = re.search(r'<img src="([^"]+)" class="bg_thumb"', li)
        if not name:
            continue
        items.append({
            "name": txt(name.group(1)),
            "eng": txt(eng.group(1)) if eng else None,
            "idx": idx.group(1) if idx else None,
            "url": urllib.parse.urljoin(BASE + "/menu/", unescape(href)),
            "img": urllib.parse.urljoin(BASE, img.group(1)) if img else None,
        })
    return u, ntit, subs, items


# ---------- 상세 ----------
def detail(u):
    h = strip_comments(get(u))
    box = re.search(r'<div class="pro_name">(.*?)</div>\s*</div>', h, re.S)
    seg = box.group(1) if box else h
    name = re.search(r'<p class="title">(.*?)</p>', seg, re.S)
    price = re.search(r'<p class="price">(.*?)</p>', seg, re.S)
    body = re.search(r'<p class="photo_txt">(.*?)</p>', h, re.S)
    body = txt(body.group(1)) if body else ""
    # 중량 — 상세에 g/kg 표기가 있으면 원문 그대로. 없으면 null.
    wt = re.search(r"(중량[^<\n]{0,30}|[\d,.]+\s*(?:g|kg|ml|L)\b)", body)
    return {
        "url": u,
        "name": txt(name.group(1)) if name else None,
        "price": money(price.group(1)) if price else None,
        "weight_raw": wt.group(1).strip() if wt else None,
    }


# ---------- 문장 걸러내기 ----------
SENT_END = ("?", "!", ".", "다", "요", "니다")
BADGES = {"NEW메뉴", "베스트메뉴", "약간 매운맛", "아주 매운맛"}


def looks_like_sentence(n, cat_names, has_idx):
    """⚠️ 상세(view.asp?idx=) 가 달린 항목은 **진짜 상품**이라 길이·카테고리 규칙으로 죽이지 않는다.
    실제로 「반.반.반 플래터」가 «카테고리 이름과 동일» 로 걸려 사라질 뻔했다 — 같은 이름의
    하위 카테고리와 상품이 둘 다 있는 브랜드다. 대신 걸릴 뻔한 것을 keep 사유로 출력한다."""
    if n in BADGES:
        return "배지 이미지 alt", True
    hit = None
    if n in cat_names:
        hit = "카테고리 이름과 동일"
    elif len(n) >= 18:
        hit = "18자 이상"
    elif n.endswith(("?", "!", ".")):
        hit = "문장부호로 끝남"
    if hit and has_idx:
        return hit + " → 상세페이지가 있어 **살림**", False
    return (hit, True) if hit else (None, False)


def main():
    cats, menus, dropped, kept, warn = [], {}, [], [], []
    cat_names = set()

    for sermode, _ in TOP_CATS:
        u, ntit, subs, items = list_page(sermode)
        top = ntit
        cat_names.add(top)
        cats.append({"name": top, "parent": None, "ext_id": "sermode=%d" % sermode})
        print("[cat] %s  하위 %d  기본화면 %d건" % (top, len(subs), len(items)))

        if not subs:
            groups = [(top, items, u)]
        else:
            groups = []
            for s2, label in subs:
                cat_names.add(label)
                cats.append({"name": label, "parent": top,
                             "ext_id": "sermode=%d&sermode2=%d" % (sermode, s2)})
                su, _, _, sitems = list_page(sermode, s2)
                print("   [sub] %s  %d건" % (label, len(sitems)))
                groups.append(("%s/%s" % (top, label), sitems, su))

        for path, items, src in groups:
            pos = 0
            for it in items:
                n = it["name"]
                why, drop = looks_like_sentence(n, cat_names, bool(it["idx"]))
                if drop:
                    dropped.append((path, n, why))
                    continue
                if why:
                    kept.append((path, n, why))
                m = menus.setdefault(n, {
                    "name": n, "price": None, "price_source": "official",
                    "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": it["url"], "image_url": it["img"], "ext_id": it["idx"],
                    "cats": [],
                })
                m["cats"].append([path, pos])
                if not m["image_url"]:
                    m["image_url"] = it["img"]
                pos += 1

    # 안 담기로 한 카테고리에 상품이 생겼는지 매번 확인
    for sm in PROBE_EMPTY:
        _, ntit, _, items = list_page(sm)
        if items:
            warn.append("sermode=%d (%s) 에 상품 %d건이 생겼다 — 카테고리를 추가할 것"
                        % (sm, ntit, len(items)))
        else:
            print("[skip] sermode=%d (%s) 0건 — 담지 않음" % (sm, ntit))

    # 상세에서 가격
    print("\n[detail] %d건" % len(menus))
    for n, m in menus.items():
        if not m["detail_url"]:
            continue
        d = detail(m["detail_url"])
        m["price"] = d["price"]
        m["weight_raw"] = d["weight_raw"]
        if d["price"] == 0:
            m["price"] = None  # 사이트가 «0 원» 으로 주는 것은 «미공개» 다
        if d["name"] and d["name"] != n:
            warn.append("목록명 «%s» ≠ 상세명 «%s» (idx=%s)" % (n, d["name"], m["ext_id"]))
        print("   %-28s %s" % (n, d["price"] if d["price"] else "가격없음"))

    # 원산지 — 포스터에 이름이 그대로 적힌 것 + 「모든 치킨 메뉴 100% 국내산」 문구가 덮는 치킨 카테고리
    for n, m in menus.items():
        if n in ORIGIN_BY_NAME:
            m["origin_raw"] = ORIGIN_BY_NAME[n]
        elif any(c[0].startswith("치킨 메뉴") for c in m["cats"]):
            m["origin_raw"] = ORIGIN_CHICKEN

    if kept:
        print("\n[규칙에 걸렸지만 살린 줄] %d개" % len(kept))
        for path, n, why in kept:
            print("   %-22s %-24s %s" % (path, n, why))
    if dropped:
        print("\n[걸러낸 줄] %d개 — 지우기 전에 확인할 것" % len(dropped))
        for path, n, why in dropped:
            print("   %-22s %-24s %s" % (path, n, why))
    else:
        print("\n[걸러낸 줄] 없음")
    for w in warn:
        print("⚠️ " + w)

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다.")
        return 1

    out = {
        "brand": "푸라닭치킨",
        "slug": "puradakchicken",
        "source": BASE + "/menu/product.asp?sermode=0",
        "collected_at": "2026-07-28",
        "price_note": "상세페이지 표기 — 「표시된 가격은 권장 판매가이며 판매 가격은 매장별로 "
                      "상이할 수 있습니다」. 배달가 아님(홀·포장 공통 권장가).",
        "origin_note": ORIGIN_NOTE,
        "origin_source": ORIGIN_SRC,
        "allergy_note": ALLERGY_NOTE,
        "cats": cats,
        "menus": [menus[k] for k in menus],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n저장: %s  (카테고리 %d · 메뉴 %d · 가격 %d)"
          % (OUT, len(cats), len(out["menus"]),
             sum(1 for m in out["menus"] if m["price"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
