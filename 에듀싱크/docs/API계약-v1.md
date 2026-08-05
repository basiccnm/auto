# API · 데이터 계약 v1 — 앱 전환 기준

작성: 2026-07-20 (코드탭) · 상태: **전략 세션 검수 대기**
근거: 「에듀싱크 앱전환 정본설계 v1」(2026-07-23, 구글 문서) §4·§5·§6·§9
목적: 정본 §12 전제 — **"트랙 충돌 방지를 위해 1주차 API·데이터 계약 확정이 먼저"**
성격: **이 문서가 확정되기 전엔 블록1·3·4를 동시에 착수하지 않는다.**

> 모든 컬럼명은 **실제 D1에서 조회한 것**입니다. 추정 없음.

---

# 0. 이 계약이 지키는 것

| 정본 원칙 | 계약에서의 실현 |
|---|---|
| §3-2 저장 형식 = 미래 입력 형식 | 기록 응답 JSON을 **블록4 AI가 그대로 읽을 형식**으로 고정(§5) |
| §3-3 DB는 자산, 화면은 소모품 | 기존 테이블 **손대지 않음**. 신설 3개만 추가 |
| §3-5 보안은 뼈대 | 이름 `identifiers` 분리 유지, 이미지 404 응답, 소유권 매 요청 검증 |
| §4.5 입력은 쉽게, 수정·삭제는 어렵게 | **재인증 토큰**을 쓰기·삭제 계열에만 요구(§3.4) |
| §9 add-only | 기존 컬럼 의미 변경 0건 |

---

# 1. 공통 규약

## 1.1 경로
```
/api/v1/*
```
기존 HTML 라우트(`/`, `/school/:slug/`, `/mypage` …)와 **완전 분리**. 웹은 안 깨집니다.

## 1.2 응답 봉투

기존 `json()` 헬퍼(`index.js:170`)를 그대로 씁니다.

**성공**
```json
{ "ok": true, "data": { ... } }
```
목록은 `data`가 배열이 아니라 객체입니다. 나중에 `total`·`cursor`를 넣을 때 형태가 안 깨집니다.
```json
{ "ok": true, "data": { "items": [...], "total": 128, "cursor": "..." } }
```

**실패**
```json
{ "ok": false, "error": { "code": "AUTH_EXPIRED", "message": "다시 로그인해 주세요." } }
```
- `code` — 앱이 분기하는 값. **절대 바꾸지 않습니다**
- `message` — 사용자에게 그대로 보여줄 한국어. 내부 사정 노출 금지

## 1.3 에러 코드

| code | HTTP | 뜻 | 앱 동작 |
|---|---|---|---|
| `AUTH_REQUIRED` | 401 | 토큰 없음 | 로그인 화면 |
| `AUTH_EXPIRED` | 401 | access 만료 | refresh 시도 → 실패 시 로그인 |
| `AUTH_INVALID` | 401 | 토큰 위조·폐기 | 로그아웃 |
| `REAUTH_REQUIRED` | 403 | 재인증 필요(수정·삭제) | 생체/비번 재확인 |
| `FORBIDDEN` | 403 | 내 것이 아님 | 오류 표시 |
| `NOT_FOUND` | 404 | 없음 **또는 권한 없음** | 오류 표시 |
| `VALIDATION` | 400 | 입력값 오류. `data.fields`에 항목별 사유 | 폼에 표시 |
| `LIMIT_EXCEEDED` | 403 | 한도 초과. `data.limit`·`data.used` | 안내 |
| `DUPLICATE` | 409 | 아이디·이메일 중복 | 폼에 표시 |
| `PAYMENT_STATE` | 409 | 주문 상태 전이 불가 | 새로고침 |
| `STORAGE` | 500 | R2 실패 | 재시도 안내 |
| `SERVER` | 500 | 그 외 | 재시도 안내 |

> **`NOT_FOUND`가 권한 없음을 겸합니다.** 남의 기록에 403을 주면 "그 id가 존재한다"는 정보가 새 나갑니다. 기존 이미지 서빙이 이미 이 규칙입니다.

