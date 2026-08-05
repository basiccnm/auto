# 우리아이학원찾기 — 기술 구조 문서

전국 학원·교습소(NEIS)와 체육도장(행안부 LOCALDATA) 공공데이터를 지역·과목별로 검색·열람하는 SSR 웹서비스. Cloudflare Workers + D1 기반.

> 최종 갱신: 2026-07 / 문서 작성 기준 배포 버전 CACHE_VERSION="17"

---

## 1. 데이터 소스

| 대상 | 원천 | 비고 |
|---|---|---|
| 학원·교습소 (academies) | **NEIS 학원·교습소 정보 공개 API** | 계열(REALM_SC_NM), 교습과정(LE_CRSE_NM), 수강료(PSNBY_THCC_CNTNT), 정원, 주소, 전화 등 |
| 체육도장 (dojos) | **행정안전부 LOCALDATA API** | 태권도/검도/유도/합기도/권투/우슈/레슬링 등 인허가 종목(sport_name) |

### 원천 필드 특성
- **수강료(fee_raw)**: `과정명(스케줄):가격, ...` 문자열. 스케줄 괄호 안에 콤마가 있어 순진한 split은 과정명이 잘림 → `parse_fee()`에서 "가격 뒤 콤마"만 레코드 구분자로 사용 + 스케줄 괄호 제거.
- **분류 기준**: `realm_raw`(계열) 100% 채움이나 "입시.검정 및 보습"(약 77k)에 국어·수학·영어·과학이 섞여 있어 세분류 불가 → **학원명·교습과정 키워드**로 과목 판별.
- **교습대상(초/중/고) 필드는 원천에 없음** → 대상 칩 미구현.
- **읍면동(dong)**: 도로명주소 상세의 `(행정동, 건물명)` 괄호에서 추출. 학원 약 15%·도장 약 18%는 괄호 부재/오염으로 NULL. 건물동("상가동" 등) 오탐 방지 로직 적용.

### 데이터 규모 (로컬 DB 기준)
- academies 약 **138,344**건 (수강료 확인 `has_fee_data=1` 약 28,165건 ≈ 20.4%)
- dojos 약 **32,715**건

---

## 2. 인프라

```
[공공 API]
   │  (Python ETL)
   ▼
academies.db (로컬 SQLite)  ──sync SQL──▶  Cloudflare D1  "academy-site-db"
                                              (id: fd2b9dde-c080-479a-8407-9e76002947b1)
                                                   ▲
                                    ┌──────────────┴───────────────┐
                        [Worker] academy-site-renderer     [Worker] academy-tipoff-api
                        (SSR 페이지 렌더링, 읽기)            (제보/별점/정보등록/관리자, 쓰기)
```

### Cloudflare Workers (2개)
| Worker | URL | 역할 |
|---|---|---|
| `academy-site-renderer` | https://academy-site-renderer.dndmotor1.workers.dev | 모든 페이지 SSR(템플릿 리터럴 HTML), D1 읽기 전용, 엣지 캐시 |
| `academy-tipoff-api` | https://academy-tipoff-api.dndmotor1.workers.dev | 전화 제보·별점·정보등록 수집, 관리자 승인 페이지 (D1 쓰기), Basic Auth |

- 빌드 스텝 없음(순수 ES 모듈 JS). 배포: `wrangler deploy`.
- 프런트 리소스: **Pretendard**(jsDelivr) + **Phosphor Icons**(unpkg) CDN, **Kakao Maps JS**(지도 보기 지연 로드).

### Cloudflare D1 테이블
| 테이블 | 용도 |
|---|---|
| `academies` | 학원·교습소 (dong, has_fee_data, fee_parsed, info_provided 포함) |
| `dojos` | 체육도장 (sport_name, is_open, info_provided) |
| `ratings` | 별점 (entity_type/slug, score, voter_key) |
| `tip_offs` | 전화번호 제보 (pending→approved/rejected) |
| `info_submissions` | 학원 정보 등록/변경 신청 (신규/변경, pending 저장) |
| `banners` | 관리자 등록 광고 배너 (슬롯/지역/분야 타깃) |

