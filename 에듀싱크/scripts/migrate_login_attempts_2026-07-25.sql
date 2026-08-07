-- 로그인 시도 제한 (2026-07-25)
-- 왜: 비밀번호를 무제한으로 대입할 수 있었다. 10회 실패하면 잠근다(사장님 지시).
-- 기존 표는 건드리지 않는다 — 새 표 하나만 추가한다.
CREATE TABLE IF NOT EXISTS login_attempts (
  identifier   TEXT PRIMARY KEY,   -- 로그인 아이디 (있는 아이디든 없는 아이디든 똑같이 센다)
  fails        INTEGER NOT NULL DEFAULT 0,
  first_fail   INTEGER,            -- 이번 실패 묶음이 시작된 시각(epoch 초)
  locked_until INTEGER             -- 이 시각까지 잠금(epoch 초). NULL이면 안 잠김
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_locked ON login_attempts(locked_until);
