# -*- coding: utf-8 -*-
"""메뉴판 **카테고리·순서** 테이블 + 브랜드 수집기의 **공통 적재 뼈대**. 2026-07-28 신설
(대표 지시: *"각 브랜드가 보여주는 것을 똑같이 지키는 게 맞다"* · *"메뉴의 순서도 같게"*)

왜 `brand_menu_official.category` 한 칸으로 안 되나
--------------------------------------------------
그 칸은 **문자열 하나**다. 실제 브랜드 메뉴판은 이렇게 생겼다:

  · 한 메뉴가 **여러 카테고리에 동시에** 걸린다 — bhc 뿌링클은 「치킨」과 「BHC시그니처」 양쪽에 있다.
    담을 자리가 없어서 지금은 `치킨 · BHC시그니처 · 뿌링클유니버스` 처럼 **이어붙여** 우회했고,
    그걸 다시 쪼개 읽다가 2026-07-28 오분류가 났다.
  · **순서가 정보다.** 홈페이지에서 왼쪽에 있는 탭이 그 가게 주력이고, 탭 안의 진열 순서도 브랜드가 정한 것이다.
    지금은 `sort_order` 가 아예 없어서 화면이 **비싼 순**(`ORDER BY price DESC`)으로 나간다.
  · 카테고리 자체가 **메뉴가 아닌데도 메뉴 행으로** 들어와 있다(BBQ `피자&버거 5,000원`).
    카테고리를 따로 들고 있으면 이런 행은 대조만으로 걸러진다.

그래서 셋으로 나눈다 — 사실(brand_menu_official) · 카테고리(brand_menu_cat) · 연결(menu_cat_link).
**분류는 `brand_menu_official` 에서 손을 뗀다.** 그 테이블의 `category` 는 원본이 없는 브랜드용 폴백일 뿐이다.

⛔ 수집기는 **자기 `brand_id` 밖을 건드리지 못한다.** 범용 수집기 10개가 같은 테이블에 쓰면서
   출처 없는 행 113건이 생겼다 — 그 사고를 코드로 막는 게 `replace_brand()` 다.
⛔ 사람이 확정한 것(`decided_at`)은 재수집이 덮지 않는다 (`never-auto-overwrite-human-decisions`).
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS brand_menu_cat (
  id         INTEGER PRIMARY KEY,
  brand_id   INTEGER NOT NULL,
  name       TEXT    NOT NULL,   -- 브랜드가 쓰는 말 그대로. 「뿌링클유니버스」도 그대로 둔다
  path       TEXT    NOT NULL,   -- 「치킨/뿌링클」 — 이게 식별자다 (구분자는 `/`)
  ext_id     TEXT,               -- 브랜드 쪽 식별자(bhc cateIdx 등) — 있으면
  parent_id  INTEGER,            -- 상위 카테고리. 없으면 최상위 탭
  sort_order INTEGER NOT NULL DEFAULT 0,   -- 형제들 사이의 순서. 왼쪽이 주력이다
  hidden     INTEGER NOT NULL DEFAULT 0,   -- 사람이 «이 탭은 빼자» 로 끈 것 (수집이 못 되돌린다)
  collector  TEXT,               -- 어느 스크립트가 넣었나 — 이상하면 여기부터 본다
  collected_at TEXT,
  -- 🔴 이름만으로는 못 구분한다 — bhc 는 「치킨 > 뿌링클」 과 「BHC시그니처 > 뿌링클」 이 **둘 다** 있다.
  --    그래서 키가 이름이 아니라 **경로**다.
  UNIQUE(brand_id, path)
);
CREATE INDEX IF NOT EXISTS ix_bmc_brand ON brand_menu_cat(brand_id, sort_order);
CREATE INDEX IF NOT EXISTS ix_bmc_par   ON brand_menu_cat(parent_id, sort_order);

CREATE TABLE IF NOT EXISTS menu_cat_link (
  brand_id   INTEGER NOT NULL,
  menu_name  TEXT    NOT NULL,   -- brand_menu_official.name 과 맞춘다(그 테이블 PK 가 이름이다)
  cat_id     INTEGER NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,   -- **그 카테고리 안에서** 몇 번째인가
  PRIMARY KEY(brand_id, menu_name, cat_id)
);
CREATE INDEX IF NOT EXISTS ix_mcl_cat ON menu_cat_link(cat_id, sort_order);
"""

