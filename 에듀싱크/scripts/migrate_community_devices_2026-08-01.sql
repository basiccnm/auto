-- 커뮤니티 개편 + 부모 기기 2대 (2026-08-01)
--
-- ① 커뮤니티를 «게시판»에서 «오픈채팅»으로 바꾼다.
--    핵심 규칙: **참여한 시점부터만 보인다.** 이전 대화는 안 보인다(오픈채팅과 같음).
--    그래서 «언제 들어왔나»를 자녀별로 적어둔다 — 방은 학교×학년×반이고, 자녀 하나가 방 하나에 속한다.
--
-- ② 신고는 **자동 삭제가 아니다.** 신고한 사람 눈에서만 가려지고,
--    서로 다른 3명이 신고했을 때 비로소 내려간다(community_reports 의 UNIQUE 가 1인 다중신고를 막는다).
--    자동 숨김을 신고 1건으로 걸면 «신고 버튼이 곧 삭제 버튼»이 되어 악용된다(2026-08-01 사장님 지적).
--
-- ③ 부모 계정은 기기 2대까지. 엄마·아빠가 각자 폰에서 같은 계정을 본다.
--    자녀(1대)와 같은 방식이지만 표를 따로 둔다 — 자녀는 children 칸에 박혀 있고 1대뿐이라
--    같은 구조로는 2대를 못 담는다.

-- ── 커뮤니티 참여 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS community_members (
  child_id INTEGER PRIMARY KEY REFERENCES children(id) ON DELETE CASCADE,
  owner_token TEXT NOT NULL,
  joined_at TEXT NOT NULL,     -- 이 시각 **이후** 글만 보인다
  agreed_at TEXT NOT NULL,     -- 참여할 때 「지켜야 할 것」에 동의한 시각(구글 UGC 정책 요건)
  left_at TEXT                 -- 나가면 기록. 다시 들어오면 joined_at 이 갱신된다
);

-- 차단 — 이 사람 글은 나에게 안 보인다. 차단은 계정 대 계정이다.
CREATE TABLE IF NOT EXISTS community_blocks (
  owner_token TEXT NOT NULL,
  blocked_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_token, blocked_token)
);

-- 방 안에서 대화를 시간순으로 읽는다 → 학교·학년·반 + 시각 인덱스
CREATE INDEX IF NOT EXISTS idx_cposts_room
  ON community_posts(school_id, author_grade, author_class, id);

-- ── 부모 기기 ────────────────────────────────────────────────
-- 로그인할 때 기기 하나를 만들고 토큰에 그 id 를 넣는다. 표에서 지우면 그 폰 토큰은 즉시 죽는다.
-- 3번째 기기가 로그인하면 **가장 오래 안 쓴 기기**가 밀려난다(2대 유지).
CREATE TABLE IF NOT EXISTS account_devices (
  id TEXT PRIMARY KEY,                -- 토큰에 실리는 기기 식별자(uuid)
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  label TEXT,                         -- 「안드로이드 16 · SM-S911N」 — 내 정보에서 어느 폰인지 알아보게
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_adev_account ON account_devices(account_id, last_seen_at);
