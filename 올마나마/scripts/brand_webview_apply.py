# -*- coding: utf-8 -*-
"""브라우저에서 뽑은 «이름<TAB>가격» 을 메뉴판에 넣는다. 2026-07-28

    python scripts/brand_webview_apply.py 설빙 data/webview/설빙.tsv --apply

왜 두 단계인가
------------
SPA(Nuxt·Next)는 탭 전환이 클라이언트 라우팅이라 헤드리스로는 **첫 탭만** 받는다.
설빙이 146개인데 13개만 나왔다. 그래서 탭 누르기는 브라우저(`brand_webview_tabs.js`)가 하고,
**저장은 이 스크립트가** 한다 — 저장 규칙(사람확정 보존·변동 보고)을 한 곳에 둔다.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    bname, path = sys.argv[1], sys.argv[2]
    apply_ = "--apply" in sys.argv
    rows = []
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        nm = parts[0].strip()
        try:
            pr = int(re.sub(r"[^\d]", "", parts[1]))
        except ValueError:
            continue
        if nm and 500 <= pr <= 300000:
            rows.append((nm, pr))
    print("● %s — 읽은 메뉴 %d개" % (bname, len(rows)))
    if not rows:
        print("  🔴 0개 — 파일이 비었거나 형식이 다르다")
        return

    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (bname,)).fetchone()
    if not br:
        print("  🔴 DB 에 «%s» 브랜드가 없다" % bname)
        return
    if not apply_:
        for nm, pr in rows[:12]:
            print("   %-30s %s원" % (nm[:30], format(pr, ",")))
        print("  (미저장 — --apply)")
        return
    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    st, changed = {"new": 0, "changed": 0, "same": 0, "skip": 0}, []
    for nm, pr in rows:
        before = cur.execute("""SELECT price FROM brand_menu_official
                                WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
        r = PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL,
                   note="공식 앱(웹뷰) 기준", now=now)
        db.commit()                        # 한 건씩 즉시 저장
        st[r] = st.get(r, 0) + 1
        if r == "changed":
            changed.append((nm, before["price"], pr))
    print("  저장: 새로 %d · **바뀜 %d** · 그대로 %d · 사람확정 건너뜀 %d"
          % (st["new"], st["changed"], st["same"], st["skip"]))
    for nm, a, b in changed[:20]:          # 값이 바뀐 것만 보고
        print("    💰 %-26s %s → %s" % (nm[:26], format(a or 0, ","), format(b, ",")))


if __name__ == "__main__":
    main()
