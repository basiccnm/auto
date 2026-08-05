# -*- coding: utf-8 -*-
"""피자마루 메뉴판 — 카테고리·메뉴·가격·구성·중량·원산지. 2026-07-28

    python scripts/brand_pizzamaru.py            # 미리보기
    python scripts/brand_pizzamaru.py --write    # data/brand_menu_list/pizzamaru.json 저장

⚠️ 옛 버전은 DB(`menu_price_store`)에 직접 적재했다. 지금 규칙(전용 수집기 → JSON 한 장)에
   맞춰 **적재 코드를 전부 버리고** JSON 만 만든다. DB 는 읽지도 쓰지도 않는다.

구조 (실측 2026-07-28) — 서버 렌더링. 헤드리스 크롬이 필요 없다.
    http://pizzamaru.co.kr/menu/{번호}/            ← 카테고리 목록
    http://pizzamaru.co.kr/menu/{번호}/p-2/        ← 2쪽 (`div.page_num` 에 링크가 있다)
    http://pizzamaru.co.kr/product/{gid}          ← 상세

    <div class="prd_lst menu_lst"><ul>
      <li class="soldout">                         ← 품절
        <div class="img"><a href="/product/17089209055144"><img src="…"></a></div>
        <div class="txt_box tac">
          <p class="t1 lh tov"><!--<span class="best">--> 불닭치킨피자 </p>   ← 이름
          <p class="t2 c6 tov2">매콤한 닭고기와 …</p>                        ← 구성 설명
          <p class="t3 lh">6,500원</p>                                       ← 가격

🔴 `t1` 안에 주석이 들어있다 → **주석을 먼저 걷어낸다.**
🔴 설명(`t2`)에도 「9,900원부터」 같은 숫자가 있다. 가격은 **`t3` 만** 쓴다.
🔴 `<p class="t1">메뉴소개</p>` 가 페이지 머리(`div.menu_tit`)에도 있다.
   그래서 `t1` 을 문서 전체가 아니라 **`div.prd_lst` 안에서만** 찾는다.
🔴 페이징이 있다. 몬스터·골드&바이트·사이드 는 2쪽까지다.
   옛 스크립트는 1쪽만 읽어 **15개를 통째로 놓쳤다.**

🔴 사이즈 — 목록은 사이즈를 이름에 안 적는다. 대신
   ① 사이즈 층이 **카테고리로** 갈려 있다 (클래식 / 몬스터 / 골드&바이트 / 1인피자(8인치) /
      퍼스널(마루업)). **같은 이름이 카테고리마다 gid·가격이 다르다** — 다른 메뉴다. 합치지 마라.
   ② 상세페이지 「사이즈 선택」 라디오에 `라지` · `점보` 가 있다.
      **점보 가격은 사이트 어디에도 안 적혀 있다.** `/dataurl_action/view_opchange/` 에
      POST 를 해야 나오는 주문 흐름이라 찌르지 않는다. 그래서 표시가는 첫(체크된) 사이즈 값이고
      `size_raw` 에 사이즈 목록을 원문 그대로 남긴다. **지어내지 않는다.**

중량 — 상세페이지 「영양 정보」 모달이 **사이즈별로** 준다
    <div class="nutrition_tb"> 제품명 | 전체중량(g) | …
       페퍼로니 피자L   683
       페퍼로니 피자점보 1304
    → weight_raw = "페퍼로니 피자L 683g / 페퍼로니 피자점보 1304g"

원산지 — 브랜드 공통 표 한 장이다 (상세페이지 모달 = `/information/02` 와 같은 표)
    표시항목 | 원산지 | 음식명(2열: 몬스터·시카고 계열 / 스크린·골드·바이트·1인 계열)
    → 최상위 `origin_note` 에 원문 그대로.
    → 메뉴별 `origin_raw` 는 **표가 그 메뉴 이름을 직접 적어준 행만** 붙인다.
      (띄어쓰기만 지운 완전일치. 「기타사이드 메뉴」 같은 묶음 표현을 내가 배분하지 않는다)

알레르기 — `/information/03` 도 브랜드 공통 표 한 장인데, 행 이름이 「페퍼로니 피자 R」처럼
    사이즈 층까지 붙어 있고 우리 메뉴명과 1:1 로 안 떨어진다. **억지 매칭을 하지 않는다** →
    `allergy_raw` 는 비운다(빈칸이 가짜보다 낫다).
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BRAND = "피자마루"
SLUG = "pizzamaru"
BASE = "http://pizzamaru.co.kr"
MENU_HOME = BASE + "/"
ORIGIN_URL = BASE + "/information/02"
COLLECTED = "2026-07-28"

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
GAP = 1.2

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "brand_menu_list", "pizzamaru.json")

RX_COMMENT = re.compile(r"<!--.*?-->", re.S)
RX_TABLINK = re.compile(r'<ul class="menu_tab[^"]*"[^>]*>(.*?)</ul>', re.S)
RX_A = re.compile(r'<a[^>]*href="([^"]*?/menu/(\d+)/?)"[^>]*>(.*?)</a>', re.S)
RX_LI = re.compile(r"<li( [^>]*)?>(.*?)</li>", re.S)
RX_T1 = re.compile(r'<p class="t1 lh tov">(.*?)</p>', re.S)
RX_T2 = re.compile(r'<p class="t2 c6 tov2">(.*?)</p>', re.S)
RX_T3 = re.compile(r'<p class="t3 lh">\s*([\d,]{1,9})\s*원', re.S)
RX_PROD = re.compile(r'href="/product/(\d+)"')
RX_IMG = re.compile(r'<img src="([^"]+)"')
RX_PAGE = re.compile(r'<div class="page_num">(.*?)</div>', re.S)
RX_PAGE_A = re.compile(r'href="(/menu/\d+/p-\d+/?)"')

RX_SIZE = re.compile(r'<span class="size_txt">(.*?)</span>', re.S)
RX_PRDTIT = re.compile(r'<p class="prd_tit[^"]*">(.*?)</p>', re.S)
RX_TR = re.compile(r"<tr>(.*?)</tr>", re.S)
RX_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)

# 메뉴가 아닌 줄을 거르는 기준 — 피자는 이름이 길어 진짜 메뉴가 죽는다.
# 그래서 **버리지 않고 표시만** 한다(구조상 `div.prd_lst > li > p.t1` 은 메뉴 자리다).
BAD_TAIL = ".!?~,;:"
MAXLEN = 18


def strip_tags(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def get(url):
    r = urllib.request.Request(url, headers=HDRS)
    return urllib.request.urlopen(r, timeout=30).read().decode("utf-8", "replace")


def nospace(s):
    return re.sub(r"\s+", "", s or "")


def okeys(name, personal=False):
    """원산지 표의 음식명과 맞춰볼 열쇠들. **표가 실제로 쓴 표기 흔들림만** 흡수한다.

    ① 띄어쓰기 무시            「몬스터 불고기피자」 = 「몬스터 불고기 피자」
    ② 끝의 「피자」 떼기        「몬스터 콤비네이션」 = 「몬스터 콤비네이션 피자」
    ③ 퍼스널 칸만 「(1인)·(퍼스널)」 붙여보기
       표 머리글이 그 열을 «…/피자마루업(1인피자)» 라고 직접 적어놨다.
       다른 카테고리에는 절대 쓰지 않는다.

    ⛔ 그 밖의 낱말 순서·수식어 차이(「오리지널 시카고」↔「리얼 시카고 오리지널」,
       「갈비 닭꼬치」↔「불갈비 닭꼬치」)는 **추측이라 안 붙인다.** 대신 보고에 남긴다.
    """
    base = nospace(name)
    ks = {base}
    if base.endswith("피자") and len(base) > 2:
        ks.add(base[:-2])
    if personal:
        for k in list(ks):
            ks.add(k + "(1인)")
            ks.add(k + "(퍼스널)")
    return ks


def prd_block(html):
    """`<div class="prd_lst menu_lst">` 안쪽만 잘라낸다. 머리말 `t1` 을 안 집으려고."""
    i = html.find('class="prd_lst')
    if i < 0:
        return ""
    j = html.find('<div class="page_num">', i)
    return html[i:j if j > 0 else len(html)]


# ── 카테고리 ────────────────────────────────────────────────────────────────
def read_cats():
    """홈에 실제로 적힌 `/menu/{번호}` 링크를 화면 순서대로 읽는다. 번호를 지어내지 않는다."""
    home = RX_COMMENT.sub(" ", get(MENU_HOME))
    m = RX_TABLINK.search(home)
    seq, seen = [], set()
    src = m.group(1) if m else home
    for _href, num, label in RX_A.findall(src):
        nm = strip_tags(label)
        if not nm or nm == "메뉴소개" or num in seen:
            continue
        seen.add(num)
        seq.append({"name": nm, "parent": None, "ext_id": num})
    return seq


# ── 목록 ────────────────────────────────────────────────────────────────────
def read_list(cat_num):
    """카테고리 1쪽 + `page_num` 이 실제로 가리키는 **다음** 쪽들. 주소를 조합하지 않는다.

    ⚠️ 2쪽의 `page_num` 은 「맨앞·1」로 **되돌아가는** 링크를 준다. 그걸 그대로 따라가면
       1쪽을 `/p-1/` 로 한 번 더 읽어 같은 메뉴가 카테고리에 두 번 붙는다.
       → 이미 본 쪽 번호는 다시 안 간다(첫 주소 = 1쪽).
    """
    urls = ["%s/menu/%s/" % (BASE, cat_num)]
    rows, done, pages, seen_gid = [], set(), {1}, set()
    while urls:
        u = urls.pop(0)
        if u in done:
            continue
        done.add(u)
        html = RX_COMMENT.sub(" ", get(u))          # 🔴 주석 먼저
        seg = prd_block(html)
        n0 = len(rows)
        for attr, body in RX_LI.findall(seg):
            attr = attr or ""
            t1 = RX_T1.search(body)
            if not t1:
                continue
            name = strip_tags(t1.group(1))
            if not name:
                continue
            t3 = RX_T3.search(body)
            price = int(t3.group(1).replace(",", "")) if t3 else None
            t2 = RX_T2.search(body)
            pid = RX_PROD.search(body)
            img = RX_IMG.search(body)
            if pid:
                if pid.group(1) in seen_gid:
                    continue
                seen_gid.add(pid.group(1))
            rows.append({
                "name": name,
                "price": price,
                "soldout": "soldout" in attr,
                "compose": strip_tags(t2.group(1)) if t2 else None,
                "gid": pid.group(1) if pid else None,
                "image": (BASE + img.group(1)) if img else None,
            })
        pg = RX_PAGE.search(html)
        if pg:
            for nxt in RX_PAGE_A.findall(pg.group(1)):
                pn = int(re.search(r"/p-(\d+)", nxt).group(1))
                if pn in pages:
                    continue
                pages.add(pn)
                full = BASE + nxt
                if full not in done and full not in urls:
                    urls.append(full)
        print("   %-34s %2d개" % (u.replace(BASE, ""), len(rows) - n0), flush=True)
        time.sleep(GAP)
    return rows


# ── 상세 ────────────────────────────────────────────────────────────────────
def read_detail(gid):
    html = RX_COMMENT.sub(" ", get(BASE + "/product/" + gid))
    out = {"compose": None, "weight": None, "sizes": None, "title": None}

    t = RX_PRDTIT.search(html)
    if t:
        out["title"] = strip_tags(t.group(1))
        # 설명은 제목 바로 뒤 <p class="fz16 c6">
        m = re.search(r'<p class="fz16 c6">(.*?)</p>', html[t.end():t.end() + 4000], re.S)
        if m:
            out["compose"] = strip_tags(m.group(1)) or None

    i = html.find('class="nutrition_tb"')
    if i >= 0:
        seg = html[i:html.find("</table>", i)]
        parts = []
        for tr in RX_TR.findall(seg):
            tds = [strip_tags(x) for x in RX_TD.findall(tr)]
            # ⚠️ 숫자만 받으면 안 된다 — 골드&바이트는 「골드908/바이트848」처럼 적혀 있다.
            #    숫자 필터를 걸었다가 그 카테고리 17개가 통째로 «중량 없음» 이 됐다.
            if len(tds) >= 2 and tds[0] and tds[0] != "제품명" and tds[1]:
                parts.append("%s %s" % (tds[0], tds[1]))
        if parts:
            out["weight"] = "전체중량(g): " + " / ".join(parts)

    j = html.find('class="size_td')
    if j >= 0:
        seg = html[j:html.find("</td>", j)]
        sz = [strip_tags(x) for x in RX_SIZE.findall(seg)]
        sz = [x for x in sz if x]
        if sz:
            out["sizes"] = " / ".join(sz)
    return out


# ── 원산지 ──────────────────────────────────────────────────────────────────
def read_origin():
    """브랜드 공통 원산지 표. 원문 그대로 + 메뉴 이름별 索引."""
    html = RX_COMMENT.sub(" ", get(ORIGIN_URL))
    i = html.find('class="origin_tb')
    if i < 0:
        return None, {}
    seg = html[i:html.find("</table>", i)]
    lines, by_name = [], {}
    for tr in RX_TR.findall(seg):
        tds = [strip_tags(x) for x in RX_TD.findall(tr)]
        if len(tds) < 3 or not tds[0] or tds[0] == "표시항목":
            continue
        item, origin = tds[0], tds[1]
        foods = " ".join(tds[2:])
        lines.append("%s - %s : %s" % (item, origin, foods))
        pair = "%s : %s" % (item, origin)
        for cell in tds[2:]:
            for nm in re.split(r"[,·]", cell):
                nm = nm.strip()
                if not nm:
                    continue
                k = nospace(nm)
                by_name.setdefault(k, []).append(pair)
                if k.endswith("피자") and len(k) > 2:
                    by_name.setdefault(k[:-2], []).append(pair)
    note = "[원산지 정보] " + " / ".join(lines) + "  (출처: %s)" % ORIGIN_URL
    return note, by_name


def main():
    write = "--write" in sys.argv

    cats = read_cats()
    print("카테고리 %d개: %s\n" % (len(cats), " · ".join(c["name"] for c in cats)))
    if not cats:
        print("🔴 카테고리 0개 — 홈 구조가 바뀌었다. 저장하지 않는다.")
        return

    # 1) 목록
    per_cat = {}
    for c in cats:
        print("● %s (/menu/%s/)" % (c["name"], c["ext_id"]))
        per_cat[c["ext_id"]] = read_list(c["ext_id"])

    # 2) 메뉴 = gid 하나 = 한 줄. gid 가 여러 카테고리에 걸리면 cats 만 늘린다.
    menus, by_gid, flagged = [], {}, []
    for c in cats:
        for pos, r in enumerate(per_cat[c["ext_id"]]):
            key = r["gid"] or ("noid:" + r["name"] + "@" + c["ext_id"])
            if key in by_gid:
                by_gid[key]["cats"].append([c["name"], pos])
                continue
            why = None
            if r["name"][-1] in BAD_TAIL:
                why = "문장부호로 끝남"
            elif len(r["name"]) >= MAXLEN:
                why = "%d자 (>=%d)" % (len(r["name"]), MAXLEN)
            elif any(r["name"] == x["name"] for x in cats):
                why = "카테고리 이름과 같음"
            if why:
                flagged.append((c["name"], r["name"], why))
            m = {
                "name": r["name"],
                "price": r["price"],
                "price_source": "official",
                "price_note": "품절" if r["soldout"] else None,
                "compose_raw": r["compose"],
                "weight_raw": None,
                "origin_raw": None,
                "allergy_raw": None,
                "size_raw": None,
                "detail_url": (BASE + "/product/" + r["gid"]) if r["gid"] else None,
                "image_url": r["image"],
                "ext_id": r["gid"],
                "cats": [[c["name"], pos]],
            }
            by_gid[key] = m
            menus.append(m)

    if flagged:
        print("\n⚠️ 「메뉴 아님」 규칙에 걸린 줄 %d개 — **버리지 않았다.** 확인할 것:" % len(flagged))
        for cn, nm, why in flagged:
            print("    [%s] %-46s %s" % (cn, nm, why))
        print("    → 전부 `div.prd_lst > li > p.t1` + `p.t3` 자리라 진짜 메뉴다"
              "(투탑박스는 이름에 구성이 들어가 길다).")

    if not menus:
        print("🔴 메뉴 0건 — 화면 구조가 바뀌었다. **저장하지 않는다.**")
        return

    # 3) 원산지 (브랜드 공통 표)
    print("\n원산지 표 읽는 중 …")
    origin_note, origin_idx = read_origin()
    if not origin_note:
        print("⚠️ 원산지 표를 못 읽었다 — 비운다")

    # 4) 상세 — 구성·중량·사이즈
    print("상세 %d쪽 …" % len(menus))
    for n, m in enumerate(menus, 1):
        if not m["ext_id"]:
            continue
        try:
            d = read_detail(m["ext_id"])
        except Exception as e:
            print("   ⚠️ %s 상세 실패: %s" % (m["name"], e))
            time.sleep(GAP)
            continue
        if d["compose"]:
            m["compose_raw"] = d["compose"]
        m["weight_raw"] = d["weight"]
        m["size_raw"] = d["sizes"]
        if d["sizes"] and "/" in d["sizes"]:
            note = "표시가는 %s 기준 (사이즈: %s · 나머지 사이즈 가격은 사이트 미공개)" \
                   % (d["sizes"].split("/")[0].strip(), d["sizes"])
            m["price_note"] = (m["price_note"] + " · " + note) if m["price_note"] else note
        if n % 10 == 0:
            print("   %d/%d" % (n, len(menus)), flush=True)
        time.sleep(GAP)

    # 5) 원산지 메뉴별 — 표가 이름을 직접 적어준 것만
    near = []
    for m in menus:
        if not origin_idx:
            break
        personal = any(c[0].startswith("퍼스널") for c in m["cats"])
        seen, keep = set(), []
        for k in sorted(okeys(m["name"], personal)):
            for p in origin_idx.get(k, []):
                if p not in seen:
                    seen.add(p)
                    keep.append(p)
        if keep:
            m["origin_raw"] = " / ".join(keep)
        else:
            base = nospace(m["name"])
            cand = [x for x in origin_idx if len(x) > 3 and (base in x or x in base)]
            if cand:
                near.append((m["cats"][0][0], m["name"], sorted(set(cand))))
    if near:
        print("\n⚠️ 원산지 표에 **비슷한 이름**이 있는데 안 붙인 것 %d개 — 추측이라 비웠다."
              " 사람이 볼 것:" % len(near))
        for cn, nm, cand in near:
            print("    [%s] %-24s ~ %s" % (cn, nm, ", ".join(cand)))

    doc = {
        "brand": BRAND, "slug": SLUG,
        "source": BASE + "/menu/ (카테고리 10개 · 상세 /product/{gid} · 원산지 " + ORIGIN_URL + ")",
        "collected_at": COLLECTED,
        "origin_note": origin_note,
        "cats": cats,
        "menus": menus,
    }

    np_ = sum(1 for m in menus if m["price"] is not None)
    nc = sum(1 for m in menus if m["compose_raw"])
    no = sum(1 for m in menus if m["origin_raw"])
    nw = sum(1 for m in menus if m["weight_raw"])
    ns = sum(1 for m in menus if m["size_raw"])
    print("\n● %s — 카테고리 %d · 메뉴 %d · 가격 %d · 구성 %d · 원산지 %d · 중량 %d · 사이즈 %d"
          % (BRAND, len(cats), len(menus), np_, nc, no, nw, ns))

    dup = {}
    for m in menus:
        dup.setdefault(m["name"], []).append(m)
    dups = {k: v for k, v in dup.items() if len(v) > 1}
    if dups:
        print("\n⚠️ 같은 이름이 여러 줄 — **사이즈 층이 카테고리로 갈린 것이다. 합치면 안 된다:**")
        for k, v in sorted(dups.items(), key=lambda x: -len(x[1])):
            print("    %-20s %s" % (k, " · ".join(
                "%s %s원" % (x["cats"][0][0], format(x["price"], ",") if x["price"] else "-")
                for x in v)))

    if not write:
        print("\n(미저장 — --write 를 붙여라)")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("\n저장: %s" % OUT)


if __name__ == "__main__":
    main()
