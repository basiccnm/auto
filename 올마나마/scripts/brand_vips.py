# -*- coding: utf-8 -*-
"""빕스(VIPS) 메뉴 수집 — 공식 홈페이지 렌더 DOM. 2026-07-31 신설

    python scripts/brand_vips.py

경로 (2026-07-31 확인)
    https://www.ivips.co.kr/menu?categoryIdx=6   MAIN (스테이크 등, 가격 있음)
    https://www.ivips.co.kr/menu?categoryIdx=1   샐러드바 (이용요금)
    https://www.ivips.co.kr/menu?categoryIdx=15  딜리버리 → 외부 스마트스토어 안내만, 메뉴 없음

🔴 **m.ivips.co.kr 로 가지 마라** — CJ ONE SSO(nsso.cjone.com)로 튕긴다. www 를 쓴다.
🔴 화면은 «이름 / 영문명 / 가격 / 더보기» 가 줄바꿈으로 이어진다. 그 짝을 그대로 읽는다.
⚠️ 공식 유의사항: 「메뉴와 가격은 점포에 따라 상이할 수 있습니다」 · 모든 가격 10% VAT 포함

결과: data/brand_menu_list/vips.json
"""
import io
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
PAGES = [("MAIN", "https://www.ivips.co.kr/menu?categoryIdx=6"),
         ("샐러드바", "https://www.ivips.co.kr/menu?categoryIdx=1")]
RX_WON = re.compile(r"^([\d,]{3,})원$")


def render(url):
    exe = next((p for p in CHROME if os.path.exists(p)), None)
    if not exe:
        raise RuntimeError("크롬을 못 찾았다")
    r = subprocess.run([exe, "--headless=new", "--disable-gpu", "--dump-dom",
                        "--virtual-time-budget=9000", url],
                       capture_output=True, timeout=120)
    return r.stdout.decode("utf-8", "replace")


def to_lines(dom):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", dom)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|td|tr|span)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">"))
    return [x.strip() for x in t.split("\n") if x.strip()]


def parse(lines):
    """«한글이름 / 영문명 / 12,345원» 짝을 뽑는다. 가격 바로 위 두 줄에서 이름을 고른다."""
    out = []
    for i, ln in enumerate(lines):
        m = RX_WON.match(ln)
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        name = None
        for j in (i - 2, i - 1):          # 영문명이 끼는 경우가 있어 두 줄 위까지 본다
            if j < 0:
                continue
            c = lines[j]
            if RX_WON.match(c) or c in ("더보기", "NEW", "BEST"):
                continue
            if re.search(r"[가-힣]", c) and 2 <= len(c) <= 30:
                name = c
        if name:
            out.append((name, price))
    # 같은 이름이 연달아 잡히면 앞의 것만 남긴다
    seen, res = set(), []
    for n, p in out:
        if n in seen:
            continue
        seen.add(n)
        res.append((n, p))
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for cname, url in PAGES:
        lines = to_lines(render(url))
        got = parse(lines)
        if not got:
            print("🔴 %-8s 0개 — 화면 구조가 바뀌었는지 확인할 것 (%s)" % (cname, url))
            continue
        cats.append({"name": cname, "parent": None, "ext_id": url.split("=")[-1]})
        for i, (n, p) in enumerate(got):
            nm = n if n not in seen else "%s (%s)" % (n, cname)
            seen.add(nm)
            menus.append({"name": nm, "price": p, "price_source": "official",
                          "cats": [[cname, i]]})
        print("   · %-8s %2d개" % (cname, len(got)))
        time.sleep(1.0)

    doc = {"brand": "빕스", "slug": "vips",
           "source": "https://www.ivips.co.kr/menu?categoryIdx=6",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지 렌더 DOM. 10% VAT 포함. 「딜리버리」 탭은 외부 스토어 안내만 "
                   "있어 메뉴가 없다. 공식 유의사항: 메뉴와 가격은 점포에 따라 상이할 수 있음.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "vips.json")
    # 🔴 **빈 결과로 기존 JSON 을 덮지 않는다** (2026-07-31 실제 사고).
    #    헤드리스 렌더가 0개를 받아왔는데 그대로 저장해 22개짜리 JSON 이 빈 파일이 됐다.
    #    수집이 실패하는 건 있을 수 있는 일이지만, **실패가 기존 자료를 지우면 안 된다.**
    if not menus:
        print("🔴 받은 메뉴가 0개다 — 기존 JSON 을 지키고 저장하지 않는다.")
        print("   화면 구조가 바뀌었거나 렌더가 덜 된 것이다. 브라우저로 확인할 것.")
        return 1
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 **줄었다**. 덮지 않는다(빽다방 반토막 사고 방지)."
                  % (old_n, len(menus)))
            print("   정말 줄어든 게 맞으면 기존 파일을 치우고 다시 돌릴 것.")
            return 1
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
