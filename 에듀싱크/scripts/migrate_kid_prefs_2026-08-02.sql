-- 자녀 앱 테마 저장(2026-08-02) — 아이가 고른 화면·색이 기기를 바꿔도 따라온다.
-- add-only 규칙 준수. 로컬·원격 둘 다 적용하고 조회로 확인할 것(적용·배포는 사장님 지시 후).
ALTER TABLE children ADD COLUMN kid_theme TEXT;
ALTER TABLE children ADD COLUMN kid_accent TEXT;
