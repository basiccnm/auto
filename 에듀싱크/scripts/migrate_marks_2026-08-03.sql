-- 달력 «아이 흔적» 월별 이력 — 2026-08-03 (지시서 0803-1 §3 후속)
--
-- GET /api/v1/children/{id}/marks?month=YYYYMM 가 쓰는 것.
-- 부모 앱 달력이 날짜마다 도장·사진·급식평가 점을 찍는다.
--
-- ⚠ **새 테이블도 새 컬럼도 없다.** 필요한 값은 이미 다 있다:
--     mission_assign(child_id, ymd, status, mission_code)  ← 도장·그날 개수
--     missions(code, verify)                               ← 사진으로 내는 미션인가
--     meal_ratings(child_id, ymd, stars)                   ← 급식 평가
--   그래서 이 파일은 **읽기 속도만** 손본다. add-only 이고, 되돌릴 일이 생기면
--   DROP INDEX 두 줄이면 원래대로다(데이터가 안 움직이니 롤백이 공짜다).
--
-- ⚠ 사진 개수를 photo_key 로 세지 않는 이유 —
--   미션 사진은 승인 7일 뒤 지운다(api_mission.js PHOTO_KEEP_DAYS).
--   photo_key 로 세면 **지난 달이 전부 0으로 보인다.** 「사진으로 내는 미션이었나」로 센다.
--
-- ⚠ 우리 집 미션을 지워도 이력은 안 깨진다 — deleteCustom 이 active=0 로만 내린다(하드 삭제 아님).
--   그래서 LEFT JOIN missions 가 지난 달에도 그대로 붙는다.
--
-- 적용: **로컬 먼저** → 조회 확인 → 승인 후 원격.
--   npx wrangler d1 execute <DB> --local  --file=scripts/migrate_marks_2026-08-03.sql
--   npx wrangler d1 execute <DB> --remote --file=scripts/migrate_marks_2026-08-03.sql
--   ⚠ --remote 는 진짜 DB다. 삭제성 검증은 절대 --remote 로 하지 말 것.

-- ── ① 미션: 한 달치를 «자녀 + 날짜»로 훑는다 ─────────────────
-- 이미 idx_massign_day(child_id, ymd) 가 있어서 찾아가는 건 빠르다.
-- 다만 status·mission_code 를 읽으려고 **매 줄 본 테이블을 다시 열고 있다.**
-- 둘을 색인에 얹으면 색인만 읽고 끝난다(covering index).
CREATE INDEX IF NOT EXISTS idx_massign_marks
  ON mission_assign (child_id, ymd, status, mission_code);

-- ── ② 급식 평가 ────────────────────────────────────────────
-- UNIQUE(child_id, ymd) 가 색인 노릇을 하지만 stars 는 안 들어 있다. 같은 이유로 얹는다.
CREATE INDEX IF NOT EXISTS idx_meal_ratings_marks
  ON meal_ratings (child_id, ymd, stars);

-- ── 되돌리기 ───────────────────────────────────────────────
-- DROP INDEX IF EXISTS idx_massign_marks;
-- DROP INDEX IF EXISTS idx_meal_ratings_marks;
