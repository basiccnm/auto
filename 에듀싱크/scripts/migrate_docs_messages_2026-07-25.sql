-- 서류·대화 저장 (2026-07-25)
-- 여태 서류(교외체험학습·결석신고·상담)와 부모↔자녀 대화는 **폰 안에서만** 돌았다.
-- 앱을 지우거나 폰을 바꾸면 사라졌다. 두 표를 추가해 서버에 남긴다.
-- 커뮤니티(community_posts)와 내 일정(personal_events)은 이미 표가 있어 그대로 쓴다.

-- ── 학교생활 서류 ───────────────────────────────────────────
-- payload에 서식 값 전체를 JSON으로 담는다. 서식이 학교마다 달라서 컬럼으로 못 박으면
-- 학교 하나 늘 때마다 스키마를 고쳐야 한다. 규칙 계산에 쓰는 값(기간·일수)만 컬럼으로 뽑는다.
CREATE TABLE IF NOT EXISTS documents (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL,
  kind       TEXT NOT NULL,                     -- field 교외체험학습 · absence 결석신고 · counsel 상담신청
  phase      TEXT NOT NULL DEFAULT 'apply',     -- apply 신청서 · report 보고서(교외체험학습만)
  title      TEXT,
  from_ymd   TEXT,                              -- 기간 시작 YYYYMMDD (연 19일 한도 계산에 쓴다)
  to_ymd     TEXT,
  days       INTEGER,                           -- 공휴일 뺀 실제 일수
  payload    TEXT NOT NULL DEFAULT '{}',        -- 서식 값 전체(JSON)
  reported   INTEGER NOT NULL DEFAULT 0,        -- 보고서까지 냈는가(안 내면 미인정 결석)
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_child ON documents(child_id, id DESC);

-- ── 부모 ↔ 자녀 대화 ────────────────────────────────────────
-- sender 는 보낸 쪽. seen_at 이 차면 상대가 봤다는 뜻(말풍선의 «1»이 사라진다).
CREATE TABLE IF NOT EXISTS messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL,
  sender     TEXT NOT NULL,                     -- parent | child
  text       TEXT NOT NULL,
  seen_at    TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_child ON messages(child_id, id DESC);