# 재수집이 덮으면 안 되는 칸 — 사람이 확정했거나, 다른 작업이 채워둔 것
KEEP = ("menu_id", "agreed", "decided_at", "prev_price", "price_changed_at", "price_note")


def connect():
    c = sqlite3.connect(DB, timeout=90)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    return c


def ensure(c):
    """테이블·칸을 만든다. 여러 번 불러도 안전하다."""
    # 계층(`path`)이 없던 첫 판을 쓰던 중이면 갈아엎는다 — 내용은 수집기를 다시 돌리면 복구된다
    old = {r[1] for r in c.execute("PRAGMA table_info(brand_menu_cat)")}
    if old and "path" not in old:
        c.executescript("DROP TABLE IF EXISTS menu_cat_link; DROP TABLE IF EXISTS brand_menu_cat;")
        print("· brand_menu_cat 을 계층 구조로 새로 만든다 — 해당 브랜드 수집기를 다시 돌릴 것")
    c.executescript(SCHEMA)
    have = {r[1] for r in c.execute("PRAGMA table_info(brand_menu_official)")}
    # collector — 출처 추적. 이게 없어서 «후라이드 23,000» 이 어디서 왔는지 못 찾았다
    if "collector" not in have:
        c.execute("ALTER TABLE brand_menu_official ADD COLUMN collector TEXT")
    # sort_order — 카테고리가 없는 브랜드도 **홈페이지 나열 순서**는 지켜야 한다
    if "sort_order" not in have:
        c.execute("ALTER TABLE brand_menu_official ADD COLUMN sort_order INTEGER")
    # ext_id — 브랜드 쪽 메뉴 식별자(교촌 `view.asp?id`, BBQ 메뉴 id, bhc productCd).
    # 없으면 재수집 때 **이름으로만** 대조해야 한다 — 이름이 바뀌면 같은 메뉴인 줄 모른다
    if "ext_id" not in have:
        c.execute("ALTER TABLE brand_menu_official ADD COLUMN ext_id TEXT")
    # compose_raw — 브랜드가 적어준 **구성·토핑 원문**(피자 「주요토핑」, 피자헛 rpstDesc 등).
    # 재료를 채우는 **근거**로 쓴다. 우리가 해석한 값이 아니라 사이트가 쓴 말 그대로 담는다
    # (`ingredients-evidence-only` — 모르면 빈칸, 추측 금지)
    if "compose_raw" not in have:
        c.execute("ALTER TABLE brand_menu_official ADD COLUMN compose_raw TEXT")
    c.commit()


def brand_id(c, slug=None, name=None):
    q = "SELECT id FROM brands WHERE slug=?" if slug else "SELECT id FROM brands WHERE name=?"
    r = c.execute(q, (slug or name,)).fetchone()
    if not r:
        raise SystemExit("브랜드를 못 찾았다: %s" % (slug or name))
    return r[0]


