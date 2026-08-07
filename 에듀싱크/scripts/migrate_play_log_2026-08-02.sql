-- 오늘 누구랑 놀았어(2026-08-02) — 부모가 제일 모르는 것, 아이가 먼저 말하지 않는 것.
-- 받는 건 이름 문자열 하나뿐이다. 성별·연락처·학교 아무것도 받지 않는다.
-- add-only. 적용은 배포 지시 후(로컬·원격 둘 다 + 조회 확인).

-- 아이가 넣어둔 친구 이름 — 다음부터는 칩으로 떠서 탭만 하면 된다(타이핑은 처음 한 번뿐)
CREATE TABLE IF NOT EXISTS kid_friends (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (child_id, name)
);

-- 그날 미션을 했는지 + 혼자였는지. 하루 한 번(UNIQUE)
CREATE TABLE IF NOT EXISTS play_days (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  alone INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)
);

-- 누구와 놀았는지 — 하루에 여러 명이면 여러 줄
CREATE TABLE IF NOT EXISTS play_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_playlog_child ON play_log (child_id, ymd);
CREATE INDEX IF NOT EXISTS idx_playlog_name ON play_log (child_id, name);
