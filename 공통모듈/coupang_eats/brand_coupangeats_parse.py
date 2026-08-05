# -*- coding: utf-8 -*-
"""쿠팡이츠 화면 **원본**(`_ce_raw/<slug>.tsv`)에서 메뉴·가격을 뽑는다. 2026-07-31 신설

    python scripts/brand_coupangeats_parse.py <slug>
    → data/brand_menu_list/<slug>_delivery.json

🔴 수집과 가공을 나눈 이유 (대표 지시 2026-07-31)
   전엔 스크롤하면서 그 자리에서 걸렀다 → **규칙이 틀리면 8분을 다시 긁어야 했다.**
   원본이 남아 있으면 여기만 고쳐 몇 번이든 다시 돌린다. 폰도 에뮬도 필요 없다.

읽는 법 — 원본 한 줄은 `화면번호 \t y \t x \t 글자`
   메뉴 한 칸은 이렇게 그려진다(왼쪽 열, 위에서 아래로):
       아침&후레쉬우유 (930ml)      ← 이름
       4,400원                     ← 가격
       목장의 신선함이 …            ← 설명
       품절임박 | 잔여 2개          ← 안내
   그래서 **가격 줄을 찾고 같은 왼쪽 열에서 바로 위 줄**을 이름으로 잡는다.

⛔ 카테고리 제목을 메뉴로 세지 않는다 — 「빙수/아이스크림」·「커피/음료#우유」 처럼
   `/` 나 `#` 가 든 줄이다(2026-07-31 파리바게트에서 8줄이 섞여 들어왔다).
🔴 가격은 배달가다 — 지점마다 다르고 매장에서 사면 더 싸다. note 에 적는다.
⛔ DB 에 쓰지 않는다. JSON 만 만든다.
"""
import io
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
RAW = os.path.join(OUT, "_ce_raw")

RX_PRICE = re.compile(r'^([\d,]{3,})\s*원$')
LEFT = 120                      # 왼쪽 열 — 이름·가격이 여기서 시작한다
# 메뉴명이 아닌 것 — UI·안내·리뷰 줄
JUNK = re.compile(r"품절|잔여|리뷰|와우|배달비|즉시할인|최소주문|가입|쿠폰|자세히|원산지|"
                  r"^\d+\s*/\s*\d+$|^\d+위$|^[\d,]+원|^\d+%|^ㆍ$|인기메뉴|내 메뉴|"
                  r"도착까지|배달\s*\d|포장\s*\d|^\d+\.\d+\(|^광고$|추천해요|맛집")

def is_cat_title(name):
    """카테고리 제목인가 — 「파이/패스트리」·「커피/음료」·「디저트#마카롱」.

    🔴 `/` 만 보고 자르면 안 된다. 「크림빵(연유/초코/생크림)」·「바삭 몬테크리스토 (1/2)」
       처럼 **괄호 안의 `/`** 는 메뉴 이름의 일부다(2026-07-31 뚜레쥬르에서 4개를 잘못 뺐다).
       그래서 **괄호를 지우고** 남은 자리에 구분자가 있을 때만 카테고리로 본다.
    """
    # 대괄호도 괄호와 같다 — 「비빔밥 + 유부주머니탕 [스팸마요/ 치킨텐더 선택]」(2026-07-31 얌샘)
    outside = re.sub(r"[\(（\[][^)）\]]*[\)）\]]", "", name or "")
    # 🔴 「치즈김밥1/2+참치김밥1/2」 의 `1/2` 는 **분수**다 — 얌샘 반반김밥 28개를 잘못 뺐다
    #    (2026-07-31). 양옆이 숫자인 `/` 는 구분자가 아니다.
    outside = re.sub(r"\d\s*/\s*\d", "", outside)
    return bool(re.search(r"[#／/]", outside))


