-- 되돌리기 — 컬럼 2개만 뗀다. 데이터는 안 움직인다.
-- ⚠ 옛 SQLite 는 DROP COLUMN 이 없다. D1 은 지원한다(2026-08 기준).
ALTER TABLE child_mode_config DROP COLUMN locked_until;
ALTER TABLE child_mode_config DROP COLUMN fail_count;
