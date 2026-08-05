# -*- coding: utf-8 -*-
"""`data/brand_menu_list/*.json` → `brand_menu_official` 적재 + **판매가 대조표**. 2026-07-27

들어오는 것: `brand_menu_list.py` 산출물 — 이미 파싱된 `{brand, slug, url, pages, menus[]}`
             `menus[i] = {name, price, weight_raw, weight_g, src}`
나가는 것:   `brand_menu_official` 행 + 우리 `menus.sell_price` 와의 **차이 표**

🔴 왜 별도 적재기인가
   `brand_official_import.py` 는 **상세페이지 원문**(`brand_menu_detail/*.txt`)을 파싱한다.
   목록 페이지 수집분은 이미 이름·가격이 뽑혀 있어 그 로직이 필요 없다.
   2026-07-27: 굽네 74개·본도시락 268개 등 **926개를 수집해놨는데 적재기가 안 읽어** 묻혀 있었다.

🔴 품질이 브랜드마다 갈린다. 그냥 넣으면 쓰레기가 들어간다 — 걸러서 넣는다:
   · **가격 없는 줄은 버린다** — 카테고리 탭(`떡볶이`·`튀김류`·`라이스`)이 대부분이다
   · **설명문은 버린다** — 미스터피자 `치즈 러버들의 입맛저격!`, 푸라닭 `마늘 조금 묻은 …`
   · 사이즈·수량 안내(`1-2인용(23cm)`)와 내비게이션도 버린다
   ⛔ 버린 것은 **개수와 예시를 반드시 출력**한다. 조용히 줄이면 «다 넣었다»로 오해한다

🔴 순살 가격 혼입을 잡는다 (bhc 4건 · 굽네 3건 실제 발생)
   우리 판매가가 공식과 다를 때, 같은 브랜드 공식 메뉴에 «<이름> … 순살/가슴살» 이 있고
   그 가격이 우리 값과 같으면 **순살가를 쓴 것**이라고 표시한다.

    python scripts/brand_list_import.py --dry     # 적재 없이 대조표만
    python scripts/brand_list_import.py --apply
"""
import glob
import io
import json
import os
import re
import sqlite3
import sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "brand_menu_list")
sys.stdout.reconfigure(encoding="utf-8")

# ── 버릴 줄 ────────────────────────────────────────────────────────────────
# 설명문 신호 — 서술어·감탄·권유가 있으면 메뉴명이 아니다
RX_DESC = re.compile(r"(습니다|하세요|해보세요|입니다|였|되는|하는|주는|있는|없는|만나|즐기|"
                     r"완성|담은|가득|듬뿍|바삭|촉촉|부드러|고소|매콤|달콤|짭조름|풍미|"
                     r"중독|극대화|저격|만점|끝판왕|유혹|경험|!$|\?$|\.$|~$)")
# 사이즈·수량·안내
RX_INFO = re.compile(r"^\d\s*[-~]\s*\d\s*인용|^\d+\s*인용|^\(\d+cm\)|^[\d,]+\s*원$|"
                     r"^(레귤러|라지|패밀리|파티|미디엄|스몰|대|중|소)$|"
                     r"^(번역|피자|치킨|메뉴|전체|더보기|다음|이전|닫기|검색)$")
# 내비게이션·푸터
NAV = ("로그인", "회원가입", "장바구니", "매장찾기", "매장 찾기", "이벤트", "쿠폰", "공지사항",
       "브랜드", "회사소개", "채용", "창업", "고객센터", "이용안내", "개인정보", "주문하기",
       "본문 바로가기", "홈", "마이페이지", "찜 리스트", "주문조회", "상세")
RX_NAVISH = re.compile(r"^(등록일|작성일|조회수|Copyright|Total|\*|＊|·|-|\d+$)|바로가기|상세$")


def bad_name(nm):
    """(버릴까, 이유)."""
    t = (nm or "").strip()
    if not t:
        return True, "빈 이름"
    if len(t) > 28:
        return True, "너무 긺(설명문)"
    if any(w == t or (len(w) > 2 and w in t) for w in NAV):
        return True, "내비게이션"
    if RX_NAVISH.search(t):
        return True, "안내·날짜"
    if RX_INFO.search(t):
        return True, "사이즈·수량 안내"
    if RX_DESC.search(t) and len(t) >= 10:
        return True, "설명문"
    if not re.search(r"[가-힣A-Za-z]", t):
        return True, "글자 없음"
    return False, ""


def norm(s):
    return re.sub(r"[\s·,\-_.()\[\]/™®]+", "", (s or "")).lower()