## 1.4 인증 헤더
```
Authorization: Bearer <access_token>
```
- **앱** — 토큰만
- **웹** — 쿠키(`owner_token`) 병용 허용. 전환기 동안 두 경로 모두 통과
- 판정 순서: `Authorization` 헤더 → 없으면 쿠키

## 1.5 공통 형식

| 항목 | 형식 | 예 |
|---|---|---|
| 시각 | ISO8601 UTC | `2026-07-20T12:34:56.000Z` |
| 날짜(학사·급식) | `YYYYMMDD` **문자열** | `20260820` |
| 시각(방과후) | `HH:MM` | `16:00` |
| 학년 | **정수 코드** 초1=1…초6=6, 중1=7…중3=9, 고1=10…고3=12, 유치원=0 | `3` |
| 학기 | 정수 | `1` \| `2` |
| 요일 | 정수 1=월…7=일 | `"1,3"` (CSV) |
| 금액 | 정수(원) | `10000` |

> 날짜를 `YYYYMMDD` **문자열**로 두는 이유: `academic_schedules.event_date`·`meals.meal_date`가 실제로 그 형식이고, 문자열 비교만으로 범위 질의가 됩니다. 여기서 ISO로 바꾸면 219만 행을 전부 변환해야 합니다.

## 1.6 페이지네이션
```
?limit=50&cursor=<불투명 문자열>
```
기본 50, 최대 200. `cursor`는 서버가 만든 불투명 값(현재는 마지막 id).

---

# 2. 신설 테이블

**add-only.** 기존 테이블은 `children`에 컬럼 1개 추가하는 것 외엔 손대지 않습니다.

## 2.1 `accounts` — 진짜 회원

```sql
CREATE TABLE accounts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token  TEXT NOT NULL UNIQUE,   -- 데이터 키. 신원 아님(강등됨)
  display_name TEXT,
  email        TEXT,                   -- 비번 복구용(무료). 소셜 가입자는 NULL 가능
  phone        TEXT,                   -- 번호는 지금 받아두되 인증은 나중
  phone_verified INTEGER NOT NULL DEFAULT 0,
  birth_ymd    TEXT,                   -- YYYYMMDD. 본인확인·가족관계 확인 재료
  status       TEXT NOT NULL DEFAULT 'active',  -- active | suspended | withdrawn
  created_at   TEXT NOT NULL,
  last_login_at TEXT
);
CREATE UNIQUE INDEX idx_accounts_email ON accounts(email) WHERE email IS NOT NULL;
```

**`owner_token`이 여기 있는 게 핵심입니다.** 정본 §4의 "신원에서 데이터 키로 강등"이 이 한 줄입니다. `children.owner_token`을 안 건드려도 `accounts`를 거쳐 소유가 이어집니다.

## 2.2 `auth_methods` — 로그인 수단 (한 계정에 여러 개)

```sql
CREATE TABLE auth_methods (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  kind       TEXT NOT NULL,   -- social_kakao|social_google|social_naver|id_password|phone
  identifier TEXT NOT NULL,   -- 소셜 uid | 로그인 아이디 | 휴대폰번호
  secret     TEXT,            -- id_password만: 해시. 그 외 NULL
  verified   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_used_at TEXT
);
CREATE UNIQUE INDEX idx_auth_kind_ident ON auth_methods(kind, identifier);
CREATE INDEX idx_auth_account ON auth_methods(account_id);
```

## 2.3 `orders` — 주문 상태기계

```sql
CREATE TABLE orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id   INTEGER NOT NULL REFERENCES accounts(id),
  child_id     INTEGER REFERENCES children(id),  -- 자녀별 과금(정본 §5)
  months       INTEGER NOT NULL,
  amount       INTEGER NOT NULL,
  method       TEXT NOT NULL,   -- mock | bank_transfer | pg | google_iap
  status       TEXT NOT NULL,   -- pending|awaiting_deposit|confirmed|active|expired|cancelled
  payer_name   TEXT,
  external_ref TEXT,            -- PG 거래번호·IAP 영수증
  confirmed_by TEXT,            -- 확인한 admin
  confirmed_at TEXT,
  activated_at TEXT,
  expires_at   TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
CREATE INDEX idx_orders_account ON orders(account_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders(status);
```