def replace_brand(c, bid, cats, items, collector, dry=False):
    """브랜드 **한 곳의 메뉴판을 통째로 갈아끼운다.**

    cats  : [{"name","ext_id"(옵션),"parent"(옵션·**상위의 경로**)}]  ← 홈페이지 탭 순서 그대로
            ⚠️ 상위를 **먼저** 넣어야 한다(부모가 없으면 그 자식은 최상위로 붙는다).
    items : [{"name","price",... ,"cats":[카테고리명 …]}]             ← 홈페이지 나열 순서 그대로
            `cats` 는 그 메뉴가 걸린 카테고리 **전부**. 중복 진열도 그대로 담는다.
            🔴 한 메뉴가 카테고리마다 **다른 자리**에 있을 수 있다(「치킨」 3번째 · 「베스트」 1번째).
               그럴 땐 `("카테고리명", 그_안에서의_번호)` 로 준다. 이름만 주면 나열 순서를 쓴다.

    🔴 «갈아끼움» 이 필요한 이유 — 키가 `(brand_id, name)` 이라 다시 넣으면 같은 이름만 덮인다.
       `새로 나왔어요!` 처럼 **이번 수집에 없는 쓰레기 행은 영영 안 지워진다.**
       그래서 지우고 다시 넣되, 사람이 손댄 값(`KEEP`)은 이름으로 물려준다.
    """
    old = {r["name"]: r for r in c.execute(
        "SELECT * FROM brand_menu_official WHERE brand_id=?", (bid,))}
    # 사람이 끈 탭은 되살리지 않는다 (경로로 기억한다)
    hidden = {r["path"] for r in c.execute(
        "SELECT path FROM brand_menu_cat WHERE brand_id=? AND hidden=1", (bid,))}

    kept = sum(1 for it in items if it["name"] in old)
    gone = [n for n in old if n not in {it["name"] for it in items}]
    decided = [n for n in gone if old[n]["decided_at"]]

    print("· 기존 %d행 → 새 %d행 (이어받음 %d · 사라짐 %d)"
          % (len(old), len(items), kept, len(gone)))
    if gone:
        print("  사라지는 행: %s%s" % (", ".join(gone[:8]), " …" if len(gone) > 8 else ""))
    if decided:
        # 사람이 확정한 행이 새 수집에 없다 = 수집이 덜 됐을 수 있다. 지우기 전에 눈에 띄게 알린다
        print("  ⚠️ 사람이 확정한 행이 새 수집에 없다: %s" % ", ".join(decided))
    if dry:
        print("(dry — DB 미반영)")
        return {"kept": kept, "gone": gone, "decided_gone": decided}

    c.execute("DELETE FROM menu_cat_link  WHERE brand_id=?", (bid,))
    c.execute("DELETE FROM brand_menu_cat WHERE brand_id=?", (bid,))
    c.execute("DELETE FROM brand_menu_official WHERE brand_id=?", (bid,))

    # 카테고리는 **경로**(「치킨/뿌링클」)로 식별한다. `parent` 는 상위의 경로를 준다.
    cat_id, pos = {}, {}
    for ct in cats:
        nm = (ct["name"] or "").strip()
        par = (ct.get("parent") or "").strip() or None
        if not nm:
            continue
        path = "%s/%s" % (par, nm) if par else nm
        if path in cat_id:
            continue
        pos[par] = pos.get(par, -1) + 1          # 순서는 **형제들 사이에서** 센다
        c.execute("""INSERT INTO brand_menu_cat
                     (brand_id,name,path,ext_id,parent_id,sort_order,hidden,collector,collected_at)
                     VALUES(?,?,?,?,?,?,?,?,datetime('now'))""",
                  (bid, nm, path, ct.get("ext_id"), cat_id.get(par), pos[par],
                   1 if path in hidden else 0, collector))
        cat_id[path] = c.execute("SELECT last_insert_rowid()").fetchone()[0]

    within, kept_price = {}, [0]
    for i, it in enumerate(items):
        nm = it["name"]
        o = old.get(nm)
        keep = {k: (o[k] if o else None) for k in KEEP}
        # 수집기가 메모를 주면 그걸 쓴다 — 「19,000원+4,000원(본품+옵션)」 처럼
        # 가격 한 칸에 안 들어가는 정보를 버리지 않기 위한 자리다
        if it.get("price_note"):
            keep["price_note"] = it["price_note"]
        # 사람이 확정한 판매가는 새로 받은 값으로 덮지 않는다
        price = o["price"] if (o and o["decided_at"]) else it.get("price")
        psrc = it.get("price_source")
        # 🔴 **가격을 못 받았다고 있던 값을 지우지 않는다** (2026-07-28 맘스터치).
        #    수집은 «골격 먼저, 가격은 나중에» 두 단계다. 골격을 다시 받았더니 가격이 없다고
        #    기존 129개를 0으로 만들면, 다시 채우기 전까지 화면이 통째로 「가격 확인 중」이 된다.
        #    브랜드가 값을 내렸는지 우리가 못 읽었는지 구분할 수 없으니 **지키는 쪽**을 고른다.
        if price is None and o and o["price"] is not None:
            price, psrc = o["price"], o["price_source"]
            kept_price[0] += 1
        c.execute("""INSERT INTO brand_menu_official
            (brand_id,name,category,price,weight_raw,weight_g,origin_raw,allergy_raw,
             detail_url,image_url,menu_id,collected_at,price_source,price_note,
             agreed,prev_price,price_changed_at,decided_at,category_raw,collector,sort_order,
             ext_id,compose_raw)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,?,?,?,?,?,?,?,?)""",
            (bid, nm, it.get("category"), price, it.get("weight_raw"), it.get("weight_g"),
             it.get("origin_raw"), it.get("allergy_raw"), it.get("detail_url"),
             it.get("image_url"), keep["menu_id"], psrc, keep["price_note"],
             keep["agreed"], keep["prev_price"], keep["price_changed_at"], keep["decided_at"],
             it.get("category"), collector, i, it.get("ext_id"), it.get("compose_raw")))
        for cn in (it.get("cats") or []):
            pos = None
            if isinstance(cn, (tuple, list)):        # ("치킨", 3) 처럼 자리를 함께 준 경우
                cn, pos = cn[0], cn[1]
            cn = (cn or "").strip()
            if cn not in cat_id:
                continue
            k = cat_id[cn]
            within[k] = within.get(k, -1) + 1
            c.execute("""INSERT OR REPLACE INTO menu_cat_link
                         (brand_id,menu_name,cat_id,sort_order) VALUES(?,?,?,?)""",
                      (bid, nm, k, within[k] if pos is None else pos))
    c.commit()

    n_link = c.execute("SELECT count(*) FROM menu_cat_link WHERE brand_id=?", (bid,)).fetchone()[0]
    nocat = c.execute("""SELECT count(*) FROM brand_menu_official o WHERE o.brand_id=?
                         AND NOT EXISTS(SELECT 1 FROM menu_cat_link l
                                        WHERE l.brand_id=o.brand_id AND l.menu_name=o.name)""",
                      (bid,)).fetchone()[0]
    if kept_price[0]:
        print("  · 새 수집에 가격이 없어 **옛 가격을 지킨 행 %d개**" % kept_price[0])
    print("✅ 카테고리 %d · 메뉴 %d · 연결 %d (카테고리 없는 메뉴 %d)"
          % (len(cat_id), len(items), n_link, nocat))
    return {"kept": kept, "gone": gone, "decided_gone": decided, "cats": len(cat_id),
            "items": len(items), "links": n_link, "nocat": nocat}


