-- ============================================================
-- 🧠 데일리 퀴즈 (기획서 §04) — 2026-08-08
-- 4지선다 10문제 · 문제당 5초 · 하루 1세트 · 맞힌 만큼 코인 · 만점 보너스
-- ============================================================
--
-- 왜 퀴즈인가
--   습관 미션은 «안 하고 그냥 누르는» 애를 막을 수 없다(부모가 봐야 안다).
--   퀴즈는 **서버가 답을 안다** → 구조적으로 못 속인다. 찍으면 기대값 2.5/10 이라
--   아는 아이와 찍는 아이가 코인으로 갈린다. 부모 개입 0 으로 신뢰가 서는 유일한 미션이다.
--
-- ⚠ 정답을 **절대 클라이언트에 내려보내지 않는다.** 채점은 서버가 한다.
--   보기 순서도 서버가 섞어 내려주고, 아이는 «몇 번을 골랐나»만 보낸다.
-- ⚠ 되돌리기: rollback_quiz_2026-08-08.sql

-- ── 문제 은행 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_questions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  code       TEXT UNIQUE NOT NULL,     -- Q-KOR-001 처럼. 시드를 다시 부어도 안 겹치게
  field      TEXT NOT NULL,            -- kor|math|sci|world|proverb|life|sports|ent
  band       TEXT NOT NULL DEFAULT 'all',  -- low|mid|high|all (학년대. 지금은 all 로 시작)
  q          TEXT NOT NULL,            -- 문제 (아이가 5초에 읽을 수 있게 짧게)
  a1         TEXT NOT NULL,
  a2         TEXT NOT NULL,
  a3         TEXT NOT NULL,
  a4         TEXT NOT NULL,
  answer     INTEGER NOT NULL,         -- 1~4 (**서버에만 있다**)
  hint       TEXT,                     -- 틀렸을 때 보여줄 한 줄 («아 이거였구나»가 남아야 학습이다)
  active     INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quiz_pick ON quiz_questions (active, band, field);

-- ── 하루 한 세트 (PK 가 «하루 1회» 를 강제한다 — 리롤과 같은 방식) ──
-- ⚠ 세는 로직을 따로 쓰지 않는다. INSERT 가 먹으면 오늘 처음이다.
CREATE TABLE IF NOT EXISTS quiz_session (
  child_id    INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  ymd         TEXT NOT NULL,           -- KST
  codes       TEXT NOT NULL,           -- 낸 문제 code 10개 (쉼표). 채점 때 이걸로 대조한다
  answered    INTEGER NOT NULL DEFAULT 0,
  correct     INTEGER NOT NULL DEFAULT 0,
  coins       INTEGER NOT NULL DEFAULT 0,
  finished_at TEXT,
  created_at  TEXT NOT NULL,
  PRIMARY KEY (child_id, ymd)
);

-- ── 문제별 기록 (분야별 정답률 → «나라박사» 뱃지의 근거) ──
CREATE TABLE IF NOT EXISTS quiz_answer_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  ymd        TEXT NOT NULL,
  code       TEXT NOT NULL,
  field      TEXT NOT NULL,
  picked     INTEGER,                  -- 1~4, 시간초과면 NULL
  correct    INTEGER NOT NULL,         -- 0|1
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quizlog_child ON quiz_answer_log (child_id, field);
