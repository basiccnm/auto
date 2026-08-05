# -*- coding: utf-8 -*-
"""LOTTE EATZ 브랜드(롯데리아·엔제리너스·크리스피크림 …) 메뉴판. 2026-07-28

    python scripts/brand_lotteeatz.py                 # 미리보기
    python scripts/brand_lotteeatz.py --apply
    python scripts/brand_lotteeatz.py --brand ria --apply

🔴 왜 전용 수집기가 필요했나
   `brand_menu_list.py` 로는 **96개 중 12개**밖에 못 얻었다. 이유가 둘이다:
     ① 가격이 `<span class="val">7,900</span><span class="unit">원</span>` 로 쪼개져 있다
     ② 카테고리 탭(버거·디저트·치킨·음료·아이스샷)이 **누를 때만 그려진다** —
        headless `--dump-dom` 은 첫 탭만 받는다. 탭을 눌러도 네트워크 요청이 없다

   ✅ 정답: 페이지 **인라인 스크립트에 `pList` 전역 배열**이 통째로 들어 있다.
      이름(`presPrdNm`) · 가격(`sellPrice`) · 카테고리(`displayCategoryNm`) · 이미지(`imgPath`)
      가 다 있다. DOM 을 긁을 필요가 없다.
      (`brand-site-spa-use-internal-api` 와 같은 갈래 — DOM 이 비면 데이터 원본을 찾는다)

⚠️ 이 값은 **본사 기준 판매가**다. 지점 가격이 아니다 — 그래서 출처를 `official` 로 넣는다.
⚠️ Incapsula(WAF)가 앞에 있다. 간격을 두고 브랜드별로 돈다. 몰아 치지 말 것.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GAP = 6

# LOTTE EATZ 안의 브랜드 — 우리 DB 이름과 사이트 코드를 잇는다
BRANDS = {
    "ria": "롯데리아",
    "aig": "엔제리너스",
    "kkd": "크리스피크림도넛",
}


def render(url, budget=14000):
    r = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
         "--disable-extensions", "--hide-scrollbars", "--window-size=1280,4000",
         "--virtual-time-budget=%d" % budget, "--dump-dom", url],
        capture_output=True, timeout=120)
    return r.stdout.decode("utf-8", "replace")


def extract(dom):
    """인라인 스크립트의 `var pList = [...]` 를 통째로 꺼낸다."""
    m = re.search(r"(?:var|let|const)?\s*pList\s*=\s*(\[)", dom)
    if not m:
        return []
    i = m.start(1)
    depth, j = 0, i
    while j < len(dom):                    # 대괄호 짝을 세어 배열 끝을 찾는다
        ch = dom[j]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        j += 1
    try:
        return json.loads(dom[i:j + 1])
    except Exception as e:
        print("  ! pList 파싱 실패: %s" % str(e)[:70])
        return []


def one(code, bname, apply_):
    url = "https://www.lotteeatz.com/brand/%s" % code
    print("■ %-12s %s" % (bname, url), flush=True)
    dom = render(url)
    if not dom:
        print("  🔴 렌더 실패 — 사이트가 막혔을 수 있다")
        return 0
    items = extract(dom)
    if not items:
        print("  🔴 pList 를 못 찾았다 — **사이트 구조가 바뀌었다.** 조용히 넘기지 말 것")
        return 0

    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
    if not br:
        print("  🔴 DB 에 «%s» 브랜드가 없다" % bname)
        return 0
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")

    seen, stats, changed = set(), {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
    cats = {}
    for it in items:
        nm = (it.get("presPrdNm") or it.get("productNm") or "").strip()
        pr = it.get("sellPrice") or it.get("aplyPrice")
        if not nm or not pr:
            continue
        k = re.sub(r"\s+", "", nm)
        if k in seen:
            continue
        seen.add(k)
        cat = (it.get("displayCategoryNm") or "").strip() or "기타"
        cats[cat] = cats.get(cat, 0) + 1
        if not apply_:
            continue
        before = cur.execute("SELECT price FROM brand_menu_official WHERE brand_id=? AND name=?",
                             (br["id"], nm)).fetchone()
        r = PS.put(cur, br["id"], nm, int(pr), source=PS.SRC_OFFICIAL, now=now)
        cur.execute("UPDATE brand_menu_official SET category=COALESCE(?,category), "
                    "image_url=COALESCE(image_url,?) WHERE brand_id=? AND name=?",
                    (cat, it.get("imgPath") or None, br["id"], nm))
        db.commit()                        # 한 건씩 즉시 저장 — 끊겨도 이어간다
        stats[r] = stats.get(r, 0) + 1
        if r == "changed":
            changed.append((nm, before["price"], int(pr)))

    print("  메뉴 %d개 · 탭 %s" % (len(seen), " / ".join(
        "%s %d" % (k, v) for k, v in sorted(cats.items(), key=lambda x: -x[1]))))
    if apply_:
        print("  저장: 새로 %d · 바뀜 %d · 그대로 %d · 사람확정 건너뜀 %d"
              % (stats["new"], stats["changed"], stats["same"], stats["skip"]))
        for nm, a, b in changed[:15]:      # 값이 바뀐 것만 보고한다
            print("    💰 %-26s %s → %s" % (nm[:26], format(a or 0, ","), format(b, ",")))
    else:
        print("  (미저장 — --apply)")
    db.close()
    return len(seen)


def main():
    apply_ = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--brand") + 1] if "--brand" in sys.argv else None
    tot = 0
    for code, bname in BRANDS.items():
        if only and only not in (code, bname):
            continue
        tot += one(code, bname, apply_)
        time.sleep(GAP)                    # WAF 가 있다 — 몰아 치지 않는다
    print("\n끝. 메뉴 %d개" % tot)


if __name__ == "__main__":
    main()
