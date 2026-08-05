# -*- coding: utf-8 -*-
"""메뉴 **사진** 테이블. 2026-07-28 신설 (대표 지시: *"이미지 DB도 구성해"*)

왜 `brand_menu_official.image_url` 한 칸으로 안 되나
------------------------------------------------
그 칸은 **브랜드가 준 주소 하나**만 담는다. 실제로는 이렇게 된다:

  · 한 메뉴에 사진이 여러 장이다 (목록 썸네일 / 상세 대표컷 / 세트 구성컷)
  · 주소가 **바뀌거나 죽는다** — 브랜드가 시즌마다 CDN 경로를 갈아엎는다
  · 우리가 **R2 로 옮겨 담아야** 한다 (핫링크는 언젠가 끊기고 남의 트래픽을 쓴다)
  · 어디서 봤는지(**근거**)가 없으면 나중에 검증이 안 된다 (`ingredients-evidence-only`)

그래서 «후보 여러 장 → 고른 한 장 → R2 로 옮김» 세 단계를 **상태로** 들고 간다.

  status  found     주소만 찾음 (아직 안 받음)
          fetched   내려받아 크기·해시까지 확인
          uploaded  R2 에 올림 — 이때만 화면에 쓴다
          rejected  로고·아이콘·깨진 파일 등 (why 에 이유)

⛔ `status='uploaded'` 가 아닌 행은 **화면에 쓰지 않는다.** 핫링크 금지.
⛔ 사람이 고른 것(`picked_by='human'`)은 자동 수집이 덮지 않는다
   (`never-auto-overwrite-human-decisions`).
"""
import hashlib
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS menu_image (
  id          INTEGER PRIMARY KEY,
  brand_id    INTEGER NOT NULL,
  menu_name   TEXT    NOT NULL,   -- 공식 표기 그대로. brand_menu_official.name 과 맞춘다
  menu_id     INTEGER,            -- 우리가 원가를 낸 메뉴면 menus.id
  src_url     TEXT    NOT NULL,   -- 원본 주소(브랜드 공식)
  src_page    TEXT,               -- 어느 페이지에서 봤나 — 근거
  alt_raw     TEXT,               -- alt/title 원문
  match_how   TEXT,               -- alt | near | order  (어떻게 이 메뉴로 판정했나)
  score       INTEGER DEFAULT 0,  -- 높을수록 확실. 대표컷 고를 때 쓴다
  width       INTEGER,
  height      INTEGER,
  bytes       INTEGER,
  sha1        TEXT,               -- 같은 사진이 여러 메뉴에 붙는 걸 잡는다
  r2_key      TEXT,               -- menu/{brand_slug}/{slug}.webp
  status      TEXT    DEFAULT 'found',
  picked      INTEGER DEFAULT 0,  -- 이 메뉴의 대표컷이면 1
  picked_by   TEXT,               -- human | auto
  why         TEXT,               -- rejected 사유 등
  collected_at TEXT,
  UNIQUE(brand_id, menu_name, src_url)
);
CREATE INDEX IF NOT EXISTS ix_mimg_brand  ON menu_image(brand_id);
CREATE INDEX IF NOT EXISTS ix_mimg_status ON menu_image(status);
CREATE INDEX IF NOT EXISTS ix_mimg_pick   ON menu_image(brand_id, menu_name, picked);
CREATE INDEX IF NOT EXISTS ix_mimg_sha1   ON menu_image(sha1);
"""

# 로고·아이콘·장식은 메뉴 사진이 아니다. 주소만 봐도 대부분 걸러진다.
RX_JUNK = re.compile(
    r"(logo|icon|sprite|bg_|_bg|banner|btn_|button|arrow|dummy|blank|noimg|no_image"
    r"|placeholder|favicon|common/|/ui/|loading|spinner|share|sns|kakao|facebook"
    r"|instagram|youtube|naver|badge|new\.|hot\.|best\.)", re.I)
RX_IMGEXT = re.compile(r"\.(jpe?g|png|webp|avif)(\?|$)", re.I)


def connect():
    # 🔴 수집기(크롬 여러 개)와 내려받기가 **동시에 쓴다** → 기본 rollback journal 이면
    #    `database is locked` 로 죽는다(2026-07-28). WAL 은 읽기와 쓰기를 겹칠 수 있게 해준다.
    #    timeout 은 «잠겨 있으면 이만큼 기다린다» 는 뜻 — 바로 포기하지 않게 넉넉히 준다.
    c = sqlite3.connect(DB, timeout=90)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=90000")
    except sqlite3.Error:
        pass
    c.executescript(SCHEMA)
    return c


def norm_name(s):
    """메뉴명 비교용 — 공백·구두점·사이즈 꼬리표를 턴다."""
    s = re.sub(r"™|®|\(.*?\)|\[.*?\]", "", s or "")
    s = re.sub(r"\s+|[·,\-_/]", "", s)
    return s.lower()


def looks_like_photo(url):
    """메뉴 사진일 법한 주소인가. 확실하지 않으면 **버린다** — 로고가 섞이면 화면이 망가진다."""
    if not url or url.startswith("data:"):
        return False
    if RX_JUNK.search(url):
        return False
    return bool(RX_IMGEXT.search(url))


def add(cur, brand_id, menu_name, src_url, *, src_page=None, alt_raw=None,
        match_how=None, score=0, menu_id=None, now=None):
    """후보 한 장 기록. 이미 있으면 **점수가 더 높을 때만** 갱신한다."""
    cur.execute("""INSERT INTO menu_image
        (brand_id,menu_name,src_url,src_page,alt_raw,match_how,score,menu_id,collected_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(brand_id,menu_name,src_url) DO UPDATE SET
          score      = MAX(menu_image.score, excluded.score),
          match_how  = CASE WHEN excluded.score > menu_image.score
                            THEN excluded.match_how ELSE menu_image.match_how END,
          src_page   = COALESCE(menu_image.src_page, excluded.src_page),
          alt_raw    = COALESCE(menu_image.alt_raw, excluded.alt_raw),
          menu_id    = COALESCE(menu_image.menu_id, excluded.menu_id)""",
                (brand_id, menu_name, src_url, src_page, alt_raw, match_how,
                 score, menu_id, now))


def sha1_of(blob):
    return hashlib.sha1(blob).hexdigest()


def pick_best(cur, brand_id, menu_name):
    """대표컷 자동 선정. **사람이 고른 게 있으면 건드리지 않는다.**"""
    h = cur.execute("""SELECT 1 FROM menu_image
        WHERE brand_id=? AND menu_name=? AND picked=1 AND picked_by='human'""",
                    (brand_id, menu_name)).fetchone()
    if h:
        return None
    row = cur.execute("""SELECT id FROM menu_image
        WHERE brand_id=? AND menu_name=? AND status<>'rejected'
        ORDER BY score DESC, COALESCE(width,0)*COALESCE(height,0) DESC, id
        LIMIT 1""", (brand_id, menu_name)).fetchone()
    if not row:
        return None
    cur.execute("UPDATE menu_image SET picked=0 WHERE brand_id=? AND menu_name=?",
                (brand_id, menu_name))
    cur.execute("UPDATE menu_image SET picked=1, picked_by='auto' WHERE id=?", (row["id"],))
    return row["id"]


def stats(cur):
    q = """SELECT b.name bn,
             COUNT(DISTINCT i.menu_name) menus,
             COUNT(*) shots,
             SUM(i.status='uploaded') up
           FROM menu_image i JOIN brands b ON b.id=i.brand_id
           GROUP BY i.brand_id ORDER BY menus DESC"""
    return cur.execute(q).fetchall()


if __name__ == "__main__":
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    c = connect()
    print("menu_image 준비 완료")
    rows = stats(c.cursor())
    if not rows:
        print("  아직 비어 있음 — menu_image_collect.py 로 채운다")
    for r in rows:
        print("  %-18s 메뉴 %3d · 사진 %4d · 업로드 %3d"
              % (r["bn"][:18], r["menus"], r["shots"], r["up"] or 0))
