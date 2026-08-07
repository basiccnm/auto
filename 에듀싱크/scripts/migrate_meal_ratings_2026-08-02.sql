-- 급식 평가(2026-08-02 재설계) — 아이가 오늘 급식을 «고른» 기록.
-- 부모에게 말로 가지 않는다. 월 1회 리포트의 재료다.
-- add-only. 적용은 배포 지시 후(로컬·원격 둘 다 + 조회 확인).

CREATE TABLE IF NOT EXISTS meal_ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,               -- 평가한 날 (KST)
  stars INTEGER NOT NULL,          -- 1~5 (오늘 급식이 얼마나 맛있었나)
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)           -- 하루 한 번
);

-- 항목별 — 원문·합친 이름·종류를 다 남긴다.
-- dish_key 는 지금 «확실한 것만» 합친 값이다. 쌓인 식단표를 훑어 사전이 좋아지면
-- dish_raw 에서 다시 계산한다 — 그래서 원문을 절대 버리지 않는다.
CREATE TABLE IF NOT EXISTS meal_rating_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  dish_raw TEXT NOT NULL,          -- 「돈육김치볶음」
  dish_key TEXT NOT NULL,          -- 「돈육김치볶음」(합친 이름)
  dish_cat TEXT NOT NULL,          -- 볶음 | 국물 | 튀김 | 나물 | 김치 | 주식 | …
  rank INTEGER,                    -- 아이가 매긴 순위(1등부터). 안 고르면 NULL
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mri_child_ymd ON meal_rating_items (child_id, ymd);
CREATE INDEX IF NOT EXISTS idx_mri_child_cat ON meal_rating_items (child_id, dish_cat);
