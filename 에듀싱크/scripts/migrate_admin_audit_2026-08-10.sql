-- 관리자 감사 로그 (2026-08-10 대표님 요구 §4)
-- 「누가·언제·무엇을·대상·사유」. 이용권을 손으로 주고 회수하는 이상 이 기록이 없으면
-- 나중에 «왜 이 계정만 1년이지?» 를 아무도 답할 수 없다.
-- ⚠ 지우지 않는다. 관리자가 자기 흔적을 지울 수 있으면 감사 로그가 아니다.
CREATE TABLE IF NOT EXISTS admin_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,                  -- ISO8601
  actor TEXT NOT NULL,               -- 관리자 계정(Basic Auth 사용자명)
  action TEXT NOT NULL,              -- pass_adjust | order_confirm | order_cancel | post_delete | ban | ...
  target_kind TEXT,                  -- account | child | order | post
  target_id TEXT,                    -- owner_token / child_id / order_id
  detail TEXT,                       -- 무엇을 얼마나 (예: "+365일", "취소")
  reason TEXT,                       -- 🔴 사유 — 비워둘 수 없게 화면에서 막는다
  ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_at ON admin_audit(at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_target ON admin_audit(target_kind, target_id);
