# -*- coding: utf-8 -*-
"""메뉴 **가격의 출처·지점**을 담는 자리. 2026-07-28
(`작업순서-2026-07-28.md` §메뉴 가격 수집·갱신 규칙)

    python scripts/menu_price_store.py            # 스키마 준비 + 현황
    python scripts/menu_price_store.py --changed  # 값이 바뀐 것만

왜 컬럼을 더 만드나
------------------
`brand_menu_official` 은 «지금 값» 한 칸만 갖고 있다. 그런데 규칙은 이렇다:

  · 플레이스는 **3개 지점**을 보고 2곳 이상 일치해야 채택한다
  · **세 값을 전부 저장한다** — 대푯값만 남기면 «왜 이 가격이지»를 못 푼다
  · **어느 지점에서 봤는지**(지점명·주소)를 같이 남긴다
  · 사람이 확정한 값(`decided_at`)은 자동 수집이 **건너뛴다**
  · 화면에 «공식 기준» / «매장 3곳 기준» 을 갈라 적어야 한다

🔴 **출처는 수집하는 순간에 같이 넣는다.** 나중에 붙이려면 전부 다시 확인해야 한다.

⛔ 프랜차이즈 가격이 지점마다 다르게 보이면 사고다(대표 지적 2026-07-28:
   *"맥도날드 가격은 지점마다 틀리면 난리남"*).
   그래서 **네이버 검색 결과(본사 권장가)를 1순위**로 쓰고,
   매장 페이지 값은 3곳을 모아 «2곳 이상 일치» 일 때만 쓴다.
"""
import io
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# source 값 — 섞이면 나중에 어느 값이 어디서 왔는지 알 수 없다
SRC_OFFICIAL = "official"    # 브랜드 공식 홈페이지
SRC_SEARCH = "naver_search"  # 네이버 **검색 결과** = 본사 권장가
SRC_PLACE = "naver_place"    # 네이버 **플레이스 매장** = 지점 가격 (3곳 합의 필요)
SRC_HUMAN = "human"          # 사람이 확정

ADD_COLS = [
    ("price_source", "TEXT"),      # 위 SRC_*
    ("price_note", "TEXT"),        # "지점별 차이 있음" 등 화면에 띄울 단서
    ("samples_json", "TEXT"),      # [{"price":..,"store":"..","addr":"..","at":".."}, ...]
    ("n_samples", "INTEGER"),      # 몇 곳에서 봤나
    ("agreed", "INTEGER"),         # 2곳 이상 일치했나 (1/0)
    ("prev_price", "INTEGER"),     # 직전 값 — 변동 감지용
    ("price_changed_at", "TEXT"),
    ("decided_at", "TEXT"),        # 사람이 확정한 시각 — 있으면 자동 수집이 건너뛴다
]


def connect():
    c = sqlite3.connect(DB, timeout=90)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=90000")
    except sqlite3.Error:
        pass
    have = {r[1] for r in c.execute("PRAGMA table_info(brand_menu_official)")}
    for col, typ in ADD_COLS:
        if col not in have:
            c.execute("ALTER TABLE brand_menu_official ADD COLUMN %s %s" % (col, typ))
    c.commit()
    return c


# 몇 개 지점을 봐야 하나 — **브랜드마다 다르다**
#   기본 3곳: 가맹 브랜드는 점주가 가격을 정할 수 있어 지점마다 다르다
#   1곳:      **직영 위주라 전국이 같은 값**인 곳 (대표 확인 2026-07-28: *"맥도날드는
#             지점 하나만 뚫으면 되 가격은 다 똑같아"*)
#  ⚠️ 여기에 브랜드를 넣을 땐 «전국 동일» 이라는 근거가 있어야 한다.
#     한 곳만 보고 전국값이라고 쓰는 게 제일 위험하다.
N_STORES = {"맥도날드": 1, "버거킹": 1}
N_STORES_DEFAULT = 3


def n_stores(brand_name):
    return N_STORES.get(brand_name, N_STORES_DEFAULT)


