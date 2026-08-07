-- 준비물 체크리스트 (2026-07-27)
-- 리서치 결과 학원·학교 일정 앱들이 공통으로 가진 것이고, 우리 커뮤니티 글에서
-- 가장 많이 오가는 주제도 «내일 뭐 가져가야 해?» 였다. 일정과 별개 표로 둔다 —
-- 준비물은 학사일정(학교가 정함)에도, 내 일정(personal_events)에도 안 붙는다.
-- 대개 «그냥 내일» 챙기는 것이라 스스로 날짜를 갖는다.
--
-- 반복(매주 수요일 체육복)은 **서버가 계산하지 않는다.** 앱이 「4주치 만들기」로
-- 실제 행을 여러 개 만든다. 반복을 서버가 펼치면 «이번 주 것만 체크» 상태를
-- 따로 저장할 표가 또 필요해지고, 그러면 체크박스 하나에 표 두 개가 걸린다.
CREATE TABLE IF NOT EXISTS supplies (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,                    -- 다른 계정 것을 못 만지게 하는 열쇠(다른 표와 같은 규칙)
  child_id    INTEGER NOT NULL,
  due_ymd     TEXT NOT NULL,                    -- 챙겨 가는 날 YYYYMMDD
  item        TEXT NOT NULL,                    -- 준비물 이름 (예: 실내화, 리코더)
  memo        TEXT,                             -- 선택 (예: 이름표 붙이기)
  done        INTEGER NOT NULL DEFAULT 0,       -- 챙겼는가
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supplies_child ON supplies(child_id, due_ymd, id);