**`method`가 플러그입니다.** `mock`(모의결제)·`bank_transfer`·`pg`·`google_iap`이 **같은 상태 전이를 탑니다.** 나중에 PG를 붙일 때 상태기계는 안 건드립니다.

## 2.4 `children` 확장

```sql
ALTER TABLE children ADD COLUMN family_verify_status TEXT;  -- NULL|pending|verified|failed
```
정본 §4 "가족검증_상태 칸 예약". 지금은 안 씁니다.

## 2.5 승계 규칙 — 무손실

```
accounts 1행  ↔  owner_token 1개  (UNIQUE)
```

| 대상 | 이관 방식 |
|---|---|
| `users` 8행 | 각 행마다 `accounts` 1개 + `auth_methods`(social_*) 1개 생성. `owner_token` **그대로 복사** |
| `children` 21행 | **손 안 댐.** `owner_token`으로 계속 연결 |
| `records`·`activity_schedules`·R2 | **손 안 댐.** `child_id`로 연결 |
| `payments` 2행 | 이력이라 보존. `orders`로 옮기지 않음 |
| 쿠키만 있고 계정 없는 자녀 | 그대로 둠. 그 사용자가 로그인하면 그때 `accounts` 생성하며 흡수 |

**강제 재가입 없음.** 기존 사용자는 다음 로그인 때 자동으로 계정이 생깁니다.

---

# 3. 인증 API (블록1)

## 3.1 토큰

| | 수명 | 담는 것 |
|---|---|---|
| **access** | 30분 | `account_id`, `owner_token`, 발급시각 |
| **refresh** | 90일 | `account_id`, 토큰ID |
| **reauth** | 5분 | `account_id`, 용도 — §4.5 step-up 전용 |

**서명**: HMAC-SHA256, Web Crypto. 외부 라이브러리 없음. 비밀키는 `wrangler secret`.
**비번 해시**: PBKDF2-SHA256(Web Crypto). Workers에 bcrypt가 없어서입니다. 반복 횟수·솔트는 구현 시 확정.

## 3.2 엔드포인트

| METHOD | 경로 | 하는 일 | 인증 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | ID 회원가입 | — |
| POST | `/api/v1/auth/login` | ID/비번 로그인 | — |
| GET | `/api/v1/auth/social/{provider}` | 소셜 로그인 시작 | — |
| GET | `/api/v1/auth/social/{provider}/callback` | 소셜 콜백 → 토큰 발급 | — |
| POST | `/api/v1/auth/refresh` | access 재발급 | refresh |
| POST | `/api/v1/auth/reauth` | 재인증 토큰 발급(비번 확인) | access |
| POST | `/api/v1/auth/logout` | refresh 폐기 | access |
| GET | `/api/v1/me` | 내 계정 + 자녀 요약 | access |
| DELETE | `/api/v1/me` | **회원 탈퇴** — 자녀·기록·R2 파기 + 계정 묘비화(신원 NULL·수단 전멸·토큰 회전), 결제·신고 이력은 익명 보존 | **access + reauth** |

> 🔧 **개정 2026-07-24 (회신24):** `DELETE /api/v1/me` 추가. 웹 `/mypage/purge`와 **같은 파기 경로**
> (`data_accounts.withdrawAccount`)를 탄다 — 탈퇴 구현이 두 벌이 되면 표가 늘 때 한쪽만 고쳐진다.
> 파기/보존 범위는 회신20 §3-3(신원·인증·연락 완전 파기 / 결제·신고 이력 익명 보존).

## 3.3 가입 요청 (정본 §4 "일반 회원가입")