# 🔴 이름이 글자까지 같은 경우는 거의 없다 (2026-07-27):
#    우리 `마가리타 피자 L` ↔ 공식 `마가리타 오리지널 라지 x 1 ( 23,500 원)`
#    우리 `치즈 러버 피자 L` ↔ 공식 `치즈러버`
#    그래서 **사이즈·수량·가격 표기와 «피자/치킨» 같은 업종어를 떼고** 핵심만 비교한다.
RX_SIZE = re.compile(r"\b[LMRSF]\b|라지|미디엄|레귤러|패밀리|파티|스몰|오리지널|씬|thin|"
                     r"x\s*\d+|\(\s*[\d,]+\s*원\s*\)|[\d,]+원|\d+\s*p\b|\(\d+p\)|"
                     r"한마리|반마리|곱빼기|\d+인용|\d+cm", re.I)
RX_GENERIC = re.compile(r"피자|치킨|버거|초밥|도시락|떡볶이|세트|단품|반상|한상")


def core(s):
    """비교용 핵심 이름 — 사이즈·수량·업종어를 뗀다."""
    t = RX_SIZE.sub(" ", s or "")
    t = RX_GENERIC.sub(" ", t)
    return norm(t)


def match(ours_name, ours_price, cands):
    """공식 후보 중 우리 메뉴와 같은 것. 못 찾으면 None — **억지로 붙이지 않는다.**

    🔴 2026-07-27: 업종어를 떼고 «가장 싼 것»을 고르게 했더니 오매칭이 났다 —
       `BBQ 양념치킨 24,500` 에 1,000원짜리 소스가, `피자스쿨 페퍼로니피자` 에 1,000원이 붙었다.
       그래서 **가격이 우리 값의 ±35% 안**일 때만 후보로 본다. 사이즈가 다른 것(패밀리·파티)과
       사이드메뉴가 저절로 걸러진다. 그 밖은 사람이 확인할 목록으로 넘긴다.
    """
    n, cn = norm(ours_name), core(ours_name)
    for m in cands:
        if norm(m["name"]) == n:
            return m                              # 완전일치는 가격 조건 없이 신뢰
    if not ours_price or len(cn) < 2:
        return None
    lo, hi = ours_price * 0.65, ours_price * 1.35
    # ⚠️ `--names` 로 **가격 없는 후보**가 섞이면서 None 비교로 죽었다(2026-07-28).
    #    가격으로 거르는 단계이니 값이 없는 후보는 여기서 제외한다(이름 완전일치는 위에서 이미 처리).
    near = [m for m in cands if m.get("price") and lo <= m["price"] <= hi]
    hit = [m for m in near if core(m["name"]) == cn]
    if len(hit) == 1:
        return hit[0]
    if len(hit) > 1:
        return min(hit, key=lambda m: abs(m["price"] - ours_price))
    hit = [m for m in near if cn in core(m["name"]) or core(m["name"]) in cn]
    if len(hit) == 1:
        return hit[0]
    return None


RX_BONELESS = re.compile(r"순살|가슴살|윙|봉|스틱|콤보|반반|곱빼기|세트|박스|\d+pcs", re.I)