def board_of(c, bid):
    """화면용 — **브랜드 순서 그대로** 계층을 돌려준다.

        [{"name": "치킨", "rows": [...], "subs": [{"name":"후라이드","rows":[...]}, …]}, …]

    원본 카테고리가 없는 브랜드면 빈 리스트 → 부르는 쪽이 표준 탭으로 폴백한다.
    """
    cats = c.execute("""SELECT id,name,parent_id FROM brand_menu_cat
                        WHERE brand_id=? AND hidden=0
                        ORDER BY sort_order, id""", (bid,)).fetchall()
    if not cats:
        return []

    def rows_of(cid):
        return c.execute("""SELECT o.* FROM menu_cat_link l
                            JOIN brand_menu_official o
                              ON o.brand_id=l.brand_id AND o.name=l.menu_name
                            WHERE l.cat_id=? ORDER BY l.sort_order""", (cid,)).fetchall()

    kids = {}
    for ct in cats:
        if ct["parent_id"]:
            kids.setdefault(ct["parent_id"], []).append(ct)
    out = []
    for ct in cats:
        if ct["parent_id"]:
            continue
        rows = rows_of(ct["id"])
        subs = [{"name": s["name"], "rows": rows_of(s["id"])} for s in kids.get(ct["id"], [])]
        subs = [s for s in subs if s["rows"]]
        if rows or subs:
            out.append({"name": ct["name"], "rows": rows, "subs": subs})
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    c = connect()
    ensure(c)
    print("테이블 준비 완료 — brand_menu_cat · menu_cat_link · collector/sort_order 칸")
    for r in c.execute("""SELECT b.name, count(DISTINCT m.id) c, count(l.cat_id) l
                          FROM brands b
                          LEFT JOIN brand_menu_cat m ON m.brand_id=b.id
                          LEFT JOIN menu_cat_link  l ON l.brand_id=b.id
                          GROUP BY b.id HAVING c>0 ORDER BY c DESC"""):
        print("  %-14s 카테고리 %d · 연결 %d" % (r[0], r[1], r[2]))
