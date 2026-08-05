# -*- coding: utf-8 -*-
"""네이버 수집분 자체 검수 (2026-07-20)

왜 만들었나: 오늘 내내 반쯤 깨진 표를 대표님께 드렸고, 대표님이 하나씩 짚어주셨다.
  · 느타리버섯 도매 29,000원  (실제 3,000원)
  · 마늘양파 10원/kg          (주방용품 보관망)
  · 고기패티 1,060,800원/kg   (묶음 오독)
  · 밀떡 75kg                 (3.75kg의 소수점 유실)
그건 역할이 뒤바뀐 것이라, **보여드리기 전에 스스로 걸러내는** 검사를 여기 모은다.
audit_dishes.py와 같은 취지다.

  python scripts/naver_audit.py            전체
  python scripts/naver_audit.py --fix      걸린 건 usable=0으로 내림
"""
import argparse
import os
import sqlite3
import statistics as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# 가정용 식재료가 이 값을 넘으면 사람이 봐야 한다 (원/kg)
ABS_MAX = 300000      # 사프란·트러플 아니면 이 위는 없다
ABS_MIN = 200         # kg당 200원 미만은 식재료가 아니다


def audit(con, fix=False):
    cur = con.cursor()
    found = []

    def flag(kind, rid, msg):
        found.append((kind, rid, msg))
        if fix and rid:
            cur.execute("UPDATE naver_offer SET usable=0 WHERE rowid=?", (rid,))

    rows = cur.execute("""SELECT o.rowid rid, i.name inm, o.tier, o.pack_qty q, o.pack_unit u,
        o.price, o.per_unit per, o.title, o.usable
        FROM naver_offer o JOIN ingredients i USING(ingredient_key)""").fetchall()

    # ① 절대 상식 벗어난 단가
    for rid, inm, tier, q, u, price, per, title, usable in rows:
        if not usable:
            continue
        if per > ABS_MAX:
            flag("과대", rid, f'{inm} {round(per):,}원/{u} — {title[:40]}')
        elif per < ABS_MIN:
            flag("과소", rid, f'{inm} {round(per):,}원/{u} — {title[:40]}')

    # ② 재료별 중앙값 대비 이상치
    g = {}
    for rid, inm, tier, q, u, price, per, title, usable in rows:
        if usable:
            g.setdefault(inm, []).append(per)
    med = {k: st.median(v) for k, v in g.items() if len(v) >= 3}
    for rid, inm, tier, q, u, price, per, title, usable in rows:
        if not usable or inm not in med:
            continue
        m = med[inm]
        if per > m * 4 or per < m * 0.25:
            flag("이상치", rid, f'{inm} {round(per):,} (기준 {round(m):,}) — {title[:36]}')

    # ③ 구간 역전 — 업소용이 가정용보다 비싸면 표본이 잘못됐다
    con.row_factory = sqlite3.Row
    c2 = con.cursor()
    for r in c2.execute("""SELECT i.ingredient_key k, i.name FROM ingredients i
                           WHERE EXISTS(SELECT 1 FROM naver_offer WHERE ingredient_key=i.ingredient_key)""").fetchall():
        def m(t):
            v = [x[0] for x in c2.execute(
                "SELECT per_unit FROM naver_offer WHERE ingredient_key=? AND tier=? AND usable=1",
                (r["k"], t))]
            return (st.median(v), len(v)) if v else None
        h, b = m("가정용"), m("업소용")
        if h and b and b[0] >= h[0]:
            found.append(("역전", None,
                          f'{r["name"]} 가정용 {round(h[0]):,}({h[1]}건) ≤ 업소용 {round(b[0]):,}({b[1]}건)'))

    # ④ 표본이 1건뿐인 구간 — 중앙값이라 부를 수 없다
    for r in c2.execute("""SELECT i.name, o.tier, COUNT(*) n FROM naver_offer o
        JOIN ingredients i USING(ingredient_key) WHERE o.usable=1
        GROUP BY o.ingredient_key, o.tier HAVING n=1"""):
        found.append(("표본1", None, f'{r["name"]} {r["tier"]} 1건뿐'))

    if fix:
        con.commit()
    return found


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fix", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    found = audit(con, a.fix)
    con.close()
    if not found:
        print("✅ 이상 없음")
        return
    from collections import Counter
    cnt = Counter(k for k, _, _ in found)
    print(f"⚠️ {len(found)}건\n")
    for k, n in cnt.most_common():
        print(f"  {k:<6}{n:>5}건")
    print()
    shown = Counter()
    for k, rid, msg in found:
        if shown[k] < 5:
            print(f"  [{k}] {msg}")
            shown[k] += 1
    if a.fix:
        print(f"\n→ 과대·과소·이상치는 usable=0 처리했습니다 (역전·표본1은 표시만)")


if __name__ == "__main__":
    main()
