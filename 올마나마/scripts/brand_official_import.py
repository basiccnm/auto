# -*- coding: utf-8 -*-
"""수집한 상세페이지 **본문에서** 공식 메뉴를 뽑아 `brand_menu_official` 에 적재한다. 2026-07-27

들어오는 것: `data/brand_menu_detail/<slug>.txt` (`=== <url>` 로 쪽이 구분된 원문)
나가는 것:   `brand_menu_official` 행 + 브랜드별 요약

🔴 왜 본문에서 뽑나 (2026-07-27 실패 후 고침)
   처음엔 `<title>`·`og:title` 로 메뉴명을 잡았다. 그런데 사이트 대부분이 **모든 상세페이지에
   같은 제목**을 쓴다 — BBQ 40쪽 전부 "BBQ 치킨", 맥도날드 "맥도날드 프로모션", 교촌 "치킨메뉴".
   그래서 536쪽을 긁고 공식메뉴 131개(브랜드당 1개)만 남았다.
   본문 구조를 보면 **메뉴명은 가격 줄 바로 위**에 있다:
       [NEW] 필크런치            ← 메뉴명
       (굿즈 증정 문구)
       * 매장별 운영 상황 …
       마지막 한입까지 바삭하게 …   ← 설명
       27,000원                 ← 가격
       * 조리전 중량 : 10호(951~1050g) 이상
   그래서 **가격을 찾고 위로 올라가며** 메뉴명을 잡는다.

⛔ 자동 판정 금지. 중량이 안 적혀 있으면 비운다 — 업태 기본중량으로 채우지 않는다
   (그건 검수 단계에서 사람이 정한다 · `ingredients-evidence-only`).
   `weight_raw` 원문은 절대 버리지 않는다.

    python scripts/brand_official_import.py            # 적재 + 요약
    python scripts/brand_official_import.py --dry      # 적재 없이 요약만
"""
import glob
import io
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "brand_menu_detail")

RX_PRICE = re.compile(r"^([\d,]{3,9})\s*원$")
RX_WEIGHT = re.compile(r"중량\s*[:：]\s*([^\n|]{2,50})")
RX_HOSU = re.compile(r"(\d{1,2})\s*호\s*\(?\s*([\d,]+)\s*~\s*([\d,]+)\s*g")

# 메뉴명이 아닌 줄 — 내비게이션·안내 문구
NAV = ("메뉴", "로그인", "회원가입", "장바구니", "매장 찾기", "매장찾기", "이벤트", "쿠폰",
       "배달", "포장", "추천", "창업", "이용안내", "전화주문", "마이 페이지", "고객센터",
       "공지사항", "브랜드", "회사소개", "채용", "주문", "몰", "홈", "더보기", "전체",
       "DELIVERY", "PACKAGING", "NEW", "BEST", "HOT", "닫기", "검색", "다음", "이전")
RX_NAVISH = re.compile(r"^(기본 주소|Copyright|\(|\*|＊|·|-|\d+$)")
# 메뉴명 앞에 붙는 꼬리표
RX_TAG = re.compile(r"^\s*[\[(【]\s*(NEW|신메뉴|BEST|추천|HOT|리뉴얼|한정)\s*[\])】]\s*", re.I)


def norm(s):
    return re.sub(r"[\s·,\-_.()\[\]/]+", "", (s or "")).lower()


def is_name(l):
    """이 줄이 메뉴명일 수 있나."""
    t = RX_TAG.sub("", l).strip()
    if not (2 <= len(t) <= 30):
        return None
    if RX_NAVISH.match(t) or RX_PRICE.match(t):
        return None
    if t in NAV or any(t == w for w in NAV):
        return None
    if not re.search(r"[가-힣A-Za-z]", t):
        return None
    if re.search(r"(하세요|합니다|입니다|바랍니다|드립니다|있습니다)$", t):
        return None
    return t


