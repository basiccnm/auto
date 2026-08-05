# -*- coding: utf-8 -*-
"""`_preview` 의 **고아 페이지**를 찾아 지운다. 2026-07-27

🔴 왜 — 브랜드를 숨기면(`brands.published=0`) 생성기가 그 페이지를 **새로 만들지 않을 뿐**
   옛 파일은 `_preview` 에 그대로 남는다. `build_dist.py` 가 폴더를 통째로 복사하니
   **숨긴 브랜드가 라이브에 계속 서빙된다.**

   2026-07-27 실제 사고: 한신포차(숨김)의 `menu_478.html` 이 **새벽 1시 파일**로 남아
   `뫼루니 베이직 치킨용파우더 5kg` 을 화면에 뿌리고 있었다. DB 에는 그런 재료가 없다.
   상표 검사에서 잡힌 35건 중 대부분이 이 고아 파일이었다.

   재료명을 바꾸면 `price_<옛이름>.html` 도 같은 식으로 남는다(CLAUDE.md 경고 4번).

⛔ 지우기 전에 무엇을 지우는지 반드시 출력한다. `--apply` 없이는 아무것도 지우지 않는다.

    python scripts/preview_orphans.py
    python scripts/preview_orphans.py --apply
"""
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
PREVIEW = os.path.join(BASE, "_preview")
DIST = os.path.join(BASE, "_dist")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row

    # 살아 있어야 하는 것
    #  ⚠️ 파일명 규칙을 생성기와 **똑같이** 맞춘다. 처음엔 브랜드를 slug 로, 재료를 공백만 지운
    #     이름으로 판정했다가 살아 있는 페이지 116개를 고아로 잡았다(2026-07-27).
    #     · 브랜드 → `brand_<id>.html`   (gen_preview_html.py:1709)
    #     · 재료   → `price_<safe_slug(name)>.html` — 한글·영숫자만 남긴다
    #                (gen_ingredient_pages.py:92 `_KEEP`)
    keep = re.compile(r"[^0-9A-Za-z가-힣]+")

    live_menu = {str(r[0]) for r in c.execute(
        "SELECT m.id FROM menus m JOIN brands b ON b.id=m.brand_id WHERE b.published=1")}
    # 🔴 «published=1 이면 산다» 만으로는 부족하다(2026-07-28 순수치킨 사고).
    #    브랜드 페이지는 gen_preview_html.py 의 brand_ids 조건과 **똑같이** 판정해야 한다 —
    #    안 그러면 인스타 프로필 긁은 쓰레기 10행이 지워져 조건을 다시 못 채우는데도
    #    "살아 있다"고 오판해 옛 페이지가 영원히 남는다. 실제로 순수치킨이 이렇게 라이브에 남았다.
    live_brand = {str(r[0]) for r in c.execute("""
        SELECT b.id FROM brands b WHERE b.published=1
          AND (EXISTS(SELECT 1 FROM menus m WHERE m.brand_id=b.id)
            OR EXISTS(SELECT 1 FROM brand_menu_official o WHERE o.brand_id=b.id))""")}
    #  재료 페이지 주소는 DB 의 `page_slug` 가 정본이다(display_name_build.py 가 정한다).
    #  이름으로 다시 계산하면 옛 파일(`price_고추장해찬들태양초1kg.html`)을 살아 있다고 오판한다.
    #
    #  🔴 «page_slug 가 있다» 만으로는 부족하다(2026-07-27). page_slug 는 670종이 갖고 있지만
    #     `gen_ingredient_pages.py` 가 실제로 만드는 건 **326종**이다. 어느 메뉴에도 안 쓰이게 된
    #     재료(`sauce_yangnyeom` 은 BBQ·bhc 전용 소스로 쪼개면서 uses=0 이 됐다)는 페이지가 더는
    #     생성되지 않는데, 여기서 살아 있다고 봐서 **옛 파일이 영원히 남았다.**
    #     실제로 `price_양념치킨소스.html` 이 이름을 바꾸기 전 슬러그(`price_골드킹소스` 등)를
    #     링크한 채 라이브에 서빙되고 있었다.
    #     ⚠️ 이 조건은 `gen_ingredient_pages.py` 의 rows 쿼리와 **똑같아야 한다.** 한쪽만 바꾸면
    #        살아 있는 페이지를 고아로 잡거나(=지워버림) 옛 파일을 놓친다.
    live_ing = {keep.sub("", (r[0] or "").replace("price_", "")) for r in c.execute("""
        SELECT i.page_slug FROM ingredients i
        LEFT JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key
        WHERE (i.wholesale_price>0 OR i.manual_price>0) AND i.type <> 'live_composite'
          AND i.page_slug IS NOT NULL
        GROUP BY i.ingredient_key
        HAVING COUNT(DISTINCT mi.menu_id)>0 OR i.chamgagyeok_key IS NOT NULL
            OR i.type IN ('live','live_composite')""")}
    live_dish = {r[0] for r in c.execute("SELECT slug FROM dishes")}

    groups = {"메뉴": [], "브랜드": [], "재료": [], "요리": []}
    for fn in sorted(os.listdir(PREVIEW)):
        if not fn.endswith(".html"):
            continue
        m = re.match(r"^menu_(\d+)\.html$", fn)
        if m:
            if m.group(1) not in live_menu:
                groups["메뉴"].append(fn)
            continue
        m = re.match(r"^brand_(.+)\.html$", fn)
        if m:
            if m.group(1) not in live_brand:
                groups["브랜드"].append(fn)
            continue
        m = re.match(r"^price_(.+)\.html$", fn)
        if m:
            if keep.sub("", m.group(1)) not in live_ing:
                groups["재료"].append(fn)
            continue
        m = re.match(r"^dish_(.+)\.html$", fn)
        if m:
            if m.group(1) not in live_dish:
                groups["요리"].append(fn)

    total = sum(len(v) for v in groups.values())
    print("=" * 78)
    print("`_preview` 고아 페이지 — DB 에 근거가 없는 파일")
    print("=" * 78)
    for k, v in groups.items():
        print()
        print("● %s %d개" % (k, len(v)))
        for fn in v[:14]:
            p = os.path.join(PREVIEW, fn)
            ts = ""
            try:
                import datetime
                ts = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M")
            except Exception:
                pass
            print("    %-46s %s" % (fn, ts))
        if len(v) > 14:
            print("    … 외 %d개" % (len(v) - 14))

    print()
    print("합계 %d개%s" % (total, "  (지움)" if apply else "  ← 미삭제, --apply 를 붙여라"))

    if not apply:
        return
    n = 0
    for v in groups.values():
        for fn in v:
            for d in (PREVIEW, DIST):
                p = os.path.join(d, fn)
                if os.path.exists(p):
                    os.remove(p)
                    n += 1
    print("→ %d개 파일 삭제 (_preview · _dist)" % n)
    print()
    print("⚠️ 사이트맵을 다시 만들어야 한다:  python scripts/gen_sitemap.py")


if __name__ == "__main__":
    main()
