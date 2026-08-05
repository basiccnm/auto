# -*- coding: utf-8 -*-
"""브랜드 메뉴판 **현황 한 방에 보기** — 읽기 전용. 2026-07-28 신설

    python scripts/brand_status.py            # 전체 요약 + 할 일
    python scripts/brand_status.py --full     # 브랜드 전부 나열
    python scripts/brand_status.py 치킨        # 그 업종만

⛔ **DB 를 절대 고치지 않는다.** SELECT 만 한다.

왜 만들었나
----------
브랜드를 하나 넣을 때마다 «진행률은? 가격 0인 곳은? 옛 잔재는? JSON 중에 안 넣은 건?» 을
매번 손으로 쿼리를 짜서 확인했다. 브랜드가 달라도 **묻는 것은 늘 같다.**
"""
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JDIR = os.path.join(BASE, "data", "brand_menu_list")


def pending(c):
    """수집 JSON 중 아직 DB 에 안 들어간 것.

    🔴 **메뉴 수와 가격 수를 둘 다** 본다 — 메뉴 수만 보면 «가격만 채워진 갱신» 을 놓친다
       (2026-07-28 호식이지두마리치킨: JSON 가격 24개, DB 0개인 채로 라이브에 나가 있었다).
    """
    todo, miss = [], []
    for f in sorted(glob.glob(os.path.join(JDIR, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        if "cats" not in d or "menus" not in d:
            continue
        r = c.execute("""SELECT b.name,
              (SELECT count(*) FROM brand_menu_official o WHERE o.brand_id=b.id) n,
              (SELECT count(*) FROM brand_menu_official o
                 WHERE o.brand_id=b.id AND o.price IS NOT NULL) np
              FROM brands b WHERE b.slug=? OR b.name=?""",
                      (d.get("slug"), d.get("brand"))).fetchone()
        base = os.path.basename(f)
        mt = time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(f)))
        jn, jp = len(d["menus"]), sum(1 for m in d["menus"] if m.get("price"))
        if not r:
            miss.append((base, d.get("slug"), d.get("brand"), jn, jp, mt))
        elif r["n"] != jn or r["np"] != jp:
            todo.append((base, r["name"], jn, jp, r["n"], r["np"], mt))
    return todo, miss


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv
    only = args[0] if args else None

    c = store.connect()
    rows = c.execute("""SELECT cc.name cat, b.id, b.name, b.frcs_cnt f,
        (SELECT count(*) FROM brand_menu_cat m WHERE m.brand_id=b.id) tabs,
        (SELECT count(*) FROM brand_menu_official o WHERE o.brand_id=b.id) n,
        (SELECT count(*) FROM brand_menu_official o
           WHERE o.brand_id=b.id AND o.price IS NOT NULL) np,
        (SELECT count(*) FROM brand_menu_official o
           WHERE o.brand_id=b.id AND o.collector IS NULL) legacy,
        (SELECT count(*) FROM menus m WHERE m.brand_id=b.id) mc
        FROM brands b JOIN categories cc ON cc.id=b.category_id
        WHERE b.published=1 ORDER BY cc.sort_order, b.frcs_cnt DESC""").fetchall()
    if only:
        rows = [r for r in rows if only in r["cat"]]
        if not rows:
            raise SystemExit("그런 업종이 없다: %s" % only)

    done = [r for r in rows if r["tabs"]]
    legacy = [r for r in rows if r["legacy"]]
    zero = [r for r in rows if r["n"] == 0]
    nopr = [r for r in rows if r["n"] and not r["np"]]
    m_all = sum(r["n"] for r in rows)
    m_pr = sum(r["np"] for r in rows)

    print("=" * 72)
    print("브랜드 %d곳 — ✅원본탭 %d · ⚠️옛잔재 %d · ⛔메뉴판0 %d"
          % (len(rows), len(done), len(legacy), len(zero)))
    print("메뉴 %d개 (가격 %d · %d%%)"
          % (m_all, m_pr, round(m_pr * 100.0 / m_all) if m_all else 0))
    print("=" * 72)

    if not only:
        print("\n■ 업종별")
        seen = {}
        for r in rows:
            d = seen.setdefault(r["cat"], [0, 0])
            d[1] += 1
            if r["tabs"]:
                d[0] += 1
        for k, (a, b) in seen.items():
            bar = "█" * int(a * 10.0 / b) + "·" * (10 - int(a * 10.0 / b))
            print("   %-14s %2d/%2d  %s" % (k, a, b, bar))

    if full:
        print("\n■ 브랜드 전체")
        cur = None
        for r in rows:
            if r["cat"] != cur:
                cur = r["cat"]
                print("\n[%s]" % cur)
            mark = "✅" if r["tabs"] else ("⚠️" if r["legacy"] else "⛔")
            print("   %s %-16s 가맹 %-6s 메뉴 %4d · 가격 %4d · 탭 %2d · 원가 %2d"
                  % (mark, r["name"], r["f"] or "-", r["n"], r["np"], r["tabs"], r["mc"]))

    if zero:
        print("\n■ ⛔ 메뉴판이 0건 — 처음부터 수집해야 한다 (%d곳)" % len(zero))
        for r in zero:
            print("   %-14s %-16s 가맹 %s" % (r["cat"], r["name"], r["f"] or "-"))

    if nopr:
        print("\n■ 가격이 0개 — 골격만 있다 (%d곳 · 메뉴 %d개)"
              % (len(nopr), sum(r["n"] for r in nopr)))
        for r in sorted(nopr, key=lambda x: -x["n"])[:12]:
            print("   %-16s 메뉴 %4d  가맹 %s" % (r["name"], r["n"], r["f"] or "-"))
        if len(nopr) > 12:
            print("   … 외 %d곳" % (len(nopr) - 12))

    if legacy:
        print("\n■ ⚠️ 옛 범용 수집기 잔재 — 전량 교체 대상 (%d곳)" % len(legacy))
        for r in sorted(legacy, key=lambda x: -x["legacy"])[:12]:
            print("   %-16s 잔재 %4d / 전체 %4d  가맹 %s"
                  % (r["name"], r["legacy"], r["n"], r["f"] or "-"))
        if len(legacy) > 12:
            print("   … 외 %d곳" % (len(legacy) - 12))

    todo, miss = pending(c)
    if miss:
        print("\n■ ❓ JSON 은 있는데 브랜드가 DB 에 없다 — 등록부터 (%d건)" % len(miss))
        for x in miss:
            print("   %-24s slug=%-16s %-16s 메뉴 %3d 가격 %3d  %s" % x)
    if todo:
        print("\n■ 🆕 아직 안 넣은 수집 JSON (%d건)" % len(todo))
        print("   %-24s %-14s %6s %6s %6s %6s  %s"
              % ("파일", "브랜드", "J메뉴", "J가격", "DB메뉴", "DB가격", "JSON시각"))
        for x in todo:
            print("   %-24s %-14s %6d %6d %6d %6d  %s" % x)
        print("\n   넣으려면:")
        for x in todo:
            print("   python scripts/brand_menu_import.py data/brand_menu_list/%s --apply" % x[0])
    if not todo and not miss:
        print("\n■ 수집 JSON — 미반영 없음 ✅")


if __name__ == "__main__":
    main()