def parse_page(url, text, brand, title_name=None):
    """상세페이지 한 장 → dict. 못 뽑는 건 None 으로 둔다.

    🔴 메뉴명은 **후보를 여러 개** 담아둔다(`cands`). 한 방식만 쓰면 브랜드마다 깨진다 —
       가격줄 기준은 BBQ 에서 39개를 뽑지만 피자스쿨은 3개로 떨어졌고,
       제목 기준은 피자스쿨 40개인데 BBQ 는 40쪽 전부 "BBQ 치킨" 이었다.
       그래서 후보를 모으고 **브랜드 단위로 흔한 것(사이트 공통 라벨)을 걸러낸 뒤** 고른다."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    d = {"url": url, "name": None, "price": None, "weight_raw": None, "weight_g": None,
         "origin": [], "allergy": [], "cands": [], "lines": lines}

    # ① 가격 줄을 찾고 ② 위로 올라가며 메뉴명 후보를 잡는다
    for i, l in enumerate(lines):
        m = RX_PRICE.match(l)
        if not m:
            continue
        p = int(m.group(1).replace(",", ""))
        if not (500 <= p <= 200000):          # 전화번호·연도 같은 숫자 걸러내기
            continue
        if d["price"] is None:
            d["price"] = p
        for j in range(i - 1, max(-1, i - 9), -1):
            nm = is_name(lines[j])
            if nm and norm(nm) != norm(brand):
                d["cands"].append(nm)
                break
        if d["cands"]:
            break

    # ③ 제목에서 뽑은 이름도 후보로 (피자스쿨처럼 제목이 메뉴명인 사이트)
    if title_name:
        tn = is_name(title_name)
        if tn and norm(tn) != norm(brand):
            d["cands"].append(tn)

    # ④ 내비게이션 뭉치를 지나친 뒤 처음 나오는 그럴싸한 줄도 후보
    for l in lines[8:60]:
        nm = is_name(l)
        if nm and norm(nm) != norm(brand) and nm not in d["cands"]:
            d["cands"].append(nm)
            break

    m = RX_WEIGHT.search(text)
    if m:
        d["weight_raw"] = m.group(1).strip()[:60]
    m = RX_HOSU.search(text)
    if m:
        lo, hi = int(m.group(2).replace(",", "")), int(m.group(3).replace(",", ""))
        d["weight_g"] = round((lo + hi) / 2.0)
        if not d["weight_raw"]:
            d["weight_raw"] = m.group(0)
    elif d["weight_raw"]:
        mm = re.search(r"([\d,.]+)\s*(kg|g)\b", d["weight_raw"], re.I)
        if mm:
            v = float(mm.group(1).replace(",", ""))
            d["weight_g"] = round(v * 1000 if mm.group(2).lower() == "kg" else v)

    for l in lines:
        if "원산지" in l and len(l) <= 200:
            d["origin"].append(l)
        if ("알레르" in l or "알러지" in l) and len(l) <= 200:
            d["allergy"].append(l)
    d["origin"], d["allergy"] = d["origin"][:6], d["allergy"][:6]
    return d


def main():
    dry = "--dry" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    brands = {r["slug"]: dict(r) for r in c.execute(
        "SELECT id, name, slug FROM brands WHERE COALESCE(slug,'') <> ''")}

    # 1층 json 의 제목 기반 이름도 후보로 쓴다(피자스쿨처럼 제목이 곧 메뉴명인 사이트)
    title_of = {}
    jp = os.path.join(BASE, "data", "research", "brand_menu_detail.json")
    if os.path.exists(jp):
        import json as _json
        for x in _json.load(io.open(jp, encoding="utf-8")):
            title_of[x["brand"]] = {d.get("url"): d.get("name")
                                    for d in (x.get("details") or []) if d.get("url")}

    if not dry:
        cur.execute("DELETE FROM brand_menu_official")   # 매번 다시 만든다(원문이 정본)

    rows_by_brand = {}
    for fp in sorted(glob.glob(os.path.join(SRC, "*.txt"))):
        slug = os.path.splitext(os.path.basename(fp))[0]
        b = brands.get(slug)
        if not b:
            continue
        raw = io.open(fp, encoding="utf-8", errors="replace").read()
        if not raw.strip():
            continue
        ours = {norm(r["name"]): r["id"] for r in
                c.execute("SELECT id, name FROM menus WHERE brand_id=?", (b["id"],))}
        titles = title_of.get(b["name"], {})

        # ── 1차: 쪽마다 후보를 모은다
        pages = []
        for chunk in raw.split("=== ")[1:]:
            nl = chunk.find("\n")
            url, body = chunk[:nl].strip(), chunk[nl + 1:]
            pages.append(parse_page(url, body, b["name"], titles.get(url)))

        # ── 2차: **그 쪽에만 나오는 줄이 메뉴명이다.**
        #    🔴 사이트 구조를 쫓지 않는다(2026-07-27). 브랜드마다 구조가 달라 세 번 깨졌다 —
        #       BBQ 는 가격 위, 피자스쿨은 제목, 본도시락은 내비게이션이 60줄 넘어 본문이 한참 아래다.
        #       공통 신호는 이것뿐이다: **메뉴명은 그 상세페이지에만 나오고 다른 쪽에는 없다.**
        #       내비게이션·푸터·브랜드명은 모든 쪽에 나오므로 저절로 걸러진다.
        from collections import Counter
        freq = Counter()
        for p in pages:
            freq.update(set(p["lines"]))
        many = len(pages) >= 4
        cut = max(2, int(len(pages) * 0.2)) if many else len(pages) + 1

        for p in pages:
            uniq = [l for l in p["lines"] if freq[l] <= cut]
            p["cands"] = [nm for nm in
                          (is_name(l) for l in uniq)
                          if nm and norm(nm) != norm(b["name"])] + p["cands"]

        cnt = Counter()
        for p in pages:
            for nm in dict.fromkeys(p["cands"]):
                cnt[norm(nm)] += 1
        common = {k for k, v in cnt.items() if many and v > len(pages) * 0.5}

        seen, out = set(), []
        for d in pages:
            pick = next((nm for nm in d["cands"]
                         if norm(nm) not in common and norm(nm) not in seen), None)
            if not pick:
                continue
            seen.add(norm(pick))
            out.append((b["id"], pick, None, d["price"], d["weight_raw"], d["weight_g"],
                        " | ".join(d["origin"])[:1000] or None,
                        " | ".join(d["allergy"])[:1000] or None,
                        d["url"], None, ours.get(norm(pick))))
        rows_by_brand[b["name"]] = out

    if not dry:
        for out in rows_by_brand.values():
            for r in out:
                cur.execute("""INSERT OR REPLACE INTO brand_menu_official
                    (brand_id,name,category,price,weight_raw,weight_g,origin_raw,allergy_raw,
                     detail_url,image_url,menu_id,collected_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", r)
        c.commit()

    print("%-16s %5s %5s %5s %5s %5s %s" % ("브랜드", "공식", "연결", "가격", "중량", "원산지", "우리DB"))
    print("-" * 74)
    tot = lk = pr = wg = og = 0
    for nm, out in sorted(rows_by_brand.items(), key=lambda x: -len(x[1])):
        if not out:
            continue
        b = next(v for v in brands.values() if v["name"] == nm)
        n_ours = c.execute("SELECT COUNT(*) FROM menus WHERE brand_id=?", (b["id"],)).fetchone()[0]
        a = sum(1 for r in out if r[10]);  b2 = sum(1 for r in out if r[3])
        d2 = sum(1 for r in out if r[5]);  e2 = sum(1 for r in out if r[6])
        tot += len(out); lk += a; pr += b2; wg += d2; og += e2
        print("%-16s %5d %5d %5d %5d %5d %5d개" % (nm[:16], len(out), a, b2, d2, e2, n_ours))
    print("-" * 74)
    print("합계 공식메뉴 %d개 · 연결 %d(%.0f%%) · 가격 %d(%.0f%%) · 중량 %d · 원산지 %d" % (
        tot, lk, lk * 100.0 / max(tot, 1), pr, pr * 100.0 / max(tot, 1), wg, og))
    if dry:
        print("(dry — DB 미반영)")
    c.close()


if __name__ == "__main__":
    main()
