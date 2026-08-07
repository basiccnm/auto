-- 되돌리기 — migrate_reroll_2026-08-08.sql
-- 「오늘 리롤을 썼다」는 기록만 사라진다. 미션 자체(mission_assign)는 안 건드린다.
DROP TABLE IF EXISTS mission_reroll;
