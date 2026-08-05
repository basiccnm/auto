# -*- coding: utf-8 -*-
"""
노랑통닭(slug=norangtongdak) 전용 메뉴판 수집기 — JSON 만 만든다. DB 는 건드리지 않는다.

## 어떻게 뚫었나 (2026-07-28)
- `https://www.norangtongdak.co.kr/` 는 4.5KB 인트로 «스플래시» 다. 메뉴 링크가 없는 게 맞다.
  다만 껍데기가 아니라 **갈림길 페이지**였다 — body 에 링크가 딱 둘 있다:
      /main.html                → 브랜드 홈페이지 (여기가 진짜 사이트)
      https://xn--o80br1a25h2q8a.kr/  → 창업 홈페이지 (관계 없음)
  `<link rel=canonical>` 은 루트를 가리켜 도움이 안 됐다. **body 의 <a href> 두 개**가 단서였다.
- `/main.html` 은 84KB 서버렌더 HTML. GNB 에 메뉴 탭 3개가 그대로 있다:
      /menu/best.html          베스트
      /menu/chicken_list.html  치킨
      /menu/side.html          사이드
  (`/menu/chicken.html` 도 링크돼 있지만 상품 링크가 0건인 소개용 페이지라 담지 않는다)
- SPA 가 아니다. 브라우저·헤드리스 없이 urllib 로 전부 읽힌다.
- 목록은 `ul.c_list > li` — `<p>` 가 메뉴명, `p_no` 가 상품 번호. **목록에 가격은 없다.**
- 가격은 상세(`menu/chicken_view.html?mode=VIEW_FORM&p_no=N&s_p_type=A`,
  사이드는 `side_view.html ... s_p_type=F`)의 `div.v_bg_txt6` 에 «라벨 + 가격» 줄로 있다.
  한 메뉴에 옵션이 여러 줄인 경우가 있다(오리지널(뼈/순살) 24,000 / 콤보(다리+윙+봉) 26,000).
  → 첫 줄을 `price`, 전체를 `price_options` · `price_note` 에 남긴다.
  상세에 «※ 메뉴의 유무와 가격은 매장마다 상이할 수 있습니다» → 배달가가 아닌 매장(홀) 기준가.
- 알레르기·중량도 상세 본문에 텍스트로 있다(`알레르기 성분` / `조리 전 중량` 다음 div.v_bg_txt4).
- 원산지는 별도 페이지 **`https://www.norangtongdak.co.kr/about/`** (상세의 검은 버튼 링크).
  이미지가 아니라 **HTML 표**라 그대로 읽힌다. 첫 표가 원산지다.
  🔴 뼈닭=국내산 / 순살=**브라질산** / 콤보(날개·북채)=국내산 — 한 메뉴 안에서 부위별로 갈린다.

## 함정 (여기서 실제로 걸린 것)
- 목록 `ul.c_list` 끝에 **HTML 주석으로 남은 템플릿 더미**가 있다(`바삭 누룽지 치킨` 18~19번 반복,
  링크가 `chicken_view.html` 로 파라미터도 없다). 주석을 먼저 지우지 않으면 치킨 38건·사이드 45건으로 부풀어 오른다.
  → `<!-- -->` 를 제거한 뒤 파싱한다.
- 목록 위쪽 `div.slider4` 는 같은 카테고리 상품의 **배너 슬라이드**다(치킨 3장). 중복이라 담지 않는다.
  단 `베스트` 탭은 이 슬라이드**만** 있고 목록이 없어서, 거기서만 슬라이드를 카테고리 구성으로 쓴다.
- 「베스트」 탭에는 메뉴명이 없다(배너 이미지뿐). 이름은 상세 페이지에서 가져온다.
- `/menu/chicken.html` 은 **메뉴 탭이 아니다.** 메인의 우측 배너 두 장이 걸어놓은 옛 단일 상품 페이지로
  「고바치 / 뼈 20,000원」 하나만 있고 현재 치킨 목록에도 사이트맵(`/guide/sitemap.html`)에도 없다.
  사이트맵이 인정하는 메뉴 페이지는 best · chicken_list · side **3장뿐**이라 그것만 담는다.
- 원산지 표에서 `대파 간장 치킨 반반` · `우도 땅콩 치킨 반반` · `웰빙 파닭 반반` 은 이름이 정확히 없다
  (표에는 `웰빙 파닭 반반 치킨` 으로만 있다). **추측해서 붙이지 않는다** — origin_note 에 표 전체가 남는다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.request
from html import unescape

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.norangtongdak.co.kr"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
GAP = 1.2  # 요청 간격(초)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "norangtongdak.json")

# /main.html GNB · 각 목록 페이지 상단 visual_tab 의 순서 그대로
TABS = [
    ("베스트", "/menu/best.html", "chicken_view", "A"),
    ("치킨", "/menu/chicken_list.html", "chicken_view", "A"),
    ("사이드", "/menu/side.html", "side_view", "F"),
]

_cache = {}


def get(url):
    if url in _cache:
        return _cache[url]
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    html = raw.decode("utf-8", "replace")
    _cache[url] = html
    time.sleep(GAP)
    return html


def clean(h):
    """script/style/HTML주석 제거 — 주석 안에 템플릿 더미 메뉴가 들어 있다."""
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def txt(s):
    s = re.sub(r"(?s)<br\s*/?>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = "\n".join(x.strip() for x in s.split("\n"))
    return s.strip()


# ── 원산지 (/about/ 첫 번째 표) ───────────────────────────────────────────
def origin_table():
    """[(제품명원문, [제품명들], 품목, 원산지), ...] 와 표 전체 원문을 돌려준다."""
    h = clean(get(BASE + "/about/"))
    m = re.search(r"(?s)<table>(.*?)</table>", h)
    if not m:
        return [], None
    rows, lines = [], []
    # 🔴 첫 칸(제품명)이 rowspan 으로 여러 줄을 덮는다.
    #    이걸 무시하면 「순살 = 브라질산」·「콤보 = 국내산」 줄이 통째로 사라진다(2026-07-28 실제로 겪음).
    carry_name, carry_left = None, 0
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", m.group(1)):
        cells = re.findall(r"(?s)<td([^>]*)>(.*?)</td>", tr)
        if not cells:
            continue
        if carry_left > 0:                       # 위 줄의 제품명이 아직 살아 있다
            cur_names, rest = carry_name, cells
            carry_left -= 1
        else:
            cur_names, rest = txt(cells[0][1]), cells[1:]
            rs = re.search(r'rowspan="(\d+)"', cells[0][0])
            carry_name, carry_left = cur_names, (int(rs.group(1)) - 1 if rs else 0)
        vals = [txt(c[1]) for c in rest]
        if len(vals) == 3:             # 품목 / 세부 / 원산지
            item, org = vals[0] + " " + vals[1], vals[2]
        elif len(vals) == 2:           # 품목(colspan=2) / 원산지
            item, org = vals[0], vals[1]
        else:
            continue
        names = [x.strip() for x in re.split(r"[,\n]", cur_names) if x.strip()]
        rows.append((cur_names, names, re.sub(r"\s+", " ", item).strip(), org))
        lines.append("%s | %s | %s" % (re.sub(r"\s+", " ", cur_names), item, org))
    note = "원산지 표시 (%s/about/) — 원문\n제품명 | 품목 | 원산지\n" % BASE + "\n".join(lines)
    return rows, note


def norm(s):
    return re.sub(r"\s+", "", s)


def origin_for(name, rows):
    """이름이 **정확히** 일치할 때만 붙인다. 추측 매칭 금지 — 못 붙으면 None(origin_note 로 남는다)."""
    hit = []
    for _raw, names, item, org in rows:
        if any(norm(n) == norm(name) for n in names):
            hit.append("%s: %s" % (item, org))
    return " / ".join(hit) if hit else None


# ── 목록 ─────────────────────────────────────────────────────────────────
def list_items(path, view):
    h = clean(get(BASE + path))
    m = re.search(r'(?s)<ul class="clfix ac mt50 c_list">(.*?)</ul>', h)
    out = []
    if m:
        for li in re.findall(r"(?s)<li>(.*?)</li>", m.group(1)):
            pn = re.search(r"p_no=(\d+)", li)
            nm = re.search(r"(?s)<p>(.*?)</p>", li)
            if pn and nm:
                out.append((pn.group(1), txt(nm.group(1))))
        return out
    # 베스트 탭 — 목록이 없고 배너 슬라이드뿐이다. 이름은 상세에서 채운다.
    sl = re.search(r'(?s)<div class="slider[^"]*">(.*?)</div>\s*</div>', h)
    seg = sl.group(1) if sl else h
    for pn in re.findall(view + r"\.html\?mode=VIEW_FORM&amp;p_no=(\d+)", seg):
        if pn not in [x[0] for x in out]:
            out.append((pn, None))
    return out


# ── 상세 ─────────────────────────────────────────────────────────────────
def detail(view, p_no, s_type):
    url = "%s/menu/%s.html?mode=VIEW_FORM&p_no=%s&p=1&s_p_type=%s" % (BASE, view, p_no, s_type)
    h = clean(get(url))
    i = h.find('class="view_bg"')
    body = h[i:h.find("메뉴목록", i)] if i >= 0 else h

    nm = re.search(r'(?s)<p class="v_bg_txt1">(.*?)</p>', body)
    name = txt(nm.group(1)) if nm else None

    def block(label):
        m = re.search(r'(?s)v_bg_txt3">.*?%s\s*</p>\s*<div[^>]*v_bg_txt4">(.*?)</div>' % label, body)
        return txt(m.group(1)) or None if m else None

    allergy = block("알레르기 성분")
    weight = block("조리 전 중량")

    opts = []
    for seg in re.findall(r"(?s)<div class='clfix v_bg_txt6[^']*'>(.*?)</div>", body):
        lab = re.search(r'(?s)<p class="fl">(.*?)</p>', seg)
        pr = re.search(r'(?s)<p class="fr">(.*?)</p>', seg)
        if not pr:
            continue
        won = re.search(r"([\d,]+)\s*원", txt(pr.group(1)))
        opts.append({
            "label": txt(lab.group(1)) if lab else None,
            "price": int(won.group(1).replace(",", "")) if won else None,
            "raw": txt(pr.group(1)),
        })

    img = re.search(r'(?s)<div class="left">\s*<img src="([^"]+)"', body)
    return {
        "name": name, "url": url, "allergy": allergy, "weight": weight,
        "options": opts,
        "image": (BASE + img.group(1)) if img and img.group(1).startswith("/") else (img.group(1) if img else None),
    }


def main():
    orows, onote = origin_table()
    print("원산지 표 %d줄" % len(orows))

    cats, menus, by_name = [], [], {}
    dropped = []
    for ci, (cname, path, view, stype) in enumerate(TABS):
        cats.append({"name": cname, "parent": None, "ext_id": stype})
        items = list_items(path, view)
        print("[%s] 목록 %d건" % (cname, len(items)))
        for idx, (p_no, lname) in enumerate(items):
            d = detail(view, p_no, stype)
            name = d["name"] or lname
            if not name:
                dropped.append((p_no, "이름 없음"))
                continue
            # 메뉴 아닌 것 거르기 — 문장부호로 끝나거나 / 18자 이상 / 카테고리명과 같음
            bad = None
            if name.endswith((".", "!", "?", "…")):
                bad = "문장부호로 끝남"
            elif len(name) >= 18:
                bad = "18자 이상"
            elif name in [c[0] for c in TABS]:
                bad = "카테고리 이름과 같음"
            if bad:
                dropped.append((name, bad))
                continue

            key = (name, p_no)
            if key in by_name:                      # 다른 탭에 또 진열된 것 — 자리만 추가
                by_name[key]["cats"].append([cname, idx])
                continue
            opts = d["options"]
            price = next((o["price"] for o in opts if o["price"] is not None), None)
            note = None
            if len(opts) > 1 or (opts and opts[0]["label"] not in (None, "가격")):
                note = " / ".join("%s %s" % (o["label"], o["raw"]) for o in opts)
            row = {
                "name": name,
                "price": price,
                "price_source": "official",
                "price_note": note,
                "price_options": [{"label": o["label"], "price": o["price"]} for o in opts] or None,
                "weight_raw": d["weight"],
                "origin_raw": origin_for(name, orows),
                "allergy_raw": d["allergy"],
                "detail_url": d["url"],
                "image_url": d["image"],
                "ext_id": p_no,
                "cats": [[cname, idx]],
            }
            by_name[key] = row
            menus.append(row)

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다")
        return 1

    doc = {
        "brand": "노랑통닭", "slug": "norangtongdak",
        "source": BASE + "/main.html",
        "collected_at": time.strftime("%Y-%m-%d"),
        "origin_note": onote,
        "cats": cats, "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("\n저장: %s" % OUT)
    print("카테고리 %d개 · 메뉴 %d개 · 가격 있는 것 %d개"
          % (len(cats), len(menus), sum(1 for m in menus if m["price"] is not None)))
    print("원산지 붙은 메뉴 %d개" % sum(1 for m in menus if m["origin_raw"]))
    if dropped:
        print("\n버린 줄 %d개:" % len(dropped))
        for n, why in dropped:
            print("  - %s (%s)" % (n, why))
    else:
        print("버린 줄 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
