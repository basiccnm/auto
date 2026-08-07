-- 아이 모드 PIN — 시도 제한 (지시서 0807 §4④ · 2026-08-07)
--
-- 왜 필요한가: PIN 은 4자리라 무차별 대입이 1만 번이면 끝난다. PBKDF2 로 저장해도
-- «몇 번이든 시도할 수 있으면» 그건 잠금이 아니다. 진짜 방어선은 **시도 제한**이다.
--
-- ⚠ 추가만 한다(add-only). 기존 행에는 기본값이 들어간다.
-- ⚠ D1 은 ALTER TABLE ADD COLUMN 에 비상수 기본값을 못 쓴다 → NULL 허용 + 앱이 0 취급.
ALTER TABLE child_mode_config ADD COLUMN fail_count   INTEGER DEFAULT 0;
ALTER TABLE child_mode_config ADD COLUMN locked_until TEXT;
