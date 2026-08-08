-- ════════════════════════════════════════════════════════════════════
--  STAGE 0 — 게임 미션 뼈대 (기획서 v2 §08 「지금 뚫어둘 자리」)
--  2026-08-08
--
--  이 마이그레이션이 넣는 것은 **기능이 아니라 자리**다.
--  값은 비어 있어도 칸이 있어야 나중에 화면·DB 를 안 뜯는다.
--
--  ⚠ BEGIN TRANSACTION 을 쓰지 않는다 — 원격 D1(Durable Objects)이 거부하고
--    «success 0» 으로 조용히 실패한다(2026-08-08 실측).
--  ⚠ 되돌리기: rollback_stage0_game_2026-08-08.sql
-- ════════════════════════════════════════════════════════════════════

-- ── ① 팩 — 운영이 곧 상품 (기획서 v2 §06) ──────────────────────────
--   문제와 미션이 팩에 속하고, 팩에 기간·on/off 가 있다.
--   「이번 달 미션」이 팩 하나를 켜는 일이 된다.
--   ⚠ 반드시 **서버에서** 켜져야 한다. 앱 업데이트로 넣으면 스토어 심사에
--     며칠 걸려서 월드컵 개막에 못 맞춘다.
CREATE TABLE IF NOT EXISTS packs (
  id          TEXT PRIMARY KEY,              -- 'base' · 'worldcup2026' · 'chuseok'
  name        TEXT NOT NULL,
  kind        TEXT NOT NULL DEFAULT 'season',-- base | season | event | milestone
  starts_at   TEXT,                          -- NULL = 항상. YYYY-MM-DD
  ends_at     TEXT,
  min_members INTEGER,                       -- 가입자 수 조건(마일스톤 팩 — §07)
  locale      TEXT NOT NULL DEFAULT 'ko-KR', -- 언어팩 = 나라별 교체 단위
  active      INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);

INSERT OR IGNORE INTO packs (id, name, kind, locale, active, created_at)
VALUES ('base', '기본팩', 'base', 'ko-KR', 1, datetime('now'));

-- ── ② 미션 — 팩 소속 + 리그 점수 ───────────────────────────────────
--   ⚠ category 칼럼을 따로 만들지 않는다. 이미 있는 `slot`(morning/after/evening/any)이
--     그 역할이라, 칼럼을 둘로 두면 반드시 어긋난다. 매핑은 코드 한 곳에서 한다.
--   points 는 코인과 **다른 축**이다. 코인은 상한이 있어 1~3 으로 좁지만
--   점수는 상한이 없으니 크게 벌린다 — 그래야 재도전으로 쉬운 것만 골라 담는 게 이득이 안 된다.
ALTER TABLE missions ADD COLUMN pack_id TEXT NOT NULL DEFAULT 'base';
ALTER TABLE missions ADD COLUMN points  INTEGER NOT NULL DEFAULT 10;

--   우리 카탈로그는 차등(무게 × 10), 부모 미션(owner_token 있음)은 **고정 10**.
--   부모가 점수를 정하면 리그가 「우리 엄마가 후하다」로 갈려 경쟁이 성립하지 않는다.
UPDATE missions SET points = stars * 10 WHERE owner_token IS NULL;
UPDATE missions SET points = 10         WHERE owner_token IS NOT NULL;

--   실제로 준 점수는 배정 쪽에 남긴다(미션 표의 값이 나중에 바뀌어도 과거가 안 흔들린다)
ALTER TABLE mission_assign ADD COLUMN points INTEGER NOT NULL DEFAULT 0;

-- ── ③ 문제 — 팩 · 유형 · 그림 · 점수 ───────────────────────────────
--   지금은 전부 4지선다지만, 나중에 OX·그림이 들어올 때 표를 다시 안 만들도록 칸을 판다.
--   OX 는 찍으면 50% 라 **점수를 깎는 대신 시간을 줄인다**(3초) — 그래서 sec 도 문제에 둔다.
ALTER TABLE quiz_questions ADD COLUMN pack_id   TEXT    NOT NULL DEFAULT 'base';
ALTER TABLE quiz_questions ADD COLUMN kind      TEXT    NOT NULL DEFAULT 'mcq'; -- mcq | ox | image
ALTER TABLE quiz_questions ADD COLUMN image_url TEXT;
ALTER TABLE quiz_questions ADD COLUMN sec       INTEGER NOT NULL DEFAULT 5;
ALTER TABLE quiz_questions ADD COLUMN points    INTEGER NOT NULL DEFAULT 5;
ALTER TABLE quiz_questions ADD COLUMN tier      INTEGER NOT NULL DEFAULT 1; -- 인지도 등급(저학년=1만)

