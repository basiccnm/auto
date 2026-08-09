-- 되돌리기 — ⚠ 감사 기록이 사라진다. 정말 필요할 때만.
DROP INDEX IF EXISTS idx_audit_target;
DROP INDEX IF EXISTS idx_audit_at;
DROP TABLE IF EXISTS admin_audit;
