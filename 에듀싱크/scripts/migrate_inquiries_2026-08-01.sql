-- 고객센터 문의 (2026-08-01)
--
-- 기존 info_reports(학교 정보 오류) · beta_feedback(베타 의견)은 **한 방향**이다 — 받기만 하고
-- 답을 돌려줄 칸이 없다. 고객센터는 답이 사용자에게 돌아가야 하므로 표를 새로 둔다.
-- (저 두 표에 answer 칸을 붙이지 않는 이유: 「학교 급식이 틀렸다」와 「결제가 안 된다」는
--  받는 사람도 처리 방식도 다르다. 한 표에 섞으면 관리자 화면에서 둘 다 놓친다.)
--
-- account_id 로 묶는다(owner_token 아님) — 로그인 계정이 문의의 주인이고, 답변을 볼 사람도 그 계정이다.
-- 계정이 지워지면 문의도 같이 지운다(ON DELETE CASCADE) — 탈퇴 3개월 뒤 파기 규칙과 같은 결.

CREATE TABLE IF NOT EXISTS inquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  child_id INTEGER,                    -- 어느 자녀 얘기인지(선택). 자녀가 지워져도 문의는 남는다
  category TEXT NOT NULL DEFAULT 'other',   -- data|record|payment|account|bug|other
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  meta TEXT,                           -- 앱 버전·기기·학교 (JSON) — 「제 폰에선 안 돼요」를 되묻지 않으려고
  contact_email TEXT,                  -- 답을 메일로도 받고 싶을 때만
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered', 'closed')),
  answer TEXT,
  answered_at TEXT,
  seen_at TEXT,                        -- 사용자가 답을 읽은 시각 — 안 읽은 답이 있으면 앱이 배지를 띄운다
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inquiries_account ON inquiries(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status, created_at DESC);
