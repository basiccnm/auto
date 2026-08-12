-- 되돌리기 — 별 라인 (2026-08-12)
--
-- ⚠ SQLite 의 DROP COLUMN 은 3.35+ 에서만 된다. D1 은 된다.
-- ⚠ 컬럼을 지우면 부모가 정해 둔 예산이 **전부 사라진다.** 코드만 되돌릴 거라면
--    이 파일을 돌리지 말고 star_core.js 만 되돌려라 — 컬럼이 남아 있어도 아무 해가 없다.

ALTER TABLE children DROP COLUMN star_line;