```json
POST /api/v1/auth/register
{
  "login_id": "hardb",
  "password": "…",
  "name": "김철수",
  "birth_ymd": "19850312",
  "email": "a@b.com",
  "phone": "01012345678",
  "agree_terms": true,
  "agree_privacy": true
}
```
- **필수**: `login_id` `password` `name` `birth_ymd` `email` `agree_terms` `agree_privacy`
- `phone`은 받되 **인증 안 함**(문자는 건당 비용 — 정본 §4). `phone_verified=0`
- 약관·방침 동의는 **법적 필수**라 서버에서도 검사

## 3.4 재인증이 필요한 요청 (§4.5)

**입력은 가볍게, 수정·삭제는 무겁게.**

| 요구 | 대상 |
|---|---|
| access만 | 조회, **기록 업로드**, 자녀 등록, 방과후 등록 |
| **access + reauth** | 기록 삭제, 자녀 삭제, 전체 삭제, **회원 탈퇴**, 계정 정보 변경, 자녀 정보 수정 |

reauth 없이 호출하면 `REAUTH_REQUIRED`(403) → 앱이 생체/비번을 받아 `/auth/reauth`로 토큰을 얻고 재시도합니다.

> 업로드에 재인증을 걸지 않는 이유: 정본 §0의 승부처가 **"넣는 데 30초"**입니다. 추가는 덧붙이기라 피해가 작고, 위험은 펼쳐보기·고치기·지우기에 있습니다.

---

# 4. 읽기 API (블록3·4) — 회원 무관

**가장 먼저 뽑힙니다.** 인증이 필요 없어 블록1을 안 기다립니다.

| METHOD | 경로 | 대응 핸들러 |
|---|---|---|
| GET | `/api/v1/schools/search?q=&level=` | `handleSearch` (index.js:211) |
| GET | `/api/v1/schools/{slug}` | `handleSchoolDetail` (433) |
| GET | `/api/v1/schools/{slug}/meals?from=&to=` | 같은 핸들러 내 급식 조회 |
| GET | `/api/v1/schools/{slug}/timetable?grade=&class=` | 같은 핸들러 내 시간표 |
| GET | `/api/v1/schools/{slug}/schedules?from=&to=` | 같은 핸들러 내 학사일정 |
| POST | `/api/v1/schools/{slug}/warm` | `handleSchoolWarm` (376) — 온디맨드 NEIS |

## 4.1 학교 응답

```json
{ "ok": true, "data": {
  "slug": "서울숭미초등학교-7051136",
  "name": "서울숭미초등학교",
  "kind": "초등학교",
  "sido": "서울특별시",
  "address": "서울 관악구 …",
  "phone": "02-123-4567",
  "homepage": "http://sungmi.sen.es.kr",
  "sem2_start": "20260820",
  "detail": { "class_count": 24, "student_count": 512 }
}}
```
`schools` 실제 컬럼(`slug` `name` `school_kind` `sido` `address_road` `phone` `homepage` `sem2_start`)에서 **그대로 나옵니다.** `detail`은 `school_details` 조인이며 없으면 `null`.

## 4.2 급식

```json
{ "items": [{
  "date": "20260713",
  "type": "중식",
  "dishes": [
    { "name": "옥수수밥", "allergens": [] },
    { "name": "근대된장국", "allergens": [5, 6, 18] }
  ],
  "calorie": "680.4 Kcal",
  "origin": "…",
  "nutrition": "…"
}]}
```

**🔧 개정 2026-07-24 — `dishes`를 문자열 배열에서 객체 배열로 변경했습니다.**

처음엔 이름만 내보내게 썼는데, `meals.dishes_parsed`에 **알레르기 번호가 이미 들어 있었습니다.**
API가 그걸 버리면 "자녀 알레르기 하이라이트"를 만들 때 API를 다시 고쳐야 하고, 앱이 배포된 뒤면 버전 호환 문제까지 생깁니다.