NAMES_TOO = "--names" in sys.argv     # 가격이 없는 메뉴도 이름만 담는다


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    by_slug = {r["slug"]: dict(r) for r in c.execute(
        "SELECT id, name, slug FROM brands WHERE COALESCE(slug,'') <> ''")}

    total_in = total_ok = 0
    dropped = Counter()
    drop_ex = {}
    report = []

    for fp in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        try:
            d = json.load(io.open(fp, encoding="utf-8"))
        except Exception:
            continue
        slug = os.path.splitext(os.path.basename(fp))[0]
        b = by_slug.get(slug) or by_slug.get(slug.replace("_api", ""))
        if not b:
            continue
        menus = d.get("menus") or []
        if not menus:
            continue

        ok, seen = [], set()
        for m in menus:
            total_in += 1
            nm = (m.get("name") or "").strip()
            pr = m.get("price")
            # 🔴 **가격이 없어도 이름은 담는다** (대표 지시 2026-07-28:
            #    *"홈페이지 들어가서 메뉴를 다 먼저 정리하고 그담 가격을 검색으로 찾아"*).
            #    대부분의 브랜드 홈페이지는 가격을 안 적는다 — 여기서 버리면
            #    설빙 100개·용우동 146개가 통째로 사라져 **나중에 가격을 붙일 대상 자체가 없다.**
            #    ⚠️ 메뉴판 화면(`menu_board`)은 `price IS NOT NULL` 만 그리므로
            #       이름만 있는 줄이 «가격 없음» 으로 노출되지는 않는다.
            #    기본은 예전대로 «가격 있는 것만». `--names` 를 줄 때만 이름도 담는다.
            if not pr and not NAMES_TOO:
                dropped["가격 없음"] += 1
                drop_ex.setdefault("가격 없음", nm)
                continue
            bad, why = bad_name(nm)
            if bad:
                dropped[why] += 1
                drop_ex.setdefault(why, nm)
                continue
            k = norm(nm)
            if k in seen:
                dropped["중복"] += 1
                continue
            seen.add(k)
            ok.append(m)
        total_ok += len(ok)

        ours = [dict(r) for r in c.execute(
            "SELECT id, name, sell_price FROM menus WHERE brand_id=?", (b["id"],))]
        omap = {norm(x["name"]): x for x in ours}
        pmap = {norm(m["name"]): m for m in ok}

        # 판매가 대조
        diffs = []
        for x in ours:
            hit = match(x["name"], x["sell_price"], ok)
            if not hit:
                diffs.append((x, None, "공식에 같은 이름이 없다"))
                continue
            if (x["sell_price"] or 0) == hit["price"]:
                continue
            # 순살가 혼입 의심 — 우리 값과 같은 «…순살/가슴살» 메뉴가 있나
            sus = None
            for m in ok:
                if m["price"] == (x["sell_price"] or 0) and RX_BONELESS.search(m["name"]) \
                   and norm(x["name"])[:4] in norm(m["name"]):
                    sus = m["name"]
                    break
            diffs.append((x, hit, ("순살·변형 가격을 쓴 것으로 보인다 → «%s»" % sus) if sus
                          else "값이 다르다"))
        report.append((b, len(menus), len(ok), diffs))

        if apply:
            paired = {id(m): x["id"] for x in ours
                      for m in [match(x["name"], x["sell_price"], ok)] if m}
            for m in ok:
                mid = paired.get(id(m)) or (omap.get(norm(m["name"])) or {}).get("id")
                cur.execute("""INSERT INTO brand_menu_official
                    (brand_id, name, category, price, weight_raw, weight_g,
                     detail_url, menu_id, collected_at)
                    VALUES(?,?,NULL,?,?,?,?,?,date('now'))
                    ON CONFLICT(brand_id, name) DO UPDATE SET
                      -- 🔴 `price=excluded.price` 로 두면 **이름만 있는 수집분이
                      --    이미 있던 가격을 NULL 로 지운다**(2026-07-28 `--names` 도입 때 발견).
                      --    새 값이 있을 때만 덮는다.
                      price=COALESCE(excluded.price, brand_menu_official.price),
                      weight_raw=excluded.weight_raw,
                      weight_g=excluded.weight_g, detail_url=excluded.detail_url,
                      menu_id=COALESCE(excluded.menu_id, brand_menu_official.menu_id),
                      collected_at=date('now')""",
                            (b["id"], m["name"], m["price"], m.get("weight_raw"),
                             m.get("weight_g"), m.get("src"), mid))
    if apply:
        c.commit()

    # ── 출력 ────────────────────────────────────────────────────────────
    print("=" * 100)
    print("수집분 적재 — 파일 %d개 · 메뉴 %d개 중 %d개 통과"
          % (len(report), total_in, total_ok))
    print("=" * 100)
    print()
    print("버린 것 (조용히 줄이지 않는다):")
    for why, n in dropped.most_common():
        print("   %-16s %4d개   예: %s" % (why, n, (drop_ex.get(why) or "")[:52]))
    print()

    print("=" * 100)
    print("판매가 대조 — 우리 DB vs 공식")
    print("=" * 100)
    nsus = ndiff = nmiss = 0
    for b, nin, nok, diffs in sorted(report, key=lambda x: -x[2]):
        bad = [d for d in diffs if d[2] != ""]
        print()
        print("● %-14s 수집 %3d → 통과 %3d · 우리 메뉴 %d개" % (b["name"][:14], nin, nok, len(diffs)))
        for x, hit, why in diffs:
            if hit is None:
                nmiss += 1
                print("   ⚠️ %-22s 우리 %7s  — %s" % (x["name"][:22],
                                                  format(x["sell_price"] or 0, ","), why))
            else:
                if "순살" in why:
                    nsus += 1
                    mark = "🔴"
                else:
                    ndiff += 1
                    mark = "❗"
                print("   %s %-22s 우리 %7s → 공식 %7s  %s"
                      % (mark, x["name"][:22], format(x["sell_price"] or 0, ","),
                         format(hit["price"], ",") if hit.get("price") else "가격없음", why))
    print()
    print("=" * 100)
    print("🔴 순살가 혼입 의심 %d건 · ❗ 값 다름 %d건 · ⚠️ 공식에 없음 %d건%s"
          % (nsus, ndiff, nmiss, "  (DB 반영)" if apply else "  ← 미반영, --apply"))


if __name__ == "__main__":
    main()
