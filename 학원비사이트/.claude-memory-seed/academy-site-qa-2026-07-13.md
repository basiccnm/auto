---
name: academy-site-qa-2026-07-13
description: 우리아이학원정보(academy-site-renderer) 전체 레이아웃·기능 QA에서 발견한 미해결 버그 3건 + 미완성 기능 1건
metadata: 
  node_type: memory
  type: project
  originSessionId: 7382aa72-27f7-4fbc-ac36-4a95dcfe30c4
---

2026-07-13에 우리아이학원정보(https://academy-site-renderer.dndmotor1.workers.dev, 로컬 경로 `학원비사이트/workers/site-renderer`) 전체 라우트(홈/지역허브/카테고리목록/검색/상세/등록/사이트맵)를 curl+브라우저로 체계적으로 점검했음. 아래 항목들은 **아직 수정 안 됨** — 다음 세션에서 이어서 고칠 것.

## 1. (우선순위 높음) 별점 남기기 위젯이 어떤 페이지에도 연결 안 됨
- `src/templates.js`의 `ratingWidgetHtml()` 함수(818번째 줄 근방)가 정의만 되어 있고 **아무 데서도 호출되지 않음**.
- `academyDetailPage`/`dojoDetailPage`는 읽기전용 `starsInline()`만 쓰고, 클릭 가능한 `.rating-widget`은 렌더링 안 함.
- 클릭 핸들러(`handleRatingClick`, 약 596번째 줄)와 백엔드 `/rate` API(`workers/tipoff-api/src/index.js` 493번째 줄)는 둘 다 완성돼 있고 정상 작동 준비됨 — 프론트엔드 템플릿에서 위젯 삽입만 빠진 상태.
- **How to apply:** `academyDetailPage`/`dojoDetailPage`에서 `starsInline(...)` 근처에 `ratingWidgetHtml("academy"/"dojo", slug, ratingStats)` 호출을 추가하면 바로 살아남. 사용자가 아직 우선순위를 정하지 않았으니, 다음에 다룰 때 "지금 붙일지" 먼저 확인할 것.

## 2. (경미) 잘못 인코딩된 URL이 500을 반환 (404여야 함)
- `src/index.js` 663번째 줄: `path.split("/").filter(Boolean).map(decodeURIComponent)` 가 UTF-8이 아닌 percent-encoding(예: 구형 EUC-KR 인코더가 보낸 요청)을 만나면 `decodeURIComponent`가 URIError를 던지고, 최상위 try/catch(707번째 줄)가 이를 잡아 일반 500을 반환함.
- 실제 브라우저는 항상 UTF-8로 인코딩해서 보내므로 정상 사용자는 절대 못 겪음. 검색엔진 크롤러나 옛날 EUC-KR 링크에서나 트리거될 수 있는 엣지케이스.
- **How to apply:** `decodeURIComponent`를 try/catch로 감싸서 실패 시 404를 반환하도록 고치면 됨. 급하지 않음.

## 3. (경미) 카테고리 목록 페이지, 범위 밖 page 번호에서 제목이 슬러그로 노출
- `src/index.js` 237번째 줄: `categoryName`은 `academies[0].category_name`에서만 가져오는데, 결과가 0건인 page(예: `?page=9999`)에서는 `categoryName`이 null이 되어 `categoryListPage(...)` 호출 시 `categoryName || categorySlug`가 원본 슬러그(예: "bosup")로 폴백됨 → `<h1>양천구 bosup</h1>`처럼 노출.
- pagination 링크 자체는 `hasMore`가 true일 때만 다음 페이지를 노출하므로 **정상적인 클릭 탐색으로는 절대 도달 불가** — URL을 직접 수동으로 조작해야만 보임. 매우 낮은 우선순위.

## 4. (경미) closed_ymd가 NULL인 폐업 도장 76곳이 직접 URL 접근 시 404
- `DOJO_ALIVE` 상수(`src/index.js` 22번째 줄): `NOT (is_open = 0 AND closed_ymd < date('now','-2 years'))`. `closed_ymd`가 NULL이면 SQL의 NULL 전파로 인해 이 조건이 NULL이 되어 행이 통째로 제외됨 (원래 의도는 "2년 이내 폐업은 계속 보여주기"인데, 폐업일자를 모르는 76건은 즉시 숨겨짐).
- `getRelatedDojos` 등 내부 링크는 전부 `is_open=1`만 필터링해서 이 76건을 절대 링크하지 않으므로, **외부에서 들어오는 옛날 북마크/백링크로만 노출되는 문제**. 실제 D1: `SELECT COUNT(*) FROM dojos WHERE is_open=0 AND closed_ymd IS NULL` → 76건 (전체 폐업 도장 4,352건 중).
- **How to apply:** SQL을 `NOT (is_open = 0 AND (closed_ymd IS NULL OR closed_ymd < date('now','-2 years')))` 처럼 NULL을 명시적으로 처리하면 해결.

## 5. (중요, 신규 작업 필요) 지방 14개 시도에 카카오맵 좌표가 아예 없음
- 서울(22,025건 중 22,002건)·경기(16,918건 중 16,887건)·인천(2,692건 중 2,664건)만 `lat`/`lng` 컬럼에 값이 있고, 나머지 14개 시도(경남·부산·대구·전북·경북·광주·충남·전남·충북·울산·강원·대전·세종·제주)는 **전체 0건**. 로컬 원본 `academies.db`와 원격 D1 둘 다 동일 — D1 동기화 문제가 아니라 애초에 지방 데이터는 지오코딩(주소→좌표 변환)이 한 번도 수행된 적 없음.
- `src/templates.js`의 `mapBox2Html(lat, lng, name)` (780번째 줄)이 `!lat || !lng`면 지도 위젯을 아예 렌더링하지 않고 조용히 스킵하도록 짜여 있어서, 지방 상세페이지에서 화면이 깨지진 않음(그냥 지도 없이 표시됨) — 다만 지도 없이 노출된다는 게 기능 결손임.
- **How to apply:** 카카오 지오코딩 API(또는 다른 geocoding 소스)로 나머지 14개 시도 주소 → lat/lng 일괄 변환 배치 작업이 필요함. 로컬 DB 먼저 채운 뒤 D1으로 동기화하는 기존 패턴(`scripts/sync_missing_sido.py`) 재사용 가능할 듯. 도장(dojos) 테이블도 동일하게 확인 필요(아직 안 확인함).

## (완료) 연락처 이메일 반영 — 2026-07-13
- `FEE_REQUEST_EMAIL` 플레이스홀더(`PLACEHOLDER@example.com`) → `hardbar@naver.com`으로 교체 완료 (`templates.js:43`).
- 푸터(`footerHtml()`)에 "문의 hardbar@naver.com" (mailto 링크) 신규 추가 — 이전엔 푸터에 연락처가 전혀 없었음.
- 개인정보처리방침 페이지, 학원 등록 폼(사업자등록증 회신 안내)도 같은 상수라 자동 반영됨.
- CACHE_VERSION 22→23으로 올려서 배포, 반영 확인 완료.
- 관리자 페이지: `https://academy-tipoff-api.dndmotor1.workers.dev/admin` (Basic Auth, 비밀번호는 로컬 `ADMIN_CREDENTIALS.txt`).

## 검증 방법 관련 메모
- 이 세션에서 Browser 프리뷰의 `computer` 스크린샷/좌표클릭 도구가 계속 타임아웃돼서, DOM 실측(`javascript_tool`)과 `.click()` 강제 호출로 대체 검증함. 다음에 스크린샷이 필요하면 먼저 도구가 정상 작동하는지 확인할 것.
- curl로 한글 URL을 직접 타이핑하면 이 Windows/Git Bash 환경이 CP949로 잘못 인코딩해서 보내는 문제가 있음(실제 브라우저는 항상 UTF-8) — 한글 경로 테스트할 땐 `python -c "import urllib.parse; print(urllib.parse.quote(...))"` 로 UTF-8 percent-encoding을 미리 만들어서 써야 함.

[관련: [방구석 약국 프로젝트](bangpharmacy-project.md)와 마찬가지로 이 프로젝트도 학원비사이트 스택]
