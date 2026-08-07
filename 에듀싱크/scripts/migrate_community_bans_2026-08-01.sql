-- 커뮤니티 이용 정지 (2026-08-01)
--
-- 신고가 쌓여 글이 내려가는 것만으로는 부족하다 — 같은 사람이 계속 쓰면 계속 내려갈 뿐이다.
-- 구글 UGC 정책은 「불량 사용자에 대한 조치」를 요구한다. 글을 지우는 것과 사람을 막는 것은 다른 일이다.
--
-- 계정을 막는 게 아니라 **커뮤니티만** 막는다. 급식·기록·서식은 돈 내고 쓰는 기능이라
-- 대화에서 시비가 붙었다고 서비스 전체를 끊으면 그건 환불 사유가 된다.

CREATE TABLE IF NOT EXISTS community_bans (
  owner_token TEXT PRIMARY KEY,
  until TEXT,                 -- NULL 이면 무기한. 보통은 며칠짜리로 둔다
  reason TEXT,
  created_at TEXT NOT NULL
);