def decide(samples, need=N_STORES_DEFAULT):
    """지점 표본 → (채택가, 합의여부, 단서).

    · 2곳 이상 같으면 그 값
    · 다 다르면 **중앙값** + "지점별 차이 있음"
    · need=1 인 브랜드(전국 동일)는 한 곳으로 확정
    """
    # 🔴 **같은 매장을 여러 번 본 것은 한 곳이다** (2026-07-28 실제 발생).
    #    플레이스 폴백 경로가 항상 «첫 매장» 을 잡아서 3번 돌아도 store_id 가 같았다.
    #    그걸 그대로 세면 «3곳이 일치» 로 잘못 기록된다 — 근거가 없는데 있다고 쓰는 셈이다.
    seen, uniq = set(), []
    for s in samples or []:
        sid = s.get("store_id") or s.get("store")
        if sid in seen:
            continue
        seen.add(sid)
        uniq.append(s)
    samples = uniq
    ps = sorted(int(s["price"]) for s in samples if s.get("price"))
    if not ps:
        return None, 0, None
    if need == 1:                 # 전국 동일이 확인된 브랜드 — 한 곳이면 충분하다
        return ps[0], 1, None
    cnt = {}
    for p in ps:
        cnt[p] = cnt.get(p, 0) + 1
    top, n = max(cnt.items(), key=lambda x: (x[1], -x[0]))
    if n >= 2:
        return top, 1, None
    if len(ps) == 1:
        return ps[0], 0, "1개 지점에서만 확인"
    mid = ps[len(ps) // 2]
    return mid, 0, "지점별 차이 있음 (%s)" % " · ".join(format(p, ",") for p in ps)


def put(cur, brand_id, name, price, *, source, samples=None, note=None, now=None):
    """가격을 넣는다. **사람이 확정한 행은 건드리지 않는다.**"""
    row = cur.execute("""SELECT price, decided_at FROM brand_menu_official
                         WHERE brand_id=? AND name=?""", (brand_id, name)).fetchone()
    if row and row["decided_at"] and source != SRC_HUMAN:
        return "skip"                       # never-auto-overwrite-human-decisions
    prev = row["price"] if row else None
    changed = bool(prev and price and int(prev) != int(price))
    sj = json.dumps(samples, ensure_ascii=False) if samples else None
    if row:
        cur.execute("""UPDATE brand_menu_official SET price=?, price_source=?,
              price_note=?, samples_json=?, n_samples=?, agreed=?,
              prev_price=COALESCE(?,prev_price),
              price_changed_at=CASE WHEN ? THEN ? ELSE price_changed_at END,
              collected_at=? WHERE brand_id=? AND name=?""",
                    (price, source, note, sj, len(samples or []) or None,
                     1 if (samples and len(samples) >= 2 and not note) else 0,
                     prev if changed else None, 1 if changed else 0, now, now,
                     brand_id, name))
        return "changed" if changed else "same"
    cur.execute("""INSERT INTO brand_menu_official
        (brand_id,name,price,price_source,price_note,samples_json,n_samples,agreed,collected_at)
        VALUES(?,?,?,?,?,?,?,?,?)""",
                (brand_id, name, price, source, note, sj,
                 len(samples or []) or None,
                 1 if (samples and len(samples) >= 2 and not note) else 0, now))
    return "new"


def main():
    c = connect()
    cur = c.cursor()
    if "--changed" in sys.argv:
        rows = cur.execute("""SELECT b.name bn, o.name, o.prev_price, o.price, o.price_changed_at
            FROM brand_menu_official o JOIN brands b ON b.id=o.brand_id
            WHERE o.price_changed_at IS NOT NULL
            ORDER BY o.price_changed_at DESC LIMIT 60""").fetchall()
        print("값이 바뀐 메뉴 %d개\n" % len(rows))
        for r in rows:
            print("  %-12s %-26s %s → %s  (%s)"
                  % (r["bn"][:12], r["name"][:26], format(r["prev_price"] or 0, ","),
                     format(r["price"] or 0, ","), (r["price_changed_at"] or "")[:10]))
        return
    print("brand_menu_official 준비 완료 — 출처·지점 컬럼 %d개\n" % len(ADD_COLS))
    for r in cur.execute("""SELECT COALESCE(price_source,'(미기록)') s, COUNT(*) n
                            FROM brand_menu_official GROUP BY s ORDER BY n DESC"""):
        print("  %-14s %d줄" % (r["s"], r["n"]))
    n = cur.execute("SELECT COUNT(*) n FROM brand_menu_official WHERE decided_at IS NOT NULL"
                    ).fetchone()["n"]
    print("\n사람이 확정한 행 %d개 — 자동 수집이 건너뛴다" % n)


if __name__ == "__main__":
    main()
