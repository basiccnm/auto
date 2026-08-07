-- 되돌리기 — migrate_childmode_pin_2026-08-07.sql
--
-- 원래 모양(migrate_reward_2026-08-07.sql §4)으로 되돌린다.
-- ⚠ 설정해 둔 PIN 은 사라진다. 아이 모드를 쓰던 부모는 PIN 을 다시 걸어야 한다.
--   (표를 되돌리는 것 말고 방법이 없다 — 칸을 지우는 ALTER 가 SQLite 에 없다.)

DROP TABLE IF EXISTS child_mode_config;

CREATE TABLE IF NOT EXISTS child_mode_config (
  owner_token TEXT PRIMARY KEY REFERENCES accounts(owner_token) ON DELETE CASCADE,
  pin_hash TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