> 정본 원칙2 — *"저장 형식 = 미래 입력 형식. 오늘 화면에 맞춰 대충 뽑으면 그 실수를 API 층에서 반복한다."*

**있는 데이터를 버리지 않습니다.** 이름만 필요한 화면은 `d.name`만 읽으면 됩니다.
`dishes_parsed`가 없으면 원문(`dishes`)을 같은 형태로 분해합니다.

## 4.3 시간표

```json
{ "items": [{
  "weekday": 1, "period": 1, "subject": "국어",
  "grade": "3", "class_name": "1",
  "school_year": "2026", "semester": "2"
}]}
```
⚠️ **`timetables.school_year`는 NEIS 학년도 문자열("2026")입니다.** §1.5의 학년 정수 코드와 **다른 개념**입니다. 앱에서 헷갈리지 않게 이 필드는 `neis_year`로 이름을 바꿔 내보냅니다.

## 4.4 학사일정

```json
{ "items": [{
  "date": "20260820",
  "name": "2학기 개학식",
  "content": "…",
  "closure_type": "…"
}]}
```
`grade_flags`는 **내보내지 않습니다** — 301MB 죽은 데이터이고 아무도 안 읽습니다.

---

# 5. 자녀·기록 API (블록5)

**정본 §3 원칙2가 가장 중요한 곳입니다.** 이 JSON을 3~4년 뒤 블록4 개인 AI가 그대로 읽습니다. 오늘 화면에 맞춰 뽑으면 그 실수가 굳습니다.

| METHOD | 경로 | 재인증 |
|---|---|---|
| GET | `/api/v1/children` | — |
| POST | `/api/v1/children` | — |
| PATCH | `/api/v1/children/{id}` | ✅ |
| DELETE | `/api/v1/children/{id}` | ✅ |
| GET | `/api/v1/children/{id}/records?category=&q=` | — |
| POST | `/api/v1/records` | — (업로드는 가볍게) |
| DELETE | `/api/v1/records/{id}` | ✅ |
| GET | `/api/v1/records/{id}/image[?thumb=1]` | — |
| GET/POST | `/api/v1/children/{id}/activities` | — |
| PATCH/DELETE | `/api/v1/activities/{id}` | ✅ |

## 5.1 자녀 응답

```json
{ "id": 24, "nickname": "첫째", "name": "김서준",
  "school": { "slug": "…", "name": "서울숭미초등학교", "kind": "초등학교" },
  "grade": "3", "class_name": "1", "grade_code": 3,
  "birth_year": 2017,
  "pass": { "active": true, "expires_at": "…", "free_open_until": "20260820" },
  "counts": { "records": 7, "activities": 4 } }
```
- **`name`은 `identifiers` 조인**입니다. 목록 응답에서는 **생략**하고 상세에서만 내려보냅니다(정본 §3-5 이름 분리)
- `grade_code`가 §1.5 정수 코드. `grade`는 원본 문자열

## 5.2 기록 응답 — **AI 입력 형식**

```json
{ "id": 42,
  "child_id": 24,
  "category": "report_card",
  "period": { "school_year": 3, "semester": 1, "label": "초3 1학기" },
  "title": "초3 1학기 통지표",
  "note": null,
  "image": { "url": "/api/v1/records/42/image",
             "thumb": "/api/v1/records/42/image?thumb=1",
             "bytes": 184320 },
  "created_at": "2026-07-20T…" }
```

**설계 의도**
- `period`를 **객체로 묶었습니다.** 나중에 `grades`(블록1.5)가 붙을 때 같은 시기 축을 공유합니다
- `image.url`이 **연번 경로**입니다. UUID를 URL에 넣으면 "URL을 아는 사람 = 권한자"라는 잘못된 모델이 생깁니다. 실제 방어는 매 요청 소유권 SQL이고, 실패는 **404**입니다
- `image_key`(R2 키)는 **절대 응답에 넣지 않습니다**
- 블록1.5에서 `"grades": [{subject, score_type, value}]`가 이 객체 안에 추가됩니다. **`record_id`로 원본에 연결** — 근거 없는 숫자를 AI가 말할 수 없는 구조

