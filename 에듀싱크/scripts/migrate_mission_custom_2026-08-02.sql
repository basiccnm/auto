-- 우리 집 미션 (2026-08-02)
--
-- 「구몬 3장」·「윙크 20분」처럼 집집마다 다른 것은 우리 목록에 담을 수 없다.
-- owner_token 이 있으면 그 집만 보는 미션이다. NULL 이면 모두가 쓰는 공용.
-- 한 번 만들면 계속 재사용하므로 매일 타자를 치는 게 아니다.
ALTER TABLE missions ADD COLUMN owner_token TEXT;
CREATE INDEX IF NOT EXISTS idx_missions_owner ON missions(owner_token);