-- ── ④ 코인 — 기본 주머니와 히든 주머니를 나눈다 ────────────────────
--   기본(미션·퀴즈)은 하루 60 까지. 히든(출석·연속·깜짝)은 별도 5.
--   부모가 미션을 아무리 늘려도 60 을 못 넘고, **히든은 부모가 못 건드린다.**
ALTER TABLE star_ledger ADD COLUMN bucket TEXT NOT NULL DEFAULT 'base'; -- base | hidden

-- ── ⑤ 리그 — STAGE 2 에서 켠다. 점수는 **STAGE 1 부터 이미 쌓는다** ──
--   나중에 켤 때 「가입 순서로 유리」가 생기지 않으려면 처음부터 세고 있어야 한다.
--   어차피 첫 시즌은 그 달 1일에 리셋된다.
CREATE TABLE IF NOT EXISTS league_standing (
  child_id   INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  season     TEXT NOT NULL,                    -- KST 기준 YYYYMM
  points     INTEGER NOT NULL DEFAULT 0,
  tier       TEXT NOT NULL DEFAULT 'bronze',   -- bronze→silver→gold→platinum→diamond→master
  group_no   INTEGER,                          -- 30명 묶음. 리그를 켤 때 배정
  band       TEXT,                             -- 학년군 🔴 미확정 — 칸만 받아둔다
  final_rank INTEGER,                          -- 시즌 마감 시 확정
  updated_at TEXT NOT NULL,
  PRIMARY KEY (child_id, season)
);
CREATE INDEX IF NOT EXISTS idx_league_rank ON league_standing (season, group_no, points DESC);

--   시즌이 끝나도 «명예»는 남는다 — 리셋되는 건 순위지 명예가 아니다.
CREATE TABLE IF NOT EXISTS child_badges (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  code       TEXT NOT NULL,          -- 'league:202607:gold:1' · 'founder' · 'pack:worldcup2026'
  label      TEXT NOT NULL,
  earned_at  TEXT NOT NULL,
  UNIQUE (child_id, code)
);

-- ── ⑥ 오늘의 미션(퀴즈) — 재도전을 위해 attempt 를 키에 넣는다 ──────
--   기존 PK(child_id, ymd) 는 «하루 한 세트»를 강제했다. 이제 재도전이 생겨
--   (child_id, ymd, attempt) 로 바뀐다 — attempt 1 은 무료, 2~6 은 코인 결제.
--   ⚠ 원격 0건 · 로컬 0건 실측(2026-08-08) 후 재작성한다. 옮길 데이터가 없다.
DROP TABLE IF EXISTS quiz_session;
CREATE TABLE quiz_session (
  child_id    INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  ymd         TEXT NOT NULL,                  -- KST YYYYMMDD
  attempt     INTEGER NOT NULL DEFAULT 1,     -- 1=무료 · 2~6=코인
  codes       TEXT NOT NULL,
  answered    INTEGER NOT NULL DEFAULT 0,
  correct     INTEGER NOT NULL DEFAULT 0,
  coins       INTEGER NOT NULL DEFAULT 0,     -- 실제로 준 코인(상한에 걸려 깎일 수 있다)
  points      INTEGER NOT NULL DEFAULT 0,     -- 리그 점수(상한 없음)
  paid        INTEGER NOT NULL DEFAULT 0,     -- 이 판을 열려고 낸 코인
  finished_at TEXT,
  created_at  TEXT NOT NULL,
  PRIMARY KEY (child_id, ymd, attempt)
);

--   2회차부터는 **틀렸던 문제를 먼저 낸다** — 재출제가 우려먹기가 아니라 오답노트가 된다.
--   그 판단의 근거가 quiz_answer_log 이므로 조회 경로를 만들어 둔다.
CREATE INDEX IF NOT EXISTS idx_qal_wrong ON quiz_answer_log (child_id, correct, code);

-- ── ⑦ 아이 — 캐릭터 자리 · 레벨 ────────────────────────────────────
--   배경색은 이미 있는 kid_theme 을 쓴다(칼럼을 새로 만들지 않는다).
--   레벨은 **해낸 미션 수**로 오른다 — 누적 코인이 아니다.
--   코인 기준이면 퀴즈 잘 푸는 애만 빨리 오르지만, 미션 수면 꾸준한 애는 무조건 오른다.
ALTER TABLE children ADD COLUMN avatar_slot    TEXT;                     -- 캐릭터(업데이트 자리). 지금은 이모지
ALTER TABLE children ADD COLUMN level_missions INTEGER NOT NULL DEFAULT 0;
ALTER TABLE children ADD COLUMN streak_days    INTEGER NOT NULL DEFAULT 0;
ALTER TABLE children ADD COLUMN streak_ymd     TEXT;

--   이미 해낸 미션을 레벨에 반영한다(0 부터 시작하면 쓰던 아이가 손해를 본다)
UPDATE children SET level_missions = (
  SELECT COUNT(*) FROM mission_assign a WHERE a.child_id = children.id AND a.status = 'done'
);
