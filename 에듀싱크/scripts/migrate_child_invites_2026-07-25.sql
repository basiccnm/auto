-- 자녀 기기 연결 — 일회용 6자리 코드 (2026-07-25 확정)
-- 엄마가 아이 폰에서 **로그인하지 않는다.** 로그인시키면 아이 폰에 부모 토큰이 남아
-- 결제·기록 삭제·형제 정보까지 열린다. 코드만 건네고 아이 폰은 **자녀 전용 토큰**만 갖는다.
CREATE TABLE IF NOT EXISTS child_invites (
  code       TEXT PRIMARY KEY,        -- 6자리 숫자. 짧아서 불러주기 쉽다 — 그래서 10분·1회용이다
  child_id   INTEGER NOT NULL,
  account_id INTEGER NOT NULL,        -- 발급한 부모 계정(감사용)
  expires_at INTEGER NOT NULL,        -- epoch 초
  used_at    TEXT,                    -- 쓰이면 채운다. 한 번 쓰면 끝
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_child_invites_child ON child_invites(child_id);
