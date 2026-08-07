-- ============================================================
-- 2학기 개학일 사전계산 + 재부여 1회성 플래그 — 2026-07-19
-- 근거: docs/회신.md [2026-07-19] "(D) 자녀 단위 개별 전환"
--
-- 왜 컬럼으로 미리 계산하나:
--   무료 개방 판정을 매 요청마다 academic_schedules(219만 행)에서 찾으면 느리다.
--   개학일은 학년도 중 바뀌지 않으므로 schools에 한 번 박아두고 읽기만 한다.
--
-- add-only. 기존 컬럼·데이터 변경 없음.
-- ============================================================

-- 1) 학교별 2학기 개학일 (YYYYMMDD). NULL이면 폴백 9/1 적용(회신 엣지케이스 2번).
ALTER TABLE schools ADD COLUMN sem2_start TEXT;

-- 2) 전환일 체험 재부여 1회성 플래그. NULL = 아직 재부여 안 됨.
--    자녀별로 두는 이유: 개학일이 학교마다 달라 전역 1회 기록으로는 관리 불가(회신 "자녀 단위" 지침).
ALTER TABLE children ADD COLUMN regranted_at TEXT;

-- 3) 개학일 채우기 — 8/1~9/30 구간의 '개학/2학기 시작' 일정 중 가장 이른 날.
--    · '방과후교실 개학' 같은 부속 일정은 제외(개학식 자체가 아님)
--    · 종업/방학식 계열 제외
UPDATE schools SET sem2_start = (
  SELECT MIN(a.event_date) FROM academic_schedules a
  WHERE a.school_id = schools.id
    AND a.event_date BETWEEN '20260801' AND '20260930'
    AND (a.event_name LIKE '%개학%' OR a.event_name LIKE '%2학기 시작%' OR a.event_name LIKE '%2학기시작%')
    AND a.event_name NOT LIKE '%방과후%'
    AND a.event_name NOT LIKE '%돌봄%'
    AND a.event_name NOT LIKE '%종업%'
    AND a.event_name NOT LIKE '%방학식%'
);

-- 4) 크론이 "오늘 개학하는 학교의 자녀"를 찾는 경로 — 개학일 인덱스.
CREATE INDEX IF NOT EXISTS idx_schools_sem2 ON schools (sem2_start);
-- 자녀 → 학교 조인 + 미재부여 필터
CREATE INDEX IF NOT EXISTS idx_children_regrant ON children (regranted_at, is_test);
