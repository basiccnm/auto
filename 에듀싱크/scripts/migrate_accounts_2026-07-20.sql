-- ============================================================
-- 블록1 회원 체계 — accounts / auth_methods / orders 신설
-- 근거: docs/API계약-v1.md §2 · 정본설계 v1 §4·§5·§9
--
-- 원칙: add-only. 기존 테이블은 children에 컬럼 1개 추가하는 것 외엔 손대지 않는다.
--       users·children·records·activity_schedules·R2 전부 그대로 살아남는다.
-- ============================================================


-- ------------------------------------------------------------
-- 1) accounts — 진짜 회원
-- ------------------------------------------------------------
-- **owner_token이 여기 있는 게 핵심이다.**
-- 정본 §4의 "owner_token을 신원에서 데이터 키로 강등"이 이 한 줄이다.
-- children.owner_token을 안 건드려도 accounts를 거쳐 소유가 이어진다 → 무손실 승계.
--
-- email : 비밀번호 복구용(무료). 문자는 건당 비용이라 이메일로 간다(정본 §4).
-- phone : 번호는 지금 받아두되 인증은 나중. phone_verified=0으로 시작.
-- birth_ymd : 본인확인·가족관계 확인의 재료(정본 §4). 목적 있어 수집 — 방침에 명시할 것.
CREATE TABLE IF NOT EXISTS accounts (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token    TEXT NOT NULL UNIQUE,
  display_name   TEXT,
  email          TEXT,
  phone          TEXT,
  phone_verified INTEGER NOT NULL DEFAULT 0,
  birth_ymd      TEXT,
  status         TEXT NOT NULL DEFAULT 'active',   -- active | suspended | withdrawn_pending(탈퇴 유예 3개월) | withdrawn
  created_at     TEXT NOT NULL,
  last_login_at  TEXT,
  marketing      TEXT,      -- 광고성 수신 동의 JSON {email,sms,call,updated_at} (2026-07-31 ALTER로 추가)
  withdrawn_at   TEXT       -- 탈퇴 시각 — +90일 지나면 크론이 완전 파기 (2026-07-31 ALTER로 추가)
);
-- 이메일은 있을 때만 유일 — 소셜 가입자는 NULL일 수 있다.
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email) WHERE email IS NOT NULL;


-- ------------------------------------------------------------
-- 2) auth_methods — 로그인 수단 (한 계정에 여러 개)
-- ------------------------------------------------------------
-- 한 계정에 소셜·ID·휴대폰을 **동시에** 매달 수 있다.
-- 카카오로 가입한 사람이 나중에 ID/비번을 추가하거나, 그 반대도 된다.
--
-- kind       : social_kakao | social_google | social_naver | id_password | phone
-- identifier : 소셜 uid | 로그인 아이디 | 휴대폰번호
-- secret     : id_password만 해시를 담는다. 소셜은 NULL(비번을 소셜에 위임).
CREATE TABLE IF NOT EXISTS auth_methods (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id   INTEGER NOT NULL REFERENCES accounts(id),
  kind         TEXT NOT NULL,
  identifier   TEXT NOT NULL,
  secret       TEXT,
  verified     INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL,
  last_used_at TEXT
);
-- 같은 종류에 같은 식별자가 둘일 수 없다(카카오 uid 중복 가입 방지).
CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_kind_ident ON auth_methods(kind, identifier);
CREATE INDEX IF NOT EXISTS idx_auth_account ON auth_methods(account_id);


-- ------------------------------------------------------------
-- 3) orders — 주문 상태기계
-- ------------------------------------------------------------
-- 지난 실수는 "더미를 둔 것"이 아니라 **주문·입금대기·확인·활성 구조 자체가 없었던 것**이다.
-- 이번엔 상태기계를 진짜로 만들고, 결제수단만 갈아끼운다.
--
-- method : mock | bank_transfer | pg | google_iap  ← **플러그**. 넷이 같은 전이를 탄다.
--          mock만 pending → active 로 직행(개발·검증용, 실제 돈 안 움직임).
-- status : pending → awaiting_deposit → confirmed → active → expired / cancelled
-- child_id : **자녀별 과금**(정본 §5). 가족 단일가가 아니라 자녀 한 명당 하나씩.
CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id   INTEGER NOT NULL REFERENCES accounts(id),
  child_id     INTEGER REFERENCES children(id),
  months       INTEGER NOT NULL,
  amount       INTEGER NOT NULL,
  method       TEXT NOT NULL,
  status       TEXT NOT NULL,
  payer_name   TEXT,
  external_ref TEXT,          -- PG 거래번호 · IAP 영수증
  confirmed_by TEXT,          -- 입금 확인한 admin
  confirmed_at TEXT,
  activated_at TEXT,
  expires_at   TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  provider_token TEXT        -- 구글 인앱결제 구매 토큰 (재사용 차단용, 2026-07-31 ALTER로 추가)
);
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_ptoken ON orders(provider_token) WHERE provider_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_child ON orders(child_id);


-- ------------------------------------------------------------
-- 4) children 확장 — 가족검증 칸 예약
-- ------------------------------------------------------------
-- 정본 §4: 가족관계증명서 전자 확인으로 도용 방지(남의 아이를 함부로 등록 못 하게).
-- 지금은 칸만 만든다. NULL | pending | verified | failed
ALTER TABLE children ADD COLUMN family_verify_status TEXT;


-- ------------------------------------------------------------
-- 5) refresh 토큰 폐기 목록
-- ------------------------------------------------------------
-- 무상태 JWT는 서버가 "이 토큰 그만"이라고 말할 방법이 없다. 로그아웃·비번변경 시
-- 그 토큰을 못 쓰게 하려면 폐기 목록이 필요하다. jti(토큰 고유 id)만 담는다.
-- 만료된 항목은 크론이 청소한다.
CREATE TABLE IF NOT EXISTS revoked_tokens (
  jti        TEXT PRIMARY KEY,
  account_id INTEGER,
  expires_at TEXT NOT NULL,
  revoked_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revoked_exp ON revoked_tokens(expires_at);


-- ============================================================
-- 승계 규칙 (코드에서 처리 — 여기선 주석으로만)
-- ============================================================
--   accounts 1행  ↔  owner_token 1개 (UNIQUE)
--
--   users 8행     → 각 행마다 accounts 1개 + auth_methods(social_*) 1개 생성,
--                   owner_token은 **그대로 복사**
--   children 21행 → 손 안 댐. owner_token으로 계속 연결
--   records·activity_schedules·R2 → 손 안 댐. child_id로 연결
--   payments 2행  → 이력이라 보존. orders로 옮기지 않음(읽기 전용 동결)
--   쿠키만 있고 계정 없는 자녀 → 그대로 둠. 그 사용자가 로그인하면 그때 흡수
--
--   **강제 재가입 없음.** 기존 사용자는 다음 로그인 때 자동으로 계정이 생긴다.