def screens(fp):
    """원본을 화면 단위로 되돌린다."""
    cur, n = [], None
    for ln in io.open(fp, encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        s, y, x, t = int(p[0]), int(p[1]), int(p[2]), "\t".join(p[3:])
        if n is not None and s != n:
            yield cur
            cur = []
        n = s
        cur.append((y, x, t))
    if cur:
        yield cur


# 가게 이름 자리에 끼어드는 안내 문구 — 「오픈 준비 중」을 가게명으로 읽었다(2026-07-31 폴바셋)
NOT_SHOP = re.compile(r"오픈|준비\s*중|영업|휴무|마감|배달|포장|리뷰|쿠폰|할인|km|분$")


def shop_of(fp):
    """가게 이름 — 첫 화면 위쪽, 왼쪽 열이 아닌 자리에 온다.

    🔴 «…점» 으로 끝나는 것을 먼저 찾는다. 그 자리에 「오픈 준비 중」 같은 **안내 문구**가
       먼저 걸려 가게명으로 저장된 적이 있다(2026-07-31 폴바셋 교보문고 합정점).
    """
    first = next(screens(fp), [])
    cand = [t for y, x, t in first
            if x >= 250 and 3 < len(t) < 30 and not JUNK.search(t)
            and not RX_PRICE.match(t) and not NOT_SHOP.search(t) and "원산지" not in t]
    for t in cand:
        if t.endswith("점"):
            return t
    return cand[0] if cand else ""


def harvest(fp):
    """가격 줄을 찾고 **같은 왼쪽 열에서 바로 위** 줄을 이름으로 잡는다."""
    bag, order, skipped = {}, [], []
    for rows in screens(fp):
        for i, (y, x, t) in enumerate(rows):
            m = RX_PRICE.match(t)
            if not m:
                continue
            price = int(m.group(1).replace(",", ""))
            name = None
            # 🔴 이름은 **같은 세로열**에서 바로 위 줄이다. 세로 리스트는 x≈36 한 열이지만,
            #    역전우동처럼 **가로 그리드**(한 줄에 여러 메뉴)면 x=252·468·684 열도 있다.
            #    x>120 만 보던 옛 코드는 그리드의 첫 열만 잡아 4개로 끝났다(2026-07-31).
            for j in range(i - 1, max(-1, i - 10), -1):
                yy, xx, tt = rows[j]
                if abs(xx - x) > 90:            # 다른 열이면 건너뛴다
                    continue
                if RX_PRICE.match(tt) or JUNK.search(tt) or not (2 <= len(tt) <= 40):
                    continue
                name = tt
                break
            if not name or name in bag:
                continue
            if is_cat_title(name):              # 카테고리 제목은 메뉴가 아니다
                skipped.append(name)
                continue
            bag[name] = price
            order.append(name)
    return bag, order, skipped


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("사용법: python scripts/brand_coupangeats_parse.py <slug>")
    slug = args[0]
    fp = os.path.join(RAW, "%s.tsv" % slug)
    if not os.path.exists(fp):
        print("🔴 원본이 없다: %s — 먼저 brand_coupangeats.py 를 돌린다." % fp)
        return 1

    shop = shop_of(fp)
    bag, order, skipped = harvest(fp)
    if not order:
        print("🔴 0개 — 원본이 메뉴 화면이 맞는지 확인할 것.")
        return 1

    doc = {"brand_slug": slug, "shop": shop, "source": "쿠팡이츠 앱(화면 원본 재가공)",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": ("쿠팡이츠 배달가(%s 기준). 배달이라 지점마다 다를 수 있고, "
                    "실제 매장에서 사면 더 저렴하다. 가격은 날마다 달라진다." % (shop or "지점")),
           "prices": [{"name": n, "price": bag[n],
                       "price_source": "delivery_coupangeats"} for n in order]}
    p = os.path.join(OUT, "%s_delivery.json" % slug)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("가게: %s" % (shop or "(못 읽음)"))
    print("✅ 메뉴 %d개 -> %s" % (len(order), p))
    if skipped:
        print("   카테고리 제목이라 뺀 것 %d개: %s" % (len(skipped), skipped[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
