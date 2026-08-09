-- PWA 웹푸시 모듈 테이블 (D1/SQLite) — 출처: 에듀싱크 schema.sql (2026-07-16 검증본)
-- owner_token = 익명 사용자 식별 쿠키. 다른 식별자(user_id 등)를 쓰는 프로젝트는 컬럼명만 맞춰 바꿀 것.

-- 알림 설정(웹푸시) — 신청/해제 상태.
CREATE TABLE IF NOT EXISTS notif_settings (
  owner_token TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

-- 웹푸시 구독(브라우저 PushSubscription) — VAPID 발송 대상. endpoint 유니크.
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_push_owner ON push_subscriptions (owner_token);
