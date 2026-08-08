-- QA 계정 5종 시딩 (2026-07-17). 기존 자녀/결제는 건드리지 않음 — qa- 접두 토큰만 사용.
-- 유료/무료 구분은 subscriber 쿠키(/dev/login-as?sub=1)로 하고, 여기선 자녀 수만 세팅한다.
-- 학교: 경기초(4666, 일정 268건) / 경복초(4674, 167건) / 경희초(4690, 142건)
-- trial_expires_at은 넉넉히 미래로 → 만료 배너 없이 QA 가능.

DELETE FROM personal_events WHERE owner_token LIKE 'qa-%';
DELETE FROM children WHERE owner_token LIKE 'qa-%';
DELETE FROM free_trials WHERE owner_token LIKE 'qa-%';

-- ② 1자녀 무료회원 — free_trials 이력 있음(2번째 등록 시 차단되어야 정상)
INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at)
VALUES ('qa-free-1', 4666, '3', '1', 'QA무료첫째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:00.000Z');
INSERT INTO free_trials (owner_token, first_used_at) VALUES ('qa-free-1', '2026-07-17T00:00:00.000Z');

-- ③ 1자녀 유료회원
INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at)
VALUES ('qa-paid-1', 4666, '2', '1', 'QA유료첫째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:00.000Z');
INSERT INTO free_trials (owner_token, first_used_at) VALUES ('qa-paid-1', '2026-07-17T00:00:00.000Z');

-- ④ 2자녀 유료회원
INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at)
VALUES ('qa-paid-2', 4666, '2', '1', 'QA둘중첫째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:00.000Z'),
       ('qa-paid-2', 4674, '5', '2', 'QA둘중둘째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:01.000Z');
INSERT INTO free_trials (owner_token, first_used_at) VALUES ('qa-paid-2', '2026-07-17T00:00:00.000Z');

-- ⑤ 3자녀 유료회원(최대) — 자녀 추가 버튼이 숨어야 정상
INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at)
VALUES ('qa-paid-3', 4666, '1', '1', 'QA셋중첫째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:00.000Z'),
       ('qa-paid-3', 4674, '4', '2', 'QA셋중둘째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:01.000Z'),
       ('qa-paid-3', 4690, '6', '3', 'QA셋중셋째', 0, '2027-12-31T00:00:00.000Z', '2026-07-17T00:00:02.000Z');
INSERT INTO free_trials (owner_token, first_used_at) VALUES ('qa-paid-3', '2026-07-17T00:00:00.000Z');

-- 달력·알림 QA용 개인 일정(2자녀 유료의 첫째에 상세+알림 샘플)
INSERT INTO personal_events (owner_token, child_id, event_date, label, detail, remind_at, remind_sent, created_at)
SELECT 'qa-paid-2', id, '20260720', '가족여행', '제주도 여행 3인', NULL, 0, '2026-07-17T00:00:00.000Z'
FROM children WHERE owner_token='qa-paid-2' AND nickname='QA둘중첫째';