## 5.3 업로드

```
POST /api/v1/records   (multipart/form-data)
  child_id, category, school_year, semester
  files[]    원본 (긴 변 2000px / JPEG 0.85 — 클라이언트 리사이즈)
  files_t[]  썸네일 (480px / 0.7)
```
- 서버 상한 **4MB/장, 10장/요청**. 초과분은 건너뛰고 결과에 보고
- **쓰기 순서 R2 → D1.** D1 실패 시 방금 올린 R2 객체를 보상 삭제
- 장별 독립 처리 — 3장 중 2번째가 실패해도 1·3은 저장

**앱에서 달라지는 점**: 브라우저 canvas가 없으므로 **네이티브가 리사이즈**합니다. EXIF 제거도 앱이 책임집니다(웹은 canvas가 자동으로 지웠음). 계약상 서버는 동일하게 받습니다.

---

# 6. 결제 API (블록2)

## 6.1 상태 전이

```
                  ┌──────────────── cancelled
                  │
pending ──────► awaiting_deposit ──────► confirmed ──────► active ──────► expired
   │                                         ▲                  
   └────────── (mock: 즉시) ──────────────────┘
```

| 상태 | 뜻 | 다음 |
|---|---|---|
| `pending` | 주문 생성 | awaiting_deposit / cancelled |
| `awaiting_deposit` | 입금 대기(무통장) | confirmed / cancelled |
| `confirmed` | 입금 확인됨 | active |
| `active` | 이용권 활성 | expired |
| `expired` | 만료 | — |
| `cancelled` | 취소 | — |

**`mock`은 `pending → active`로 한 번에 갑니다.** 개발·검증용이며 실제 돈이 안 움직입니다.
**PG는 `confirmed`부터 자동입니다.** PG가 입금을 확인해 웹훅을 주면 `confirmed → active`.

## 6.2 엔드포인트

| METHOD | 경로 | 하는 일 |
|---|---|---|
| GET | `/api/v1/plans` | 상품·가격 목록 |
| POST | `/api/v1/orders` | 주문 생성 (`child_id`, `months`, `method`) |
| GET | `/api/v1/orders` | 내 주문 목록 |
| GET | `/api/v1/orders/{id}` | 주문 상세 |
| POST | `/api/v1/orders/{id}/cancel` | 취소 |
| POST | `/api/v1/admin/orders/{id}/confirm` | **입금 확인**(admin) |
| POST | `/api/v1/orders/{id}/mock-pay` | 모의결제 (`DEV_TOOLS`에서만) |

## 6.3 이용권 활성

`active` 전이 시 **`children.trial_expires_at`을 연장**합니다.

- 기존 만료일이 남아 있으면 **그 뒤에 이어붙입니다**(현행 로직 그대로)
- **자녀별 과금**이라 `orders.child_id`의 자녀만 연장됩니다
- 정본 §5의 "자녀 한 명당 하나씩"이 이 구조와 맞습니다

## 6.4 가격

```js
PLAN_PRICES = { 1: 10000, 3: 27000, 6: 51000, 12: 96000 }  // 자녀 1명당
```
**작업 기준값입니다.** 정본 §5가 "자녀 1명당 약 1만원, 열어둠"이라 했고 대표님 최종 확정 대기입니다. 기간권이라 상수 하나로 다음 구매분부터 바뀝니다.

---

# 7. 정합성 검증 결과

## 7.1 정본 대조

