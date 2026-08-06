-- ════════════════════════════════════════════════════════════════
--  migrate_reward_2026-08-07.sql 되돌리기
--
--  ⚠ 새로 만든 표 6개는 지워도 **기존 데이터가 안 다친다**(참조가 한 방향뿐).
--  ⚠ 그러나 ALTER 로 붙인 컬럼 3개는 SQLite 에서 **간단히 못 지운다.**
--     DROP COLUMN 은 SQLite 3.35+ 에서만 되고, D1 은 되지만 인덱스·뷰가 걸려 있으면 실패한다.
--     실서버에서는 **컬럼을 남겨 두는 편이 안전하다** — 값이 NULL/기본값이면 아무 일도 안 한다.
--     정말 지워야 하면 아래 주석을 풀되, 반드시 백업 뒤에.
-- ════════════════════════════════════════════════════════════════

DROP INDEX IF EXISTS idx_mv_pending;
DROP INDEX IF EXISTS idx_mv_child;
DROP INDEX IF EXISTS idx_reactions_child;
DROP INDEX IF EXISTS idx_rorders_status;
DROP INDEX IF EXISTS idx_rorders_child;
DROP INDEX IF EXISTS idx_store_child;
DROP INDEX IF EXISTS idx_pmt_child;

DROP TABLE IF EXISTS mission_verifications;
DROP TABLE IF EXISTS reactions;
DROP TABLE IF EXISTS child_mode_config;
DROP TABLE IF EXISTS reward_orders;
DROP TABLE IF EXISTS store_items;
DROP TABLE IF EXISTS parent_mission_templates;

-- 컬럼 되돌리기 — 기본값이라 남겨도 무해하다. 꼭 필요할 때만 푼다.
-- ALTER TABLE children DROP COLUMN trial_ends_at;
-- ALTER TABLE orders   DROP COLUMN payment_channel;
-- ALTER TABLE orders   DROP COLUMN child_limit;
