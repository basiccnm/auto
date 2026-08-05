# -*- coding: utf-8 -*-
"""브랜드의 **메뉴판만** 비운다 — 브랜드 자체는 남긴다. 2026-07-31 신설

    python scripts/brand_board_reset.py 도미노피자 죠스떡볶이        # 미리보기(기본)
    python scripts/brand_board_reset.py 도미노피자 --apply
    python scripts/brand_board_reset.py --junk                     # 쓰레기 골격을 한 번에 찾아준다
    python scripts/brand_board_reset.py --junk --apply

왜 만들었나
----------
옛 범용 수집기가 홈페이지의 **UI 글자**를 메뉴로 담아둔 곳이 있다. 실제로 본 것:

    도미노피자   → `KOR`, `close`
    죠스떡볶이   → `웹사이트`
    국대떡볶이   → `copyright gabia.inc (주)가비아`
    북촌손만두   → `닫기버튼`
    놀부부대찌개  → `Logo`, `banner`, `인테리어`

이건 «가격이 없는 메뉴» 가 아니라 **메뉴가 아닌 것**이다. 그대로 두면 브랜드 페이지에
「메뉴 2개 · close」 가 뜬다 — 한 줄만 이상해도 그 브랜드 페이지 전체를 못 믿게 된다.
재수집을 시키기 전에 자리를 비워두는 게 맞다.

⛔ **`menus`(우리가 원가를 낸 메뉴)는 건드리지 않는다.** 사람이 재료를 하나씩 확인한 작업물이다.
   메뉴판 줄에 그 연결(`menu_id`)이 붙어 있으면 **기본적으로 거부**한다 — `--force` 를 명시해야 한다.
⛔ 되돌릴 수 없다. 그래서 기본은 미리보기이고 지울 줄을 전부 출력한다.

비운 뒤에는:
    1) 수집기 세션에 그 브랜드 재수집을 지시
    2) python scripts/brand_menu_import.py data/brand_menu_list/<slug>.json --apply
    3) python scripts/publish.py --apply --menu-only
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

# 🔴 «골격이 깨졌다» 고 볼 기준 — 여기에 걸린 것만 --junk 가 집어준다.
#    ⚠️ 넉넉히 잡지 않는다. 진짜 메뉴를 지우면 되돌릴 수 없다.
JUNK_MAX = 5          # 이 개수 이하면서
JUNK_ALL_LEGACY = 1   # 전부 옛 범용 수집기(collector IS NULL) 가 담은 것일 때만


def board_of(c, bid):
    return c.execute("""SELECT o.name, o.price, o.menu_id, o.collector
                        FROM brand_menu_official o WHERE o.brand_id=?
                        ORDER BY o.rowid""", (bid,)).fetchall()


def find_junk(c):
    out = []
    for b in c.execute("SELECT id,name FROM brands WHERE published=1 ORDER BY id"):
        rows = board_of(c, b["id"])
        if not rows or len(rows) > JUNK_MAX:
            continue
        if JUNK_ALL_LEGACY and any(r["collector"] for r in rows):
            continue
        out.append((b["id"], b["name"], rows))
    return out


def wipe(c, bid, apply_):
    n1 = c.execute("SELECT count(*) FROM menu_cat_link WHERE brand_id=?", (bid,)).fetchone()[0]
    n2 = c.execute("SELECT count(*) FROM brand_menu_cat WHERE brand_id=?", (bid,)).fetchone()[0]
    n3 = c.execute("SELECT count(*) FROM brand_menu_official WHERE brand_id=?",
                   (bid,)).fetchone()[0]
    if apply_:
        c.execute("DELETE FROM menu_cat_link WHERE brand_id=?", (bid,))
        c.execute("DELETE FROM brand_menu_cat WHERE brand_id=?", (bid,))
        c.execute("DELETE FROM brand_menu_official WHERE brand_id=?", (bid,))
    return n1, n2, n3


def main():
    argv = sys.argv[1:]
    apply_ = "--apply" in argv
    force = "--force" in argv
    junk = "--junk" in argv
    names = [a for a in argv if not a.startswith("--")]
    if not names and not junk:
        raise SystemExit(__doc__)

    c = store.connect()
    targets = []
    if junk:
        for bid, nm, rows in find_junk(c):
            targets.append((bid, nm, rows))
    for key in names:
        b = c.execute("SELECT id,name FROM brands WHERE name=? OR slug=?", (key, key)).fetchone()
        if not b:
            cand = [r["name"] for r in
                    c.execute("SELECT name FROM brands WHERE name LIKE ?", ("%" + key + "%",))]
            raise SystemExit("브랜드를 못 찾았다: %s%s"
                             % (key, ("\n비슷한 것: " + ", ".join(cand)) if cand else ""))
        if not any(t[0] == b["id"] for t in targets):
            targets.append((b["id"], b["name"], board_of(c, b["id"])))

    if not targets:
        print("비울 것이 없다 ✅")
        return

    print("=" * 70)
    print("메뉴판을 비울 브랜드 %d곳 — 브랜드·원가메뉴는 남는다" % len(targets))
    print("=" * 70)
    linked = []
    for bid, nm, rows in targets:
        mk = [r for r in rows if r["menu_id"]]
        if mk:
            linked.append(nm)
        print("\n● %-16s %d줄%s" % (nm, len(rows), "  🔴 원가 연결 %d" % len(mk) if mk else ""))
        for r in rows:
            print("     · %-34s %s" % ((r["name"] or "")[:34],
                                       ("%s원" % r["price"]) if r["price"] else ""))

    if not apply_:
        print("\n(안 지웠다 — 실제로 지우려면 --apply)")
        return
    if linked and not force:
        raise SystemExit("\n❌ 원가 메뉴와 이어진 줄이 있다: %s\n"
                         "   연결이 끊기면 그 원가 메뉴가 메뉴판에서 사라진다.\n"
                         "   정말 비우려면 --force 를 함께 줄 것." % ", ".join(linked))

    tot = [0, 0, 0]
    for bid, nm, rows in targets:
        a, b_, d = wipe(c, bid, True)
        tot[0] += a
        tot[1] += b_
        tot[2] += d
        print("   %-16s 메뉴 %d · 탭 %d · 연결 %d 지움" % (nm, d, b_, a))
    c.commit()
    print("\n✅ 메뉴 %d줄 · 탭 %d개 · 연결 %d개 지웠다" % (tot[2], tot[1], tot[0]))
    print("\n다음: 수집기에 재수집 지시 → brand_menu_import.py → publish.py --apply --menu-only")


if __name__ == "__main__":
    main()