| 정본 | 계약 반영 |
|---|---|
| §4 accounts + auth_methods, owner_token 강등 | §2.1·2.2·2.5 ✅ |
| §4 가입 항목(이름·생년월일·이메일·휴대폰·아이디·비번) | §3.3 ✅ |
| §4 비번 복구 = 이메일 | `accounts.email` ✅ |
| §4 휴대폰은 받되 인증 나중 | `phone_verified=0` ✅ |
| §4 가족검증 칸 예약 | §2.4 ✅ |
| §4.5 3층 방어 | §3.1 reauth · §3.4 ✅ |
| §5 orders 상태기계 | §2.3·6.1 ✅ |
| §5 결제수단 플러그 | `method` 4종 ✅ |
| §5 자녀별 과금 | `orders.child_id` ✅ |
| §6 /api/v1/* 한 겹씩 | §1.1·4·5 ✅ |
| §9 add-only | 신설 3 + ALTER 1 ✅ |

## 7.2 기존 코드 대조 — 실제 컬럼으로 확인

| 응답 필드 | 출처 | 확인 |
|---|---|---|
| 학교 `homepage`·`sem2_start` | `schools` | ✅ 실재 |
| 급식 `dishes` | `meals.dishes_parsed` | ✅ 실재 |
| 시간표 `weekday`·`period`·`subject` | `timetables` | ✅ 실재 |
| 학사일정 `event_date`·`event_name` | `academic_schedules` | ✅ 실재 |
| 자녀 `birth_year`·`consent_at` | `children` | ✅ 실재 |
| 기록 `school_year`·`semester`·`image_key` | `records` | ✅ 실재 |
| 자녀 실명 | `identifiers.name` | ✅ 실재 |

**계약에 있는데 DB에 없는 필드: 0개.**

## 7.3 🔴 발견한 충돌 2건

**① `school_year`가 두 테이블에서 뜻이 다릅니다**
- `timetables.school_year` = NEIS 학년도 문자열 `"2026"`
- `records.school_year` = 학년 정수 코드 `3`(초3)

**같은 이름, 다른 의미.** 앱이 헷갈리면 초3 기록이 2026년으로 표시됩니다.
→ **계약에서 시간표만 `neis_year`로 이름을 바꿔 내보냅니다**(§4.3). DB는 안 건드립니다.

**② `payments`와 `orders`가 공존합니다**
- `payments.owner_token` (구) ↔ `orders.account_id` (신)
- 기존 2행은 더미이나 정본이 "이력은 사실 그대로"를 원칙으로 삼았습니다
→ **`payments`는 읽기 전용 이력으로 동결**, 신규는 전부 `orders`. API는 `orders`만 노출합니다.

## 7.4 트랙 충돌 점검

| 블록 | 만지는 파일 | 충돌 |
|---|---|---|
| 1 회원 | `auth.js`, `index.js` 인증부(2195~2228), 신규 `api_auth.js` | — |
| 3 학교정보 | 신규 `api_schools.js`, `index.js` 라우터 1줄 | — |
| 4 일정·시간표 | 위와 같은 파일 | ⚠️ **3과 같음** |
| 5 자녀·기록 | 신규 `api_records.js` | — |
| 2 결제 | 신규 `api_orders.js` | — |

**결론**: 블록3·4가 같은 파일을 만집니다. **하나로 합쳐 진행하는 게 맞습니다**(둘 다 학교 읽기 API라 자연스럽습니다).
그 외에는 **신규 파일로 분리**해 라우터에 한 줄씩만 추가하면 `index.js` 충돌이 없습니다.

---

# 8. 미결 — 전략 세션 확인 요청

1. **가격 확정** — §6.4는 제 작업 기준값입니다. 대표님 결정 필요
2. **`payments` 처리** — §7.3-②처럼 동결이 맞는지
3. **블록3·4 병합** — §7.4 결론대로 하나로 묶어도 되는지
4. **`/api/v1/plans` 노출 범위** — 앱에 가격을 보여줄지(구글 정책 §정본 §5 주의). 계약엔 넣었으나 앱에서 호출 안 할 수 있음
5. **웹 전환 시점** — 기존 HTML 핸들러를 언제 이 API 위로 옮길지. 지금은 병존입니다

---

*이 계약이 확정되면 블록1·3+4·5·2를 병렬로 착수합니다. 확정 전엔 착수하지 않습니다.*
