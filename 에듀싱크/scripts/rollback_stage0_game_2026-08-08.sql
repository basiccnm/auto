-- ════════════════════════════════════════════════════════════════════
--  되돌리기 — STAGE 0 게임 미션 뼈대 (2026-08-08)
--
--  ⚠ SQLite 는 DROP COLUMN 이 되지만 D1 버전에 따라 막힐 수 있다.
--    막히면 칼럼은 그대로 두고(기본값이라 무해하다) 새 표만 지우면 된다 —
--    아래를 위에서부터 한 문장씩 돌리고, 실패하는 줄은 건너뛴다.
--  ⚠ BEGIN TRANSACTION 을 쓰지 않는다(원격 D1 거부).
-- ════════════════════════════════════════════════════════════════════

DROP INDEX IF EXISTS idx_qal_wrong;
DROP INDEX IF EXISTS idx_league_rank;
DROP TABLE IF EXISTS child_badges;
DROP TABLE IF EXISTS league_standing;

-- 오늘의 미션 세션 — 재도전 없던 원래 모양으로
DROP TABLE IF EXISTS quiz_session;
CREATE TABLE quiz_session (
  child_id    INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  ymd         TEXT NOT NULL,
  codes       TEXT NOT NULL,
  answered    INTEGER NOT NULL DEFAULT 0,
  correct     INTEGER NOT NULL DEFAULT 0,
  coins       INTEGER NOT NULL DEFAULT 0,
  finished_at TEXT,
  created_at  TEXT NOT NULL,
  PRIMARY KEY (child_id, ymd)
);

ALTER TABLE children ADD COLUMN _drop_ignore INTEGER; -- (자리표시 — 아래가 막힐 때 파일이 통째로 죽지 않게)
ALTER TABLE children       DROP COLUMN streak_ymd;
ALTER TABLE children       DROP COLUMN streak_days;
ALTER TABLE children       DROP COLUMN level_missions;
ALTER TABLE children       DROP COLUMN avatar_slot;
ALTER TABLE children       DROP COLUMN _drop_ignore;

ALTER TABLE star_ledger    DROP COLUMN bucket;

ALTER TABLE quiz_questions DROP COLUMN tier;
ALTER TABLE quiz_questions DROP COLUMN points;
ALTER TABLE quiz_questions DROP COLUMN sec;
ALTER TABLE quiz_questions DROP COLUMN image_url;
ALTER TABLE quiz_questions DROP COLUMN kind;
ALTER TABLE quiz_questions DROP COLUMN pack_id;

ALTER TABLE mission_assign DROP COLUMN points;
ALTER TABLE missions       DROP COLUMN points;
ALTER TABLE missions       DROP COLUMN pack_id;

DROP TABLE IF EXISTS packs;
