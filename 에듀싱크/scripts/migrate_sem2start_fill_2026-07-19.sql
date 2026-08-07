-- ============================================================
-- 2학기 개학일 보충 채우기 — 2026-07-19
--
-- 1차(migrate_sem2start)는 '개학' 키워드로 8,864개교를 채웠다.
-- 남은 3,699개교 중 3,538개교는 학사일정은 있는데 '개학' 명칭이 없다.
-- 그 학교들도 대부분 '여름방학'을 날짜별 행으로 갖고 있으므로,
--   **여름방학 마지막 날 + 1일(주말이면 다음 월요일) = 개학일**
-- 로 유도한다.
--
-- 근거(실측): 두 신호가 모두 있는 8,445개교에서 이 규칙이 7,416개(87.8%) 정확 일치.
--   불일치분은 대부분 방학 끝이 금요일이라 +1이 토요일이 되는 경우 → 주말 보정으로 흡수.
--   예) 서울숭미초: 여름방학 ~8/19, 개학일 8/20 — 일치.
--
-- **이미 값이 있는 학교는 건드리지 않는다** (WHERE sem2_start IS NULL).
-- 1차에서 얻은 '개학' 명시 일정이 유도값보다 정확하므로 덮어쓰지 않는다.
-- ============================================================

UPDATE schools SET sem2_start = (
  SELECT strftime('%Y%m%d',
    date(
      substr(MAX(a.event_date),1,4)||'-'||substr(MAX(a.event_date),5,2)||'-'||substr(MAX(a.event_date),7,2),
      '+1 day',
      -- 주말 보정: 토(6) → +2일(월), 일(0) → +1일(월)
      CASE strftime('%w',
        date(substr(MAX(a.event_date),1,4)||'-'||substr(MAX(a.event_date),5,2)||'-'||substr(MAX(a.event_date),7,2), '+1 day')
      ) WHEN '0' THEN '+1 day' WHEN '6' THEN '+2 day' ELSE '+0 day' END
    ))
  FROM academic_schedules a
  WHERE a.school_id = schools.id
    AND a.event_name IN ('여름방학','하계방학','방학')
    AND a.event_date BETWEEN '20260701' AND '20260930'
)
WHERE sem2_start IS NULL;