### 로컬 ETL·운영 스크립트 (`scripts/`, Python)
- `common.py` — 정규화 + `parse_fee()`(수강료 파서)
- `fetch_all.py` / `export_region.py` — 수집·추출
- `compute_dong.py` — 주소에서 읍면동 추출(건물동 오탐 필터)
- `reparse_fees.py` — 수강료 재파싱 후 `fee_parsed`/`has_fee_data` 갱신
- `sync_dong_to_d1.py`, `sync_fees_to_d1.py` — D1 UPDATE SQL 생성 → `wrangler d1 execute --remote --file`로 반영

---

## 3. URL 구조 (site-renderer)

| 경로 | 페이지 |
|---|---|
| `/` | 홈 (히어로 검색 카드 + 지역/분야 요약) |
| `/{시도}/` | 시도 분야 아이콘 그리드 ("서울 학원 총 N개") |
| `/{시도}/{시군구}/` | 시군구 허브 (분야 아이콘 그리드) |
| `/{시도}/{시군구}/{읍면동}/` | 읍면동 페이지 (분야 버튼 → 클릭 시 하단 목록, `?subject=`,`?chip=`) |
| `/{시도}/{시군구}/{categorySlug}/` | 카테고리 목록 (bosup, taekwondo 등 원천 분류 slug) |
| `/{시도}/{시군구}/{slug}/` | 학원/도장 상세 |
| `/search?sido=&sigungu=&dong=&q=&subject=` | 검색·과목 목록 (상단 10칸 분야 필터바 + 2열 카드) |
| `/register/` | 우리 학원 신규 등록 폼 |
| `/privacy/` | 개인정보처리방침 |
| `/sitemap.xml`, `/sitemaps/{academies|dojos}-{n}.xml` | 사이트맵 |
| `/robots.txt` | 색인 제어 (`SITE_INDEXABLE`) |

### tipoff-api 엔드포인트
| 경로 | 메서드 | 설명 |
|---|---|---|
| `/submit` | POST | 전화번호 제보 저장(pending) |
| `/rate` | POST | 별점 upsert (voter token) |
| `/info-submit` | POST | 학원 정보 등록/변경 신청 저장(pending) |
| `/admin` | GET | 관리자 대기목록(정보신청·제보·배너), **Basic Auth** |
| `/admin/approve\|reject/:id` | POST | 전화 제보 승인/거절 |
| `/admin/info/approve\|reject/:id` | POST | 정보 신청 승인(→ `info_provided=1` + 수강료/전화 반영)/거절 |
| `/admin/banners` , `/admin/banners/:id/delete` | POST | 배너 등록/삭제 |

라우팅 규칙: `/search`에서 검색어·분야 없이 지역만 있으면 해당 허브로 302 리다이렉트. 3세그먼트 경로는 `categorySlug` → 카테고리목록, `REGION_MAP`상 읍면동 → 읍면동페이지, 그 외 → 상세 순으로 판별.

---

## 4. 운영 설계

### 분야 분류 (키워드 기반 10분류)
`국어·논술 / 수학 / 영어 / 과학 / 미술 / 음악 / 체육 / 외국어 / 독서실·스터디카페 / 기타`
- 학원명·교습과정·category_slug 키워드 매칭 (`getSubjectCounts`, `subjectAcademyCondition`, 카드용 `academySubjectLabel`).
- **체육(pe)** = 학원 키워드 + 도장 전체 포함(특수 그룹).
- "보습학원" 같은 뭉뚱그린 원천 분류는 화면에 실제 과목으로 치환 노출.
- (향후 옵션) 교습과목 필드 기반 **다대다 정식 분류**는 데이터 재빌드 필요 — 현재는 키워드 방식.

### 노출 우선순위 (티어 정렬)
배열 구조 `LIST_TIERS`로 ORDER BY 자동 생성(하드코딩 if 없음):
1. **정보제공**(info_provided) — 폼 등록·승인된 학원, **일 단위 로테이션**(UTC 날짜 시드로 캐시와 충돌 없이 순서 회전)
2. **수강료 확인**(has_fee_data)
3. 나머지 (가나다순)
- 추후 최상단 "광고" 티어는 `{ col: "is_ad" }`를 배열 앞에 추가만 하면 됨.

### 뱃지 정책
- **정보확인**(노란 리본/배지): 업체가 폼으로 정보 제공·승인된 상태.
- **정보 미제공**(회색 라벨): 정보 미제출 업체.
- 상세 관련목록에서 `정보확인`(노랑)은 항상 `수강료✓`(초록) 동반.

