-- ════════════════════════════════════════════════════════════════
--  2단계 보상 검증 + 별도장 상점  (지시서 「에듀싱크 MVP 재설계」 §8 정본)
--  2026-08-07 · 1단계 DB 마이그레이션
--
--  적용:  npx wrangler d1 execute <DB> --local  --file scripts/migrate_reward_2026-08-07.sql
--         npx wrangler d1 execute <DB> --remote --file scripts/migrate_reward_2026-08-07.sql
--  롤백:  scripts/rollback_reward_2026-08-07.sql
--
--  ⚠ 실서버(--remote) 적용은 **대표님 「배포해」 승인 뒤**에만 한다.
--  ⚠ 이 파일은 여러 번 돌려도 안전해야 한다(IF NOT EXISTS). ALTER 만 예외라 아래 주석 참고.
-- ════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 0) 왜 타입을 이렇게 잡았나 (지시서 초안과 다른 부분 — 실DB에 맞춘 것)
-- ────────────────────────────────────────────────────────────────
-- · child_id 는 **INTEGER** 다. children.id 가 INTEGER PRIMARY KEY AUTOINCREMENT 이기 때문.
--   D1 에 TEXT 로 넘기면 **에러가 아니라 «0건 일치»** 로 조용히 지나간다(이 프로젝트에서 이미 한 번 겪음).
-- · ON DELETE CASCADE — 자녀를 지우면 그 아이의 상점·보상·검증기록도 같이 사라져야 한다.
--   판별 기준은 «개인정보처럼 보이는가» 가 아니라 **child_id 를 들고 있는가** 다.
-- · passes 테이블은 **존재하지 않는다**(2026-07-19 조사에서 신설 안 하기로 결정).
--   이용권은 children.trial_expires_at + orders 로 굴러간다 → §8-7 은 그 둘을 확장한다.

-- ────────────────────────────────────────────────────────────────
-- 1) 부모 커스텀 미션 템플릿
--    하이브리드 세트 3개 중 «부모 커스텀 1개» 를 여기서 뽑는다.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS parent_mission_templates (
  template_id TEXT PRIMARY KEY,
  child_id    INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  stars       INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pmt_child ON parent_mission_templates(child_id);

-- ────────────────────────────────────────────────────────────────
-- 2) 별도장 상점 진열대
--    부모가 «무엇을 얼마에 파는지» 를 정한다. limit_* 는 주간·월간 상한.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_items (
  item_id        TEXT PRIMARY KEY,
  child_id       INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  title          TEXT NOT NULL,
  stars_required INTEGER NOT NULL,
  limit_type     TEXT,                      -- 'weekly' | 'monthly' | NULL(무제한)
  limit_count    INTEGER,
  created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_store_child ON store_items(child_id);

-- ────────────────────────────────────────────────────────────────
-- 3) 보상 구매 내역(영수증)
--    ⚠ 이름이 reward_orders 인 이유 — orders 는 **이용권 결제**가 이미 쓰고 있다.
--      같은 이름으로 만들면 결제가 통째로 깨진다(§0-4).
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reward_orders (
  reward_order_id TEXT PRIMARY KEY,
  child_id        INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  item_id         TEXT NOT NULL,
  item_title      TEXT NOT NULL,            -- 상품이 지워져도 영수증은 남아야 한다 → 이름을 박아 둔다
  stars_spent     INTEGER NOT NULL,
  status          TEXT NOT NULL DEFAULT 'requested',   -- 'requested' | 'fulfilled'
  created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rorders_child ON reward_orders(child_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rorders_status ON reward_orders(status);

-- ────────────────────────────────────────────────────────────────
-- 4) 아이 모드 PIN — 부모 폰을 아이와 나눠 쓰는 저학년용(§0-5)
--    ⚠ 키는 accounts.owner_token 이다. children 이 아니다 — 폰은 계정 단위로 잠근다.
--    ⚠ pin_hash 만 저장한다. 네 자리 숫자를 평문으로 두지 않는다.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS child_mode_config (
  owner_token TEXT PRIMARY KEY REFERENCES accounts(owner_token) ON DELETE CASCADE,
  pin_hash    TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- ────────────────────────────────────────────────────────────────
-- 5) 칭찬 리액션 + 2차 보너스 승인
--    sticker_type='bonus_approved' 이면 bonus_stars 가 실제로 지급된 도장 수다.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reactions (
  reaction_id  TEXT PRIMARY KEY,
  child_id     INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  sticker_type TEXT NOT NULL,               -- 'thumb_up' | 'heart' | 'bonus_approved'
  bonus_stars  INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reactions_child ON reactions(child_id, created_at DESC);

-- ────────────────────────────────────────────────────────────────
-- 6) 미션 검증 로그 — 1차(아이 행동) / 2차(부모 확인) 두 단계를 한 줄에 담는다
--    step1_granted_at 이 있고 step2_approved_at 이 비어 있으면 «부모 확인 대기» 다.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mission_verifications (
  verify_id         TEXT PRIMARY KEY,
  child_id          INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  mission_code      TEXT NOT NULL,
  step1_data        TEXT,                   -- 'p10-p20' 같은 페이지 범위 · 사진 R2 키
  step1_granted_at  TEXT,
  step2_approved_at TEXT,
  step2_bonus_stars INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mv_child ON mission_verifications(child_id, created_at DESC);
-- 부모 화면의 «확인해 주세요» 목록 — 2차 승인이 안 된 것만 훑는다
CREATE INDEX IF NOT EXISTS idx_mv_pending ON mission_verifications(child_id, step2_approved_at);

-- ────────────────────────────────────────────────────────────────
-- 7) 기존 테이블 확장 (passes 대체 · §8-7)
--    ⚠ SQLite 의 ALTER TABLE 에는 IF NOT EXISTS 가 없다. **두 번 돌리면 «duplicate column» 에러**가 난다.
--      그건 정상이다 — 이미 들어갔다는 뜻이니 그 줄만 건너뛰고 진행하면 된다.
--    ⚠ plan_months 는 만들지 않는다. orders.months 가 이미 같은 값이다(중복 컬럼 금지).
--    ⚠ trial_ends_at 도 만들지 않는다 — children.trial_expires_at 이 **이미 있고 코드 45곳이 쓴다.**
--      지시서 초안에 있어 한 번 넣었다가 뺐다(2026-08-07). 체험 만료일이 두 칸이 되면
--      어느 쪽이 진짜인지 아무도 모르게 된다. 체험 기간(1주/2주)은 값의 문제이지 칸의 문제가 아니다.
-- ────────────────────────────────────────────────────────────────
ALTER TABLE orders   ADD COLUMN payment_channel TEXT DEFAULT 'inapp';   -- 'inapp' | 'web'
ALTER TABLE orders   ADD COLUMN child_limit INTEGER DEFAULT 1;          -- 1(단독) | 3(패밀리)
