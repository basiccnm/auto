-- 미션(퀘스트) — 2026-08-01
--
-- 목록을 **서버에 둔다.** 앱에 박아두면 미션 하나 고칠 때마다 앱을 새로 내야 한다.
-- 계절·학사일정에 맞춰 계속 손볼 것이라 앱 업데이트와 분리해야 한다.
--
-- 판정(verify) 세 가지 — 이게 화면·알림·자동승인을 전부 가른다:
--   instant : 누르는 순간 도장. 그냥 누르기 / 타이머 완료 / 앱 접속
--   review  : 사진을 찍어 제출 → 부모 확인. **다음날 오전 8시 자동 승인**
--   endday  : 「안 하기」 미션. 하루가 끝나면 앱이 스스로 판정
--
-- ⚠ 리서치 표에 자체 모순이 있어 걸러 넣는다:
--   · 불을 쓰는 것(라면 끓이기·점심 차려먹기)은 같은 리포트 금지 5번과 충돌 → 뺀다
--   · 아이 얼굴을 찍게 하는 사진(비타민 먹는 사진·땀난 얼굴)은 결과물 사진으로 바꾼다
--   · 저학년 대기(사진) 비중이 권고(20%)보다 훨씬 많아 즉시로 돌린다

CREATE TABLE IF NOT EXISTS missions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,          -- 안정된 식별자. 문구가 바뀌어도 이건 안 바꾼다
  band TEXT NOT NULL,                 -- low(초1~2) | mid(초3~4) | high(초5~6)
  season TEXT NOT NULL,               -- weekday | weekend | vacation | patience(기다림)
  title TEXT NOT NULL,                -- 아이가 읽을 문장. 15자 이내, 평어체
  area TEXT NOT NULL,                 -- body|things|study|family|outside|digital|mind|money
  minutes INTEGER NOT NULL DEFAULT 0,
  cycle TEXT NOT NULL DEFAULT 'daily',-- daily | weekly | anytime
  verify TEXT NOT NULL,               -- instant | review | endday
  verify_hint TEXT,                   -- instant면 타이머·접속 방식, review면 「무엇을 찍나」
  slot TEXT NOT NULL DEFAULT 'any',   -- morning | after | evening | any  (유효 시간대)
  stars INTEGER NOT NULL DEFAULT 1,   -- 1~3. 소요시간 기준
  why TEXT,                           -- 왜 이 학년이 확실히 해낼 수 있는지
  caution TEXT,                       -- 「불을 써요」처럼 부모가 **알고** 골라야 하는 것
                                      -- (위험하다고 우리가 미리 빼면 그건 과보호를 강제하는 것이다)
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_missions_pick ON missions(band, season, active);

-- 넣으면 안 되는 것 — 목록으로 남긴다. 나중에 누가 「이건 왜 없지?」 할 때 이유가 있어야 한다.
CREATE TABLE IF NOT EXISTS mission_banned (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- 오늘 아이에게 준 미션과 그 결과
CREATE TABLE IF NOT EXISTS mission_assign (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  mission_code TEXT NOT NULL,
  ymd TEXT NOT NULL,                  -- 어느 날 것인가 (YYYYMMDD)
  status TEXT NOT NULL DEFAULT 'open',-- open | done | waiting | skipped | undone
  --   waiting = 사진 내고 부모 확인 대기 / skipped = 아이가 「못 했어요」 / undone = 부모가 되돌림
  photo_key TEXT,                     -- R2 키. 승인 7일 뒤 지운다(서랍과 별도)
  claimed_at TEXT,                    -- 아이가 완료를 누른 시각
  decided_at TEXT,                    -- 부모가 확인했거나 자동 승인된 시각
  auto_at TEXT,                       -- 자동 승인 예정 시각(다음날 08:00)
  stars INTEGER NOT NULL DEFAULT 0,   -- 실제로 준 도장
  created_at TEXT NOT NULL,
  UNIQUE (child_id, mission_code, ymd)
);
CREATE INDEX IF NOT EXISTS idx_massign_day ON mission_assign(child_id, ymd);
CREATE INDEX IF NOT EXISTS idx_massign_wait ON mission_assign(status, auto_at);

-- 도장 지갑 — 번 것과 쓴 것을 줄로 남긴다(잔액만 두면 어디서 틀어졌는지 못 찾는다)
CREATE TABLE IF NOT EXISTS star_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  delta INTEGER NOT NULL,             -- +획득 / -사용 / 되돌림은 음수
  reason TEXT NOT NULL,               -- mission:<code> | buy:<item> | revert:<code>
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_child ON star_ledger(child_id, created_at);
