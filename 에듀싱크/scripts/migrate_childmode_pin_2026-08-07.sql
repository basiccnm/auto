-- ============================================================
-- 아이 모드 4자리 PIN — 시도 횟수·잠금 칸 추가 (2026-08-07)
-- 지시서 「에듀싱크 MVP 재설계」 §0-6 · §5④
-- ============================================================
--
-- 왜 필요한가
--   4자리 PIN 은 경우의 수가 1만 개뿐이다. 「부모 모드로 돌아가기」를 아이가
--   계속 두드리면 언젠가 맞는다. **화면에서 세면 앱을 껐다 켜서 우회된다** —
--   상점 상한을 서버가 세는 것과 같은 이유로, 실패 횟수도 서버가 세야 한다.
--   그래서 fail_count · locked_until 두 칸을 둔다.
--
-- 왜 ALTER 가 아니라 DROP + CREATE 인가
--   ① SQLite 의 ALTER TABLE ADD COLUMN 은 **두 번 돌리면 죽는다**(칼럼 중복).
--      마이그레이션을 다시 돌릴 일이 반드시 생기므로 여기서 막아 둔다.
--   ② 이 표는 **실서버에 0건**이다(2026-08-07 원격 실측 — 아이 모드가 아직 없었다).
--      지울 데이터가 없으니 다시 만드는 쪽이 안전하고 모양도 깨끗하다.
--
-- ⚠ 적용 순서를 안 타도 된다 — migrate_reward_2026-08-07.sql 의 child_mode_config 는
--   `CREATE TABLE IF NOT EXISTS` 라, 이 파일이 먼저 가든 나중에 가든 결과가 같다.
--   (그 파일이 나중에 가면 «이미 있으니» 건너뛰고, 먼저 가면 여기서 다시 만든다.)
--
-- 되돌리기: rollback_childmode_pin_2026-08-07.sql

DROP TABLE IF EXISTS child_mode_config;

CREATE TABLE child_mode_config (
  owner_token  TEXT PRIMARY KEY REFERENCES accounts(owner_token) ON DELETE CASCADE,
  pin_hash     TEXT NOT NULL,          -- pbkdf2$반복수$솔트$해시 (auth_core.js 와 같은 형식)
  fail_count   INTEGER NOT NULL DEFAULT 0,   -- 연속 실패. 맞히면 0 으로 되돌린다
  locked_until TEXT,                   -- ISO. 이 시각까지는 맞아도 안 열어 준다
  updated_at   TEXT NOT NULL
);
