# -*- coding: utf-8 -*-
"""멕시카나치킨 메뉴판 — 이름 + 가격. 2026-07-28

    python scripts/brand_mexicana.py            # 미리보기
    python scripts/brand_mexicana.py --apply

구조 (실측)
    <li>
      <dl class="tit"><dt>순살 고추화삭</dt><dd>설명…</dd></dl>
      … <strong>26,000</strong>
    </li>

🔴 가격이 `<strong>26,000</strong>` — **「원」이 없다.**
   그래서 «숫자+원» 을 찾는 일반 파서가 0건으로 봤다(`brand_probe9` 판정: 「가격 쪼개짐」).
   여기서는 `<dt>` 와 `<strong>` 을 짝지어 읽는다.

카테고리 6개는 `?catecode=` 로 갈린다 — 목록 페이지의 탭에서 **이름과 순서를 그대로** 읽는다.
    전체 → 후라이드 → 양념 → 시즈닝 → 순살 → 부위별
⚠️ 코드를 손으로 나열한 순서와 화면 순서가 다르다. **화면 탭 순서**를 쓴다.
⚠️ 「전체」 는 중복 진열 탭이지만 **브랜드가 그렇게 보여주므로 그대로 둔다**
   (2026-07-28 방침: 브랜드 메뉴판을 있는 그대로 — `브랜드메뉴판등록방식.md`).
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                 # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BRAND = "멕시카나치킨"
SLUG = "mexicana"
BASE = "https://www.mexicana.co.kr/menu/product.asp"
FIRST = "1000001"          # 여기서 탭 목록을 읽는다
GAP = 4

RX_LI = re.compile(r"(?is)<li[^>]*>(.*?)</li>")
RX_DT = re.compile(r"(?is)<dt[^>]*>(.*?)</dt>")
RX_STRONG = re.compile(r"(?is)<strong[^>]*>\s*([\d,]{3,9})\s*</strong>")
RX_TAB = re.compile(r"(?is)catecode=(\d+)[^>]*>(.{0,90}?)</a>")
# 🔴 목록이 **쪽으로 나뉜다**(2026-07-28). 첫 쪽만 읽으면 「전체」 탭이 29개 중 12개로 잡힌다.
RX_PAGE = re.compile(r"(?i)page\w*\s*=\s*[\"']?(\d{1,3})")


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def render(url, budget=15000):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,6000",
             "--virtual-time-budget=%d" % budget, "--dump-dom", url],
            capture_output=True, timeout=150)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def parse(dom):
    out = []
    for body in RX_LI.findall(dom):
        dt = RX_DT.search(body)
        st = RX_STRONG.search(body)
        if not dt or not st:
            continue
        nm = strip(dt.group(1))
        try:
            pr = int(st.group(1).replace(",", ""))
        except ValueError:
            continue
        if nm and 1000 <= pr <= 300000:
            out.append((nm, pr))
    return out


def tabs_of(dom):
    """화면 탭 — (코드, 이름) 을 **나온 순서 그대로**. 중복 코드는 처음 것만."""
    out, seen = [], set()
    for cc, raw in RX_TAB.findall(dom):
        nm = strip(raw)
        if not nm or cc in seen or len(nm) > 12:
            continue
        seen.add(cc)
        out.append((cc, nm))
    return out


def main():
    apply_ = "--apply" in sys.argv

    dom = render("%s?catecode=%s" % (BASE, FIRST))
    tabs = tabs_of(dom)
    if not tabs:
        print("🔴 탭을 못 읽었다 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    print("탭 %d개: %s" % (len(tabs), " → ".join(n for _, n in tabs)), flush=True)

    # 카테고리마다 **그 안에서의 자리**를 함께 담는다. 여러 탭에 걸리면 전부 기록한다
    order, byname = [], {}
    for cc, cn in tabs:
        rows, pos = [], 0
        page, n = dom if cc == FIRST else render("%s?catecode=%s" % (BASE, cc)), 1
        while True:
            got = parse(page)
            rows += got
            last = max([int(x) for x in RX_PAGE.findall(page)] or [1])
            if n >= last or n >= 20:          # 20쪽에서 멈춘다 — 무한루프 방지
                break
            n += 1
            time.sleep(GAP)
            page = render("%s?catecode=%s&page=%d" % (BASE, cc, n))
        for nm, pr in rows:
            k = re.sub(r"\s+", "", nm)
            if k not in byname:
                byname[k] = {"name": nm, "price": pr, "price_source": "official", "cats": []}
                order.append(k)
            byname[k]["cats"].append((cn, pos))
            pos += 1
        print("  %-8s %2d개 (%d쪽)" % (cn, len(rows), n), flush=True)
        time.sleep(GAP)

    items = [byname[k] for k in order]
    if not items:
        print("🔴 0건 — **화면 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return
    print("\n● %s — 고유 메뉴 %d개 · 연결 %d건"
          % (BRAND, len(items), sum(len(x["cats"]) for x in items)))
    for it in items[:8]:
        print("   %-26s %8s원  %s" % (it["name"][:26], format(it["price"], ","),
                                      ", ".join(c for c, _ in it["cats"])))
    if not apply_:
        print("\n(미저장 — --apply)")
        return

    c = store.connect()
    store.ensure(c)
    bid = store.brand_id(c, name=BRAND)
    store.replace_brand(c, bid, [{"name": n} for _, n in tabs], items,
                        collector="brand_mexicana")
    c.close()


if __name__ == "__main__":
    main()
