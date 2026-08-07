-- ============================================================
-- 🎲 미션 리롤 (하루 1회) — 지시서 §5② 「자율성 리롤」 (2026-08-08)
-- ============================================================
--
-- 왜 표를 따로 두나
--   «하루 한 번»을 화면이 세면 앱을 껐다 켜서 우회된다(상점 상한·PIN 과 같은 이유).
--   그런데 세는 로직을 서버에 또 쓰면 그 로직이 틀릴 수 있다 →
--   **PRIMARY KEY (child_id, ymd) 가 «하루 한 번»을 자연히 강제**하게 만든다.
--   INSERT 가 성공하면 오늘 처음이고, 실패하면 이미 쓴 것이다. 셀 것이 없다.
--
-- ⚠ 되돌리기: rollback_reroll_2026-08-08.sql (DROP 한 줄, 데이터 안 움직임)
-- ⚠ 이 표는 «썼나 안 썼나»만 기억한다. 무엇으로 바뀌었는지는 mission_assign 이 갖고 있다.

CREATE TABLE IF NOT EXISTS mission_reroll (
  child_id   INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  ymd        TEXT NOT NULL,          -- KST 기준 YYYYMMDD (아이의 «오늘»)
  created_at TEXT NOT NULL,
  PRIMARY KEY (child_id, ymd)
);