### 정보 등록 워크플로 (승인제)
```
[사용자] /register 신규 or 상세 "정보 등록·수정 요청"(변경, 기존값 프리필)
   └─ POST /info-submit ─▶ info_submissions (status=pending, 사이트 미노출)
[관리자] /admin (Basic Auth) ─▶ 승인
   └─ 변경: 대상 학원 info_provided=1 + fee_parsed/phone 반영
   └─ 신규: academies 신규 레코드 삽입(info_provided=1)
   └─ 안내: 사업자등록증을 지정 메일로 제출받아 확인 후 반영
```

### 광고 슬롯 (교체 가능 컴포넌트 `adxHtml`)
- 종류: `house`(방구석 약국 하우스 배너) / `adsense` / `coupang` / `personal`.
- 현재 활성: 하우스 배너(→ 방구석 약국 수험생 영양제 글, 새 탭 + "광고" 라벨). 애드센스·쿠팡은 승인/코드 확보 시 슬롯 내용만 교체.

### 캐싱
- `CACHE_VERSION` 상수를 키에 포함 → 값만 올리면 이전 배포 엣지 캐시 자동 무효화.
- 내부 `caches.default`에는 장기 TTL 저장, 외부 응답은 `Cache-Control: no-store`(엣지 자체 캐싱 방지).

### 지도/별점
- 지도: Kakao Maps JS 지연 로드("지도 보기" 클릭 시 렌더).
- 별점: 브라우저 voter token 해시 기반 1인 1표 upsert. (인터랙티브 별점 위젯은 트래픽 확보 전까지 상세페이지에서 제외, 표시만 유지.)

---

## 5. 현재 진행 상태

### 완료·배포됨
- 공공데이터 수집·정규화, D1 적재, 사이트맵/robots, SEO(canonical/breadcrumb/OG/JSON-LD).
- 3단계 지역 검색(시도→시군구→읍면동), 키워드 10분류, 티어 정렬(로테이션).
- **Claude 디자인 핸드오프 시안 이식**: 팔레트/폰트/아이콘, 홈·시도·시군구·읍면동·목록·상세 전 페이지, 분야 정사각/필터바, 정보확인 리본·정보미제공 라벨, 상세 2박스+전화 CTA+수강료 그리드.
- 수강료 과정명 파싱 정정 + D1 재동기화, 읍면동 파싱 오류 수정.
- "보습학원" → 실제 과목 표기(빵부스러기/칩/분야/관련목록).
- 정보 등록 폼(신규/변경 2모드) + 관리자 승인 페이지.
- 하우스 배너(방구석 약국) 연동.

### 대기 중 (사용자 입력 필요)
| 항목 | 필요한 것 |
|---|---|
| 쿠팡 파트너스 배너 | 파트너스에서 생성한 배너 코드 (현재 슬롯만 존재) |
| 법정동 전수 검증 | 행정표준코드 법정동 파일 (건물동 오탐 목록은 `audit/` CSV로 확보) |
| 정보등록 수신 메일 | `FEE_REQUEST_EMAIL` 실제 주소 (현재 PLACEHOLDER) |
| 관리자 로그인 | `ADMIN_PASSWORD`(wrangler secret) 확인/재설정 |

### 검토 옵션 (미확정)
- 교습과목 필드 기반 **다대다 정식 분류**로 전환 여부 (정확도↑, 데이터 재빌드 필요).
- 이상 데이터(이름=지역명/2자 이하/주소 없음/동 추출 실패) 정리 — 목록만 추출됨, 삭제/수정은 사용자 확인 후.

---

## 6. 저장소 구조 (요약)

```
학원비사이트/
├─ academies.db                  # 로컬 SQLite (원천 + 파생 컬럼)
├─ scripts/                      # Python ETL/운영 스크립트
│  ├─ common.py (parse_fee 등)
│  ├─ compute_dong.py / reparse_fees.py
│  └─ sync_dong_to_d1.py / sync_fees_to_d1.py
├─ audit/                        # 이상 데이터 점검 CSV
└─ workers/
   ├─ site-renderer/src/
   │  ├─ index.js                # 라우팅, D1 쿼리, 분류/정렬/캐시
   │  └─ templates.js            # 전 페이지 HTML/CSS/클라이언트 JS
   └─ tipoff-api/src/index.js    # 제보/별점/정보등록/관리자
```
