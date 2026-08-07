-- 되돌리기 — migrate_quiz_2026-08-08.sql
-- ⚠ 문제 은행까지 사라진다. 시드(seed_quiz_*.sql)를 다시 부으면 복구된다.
DROP TABLE IF EXISTS quiz_answer_log;
DROP TABLE IF EXISTS quiz_session;
DROP TABLE IF EXISTS quiz_questions;
