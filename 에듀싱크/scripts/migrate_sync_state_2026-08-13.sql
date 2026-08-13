-- 자녀 학교 자동 갱신 (2026-08-13 대표님 「학교일정·시간표·급식을 자동으로 가져오게 돌려야 해」)
-- sync_state 는 여태 학사일정 시각 하나만 들고 있었다. 급식·시간표 시각을 따로 둔다
-- — 셋이 주기가 다르기 때문이다(급식 12시간 · 일정 3일 · 시간표 3일).
--
-- 적용:  npx wrangler d1 execute eduthink-db --remote --file scripts/migrate_sync_state_2026-08-13.sql
-- 되돌리기: SQLite 는 컬럼 DROP 이 되지만 굳이 되돌릴 이유가 없다(값이 NULL 이면 «받은 적 없음»으로 읽힌다).

ALTER TABLE sync_state ADD COLUMN meals_synced_at TEXT;
ALTER TABLE sync_state ADD COLUMN timetable_synced_at TEXT;
