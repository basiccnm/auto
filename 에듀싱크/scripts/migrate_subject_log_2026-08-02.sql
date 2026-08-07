-- 오늘 재밌었던 과목(2026-08-02) — 일일 퀘스트 셋째.
-- 성적표는 «잘하는 것»을 알려주지만 이건 «재밌어하는 것»을 알려준다.
-- add-only. 적용은 배포 지시 후(로컬·원격 둘 다 + 조회 확인).
CREATE TABLE IF NOT EXISTS subject_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  subject TEXT NOT NULL,           -- 시간표에 있던 과목명 그대로
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)           -- 하루 한 번
);
CREATE INDEX IF NOT EXISTS idx_subjlog_child ON subject_log (child_id, subject);
