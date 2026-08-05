# 학교알리미(schoolinfo.go.kr) 연동 — 착수 전 조사 메모

전교생·학급수·교원수·수업일수는 NEIS Open API에 **없다.** 학교알리미 OPEN API 소관.
스탯 그리드의 이 3칸(전교생/학급수/교원수)과 `상세정보`/방과후 데이터를 채우기 위한 소스.

## 현재 상태 (2026-07-12) — 인증키 발급·검증 완료
- ✅ **인증키 발급 완료** (kakao 4986673372). `eduthink_config.json`의 `schoolinfo_api_key`. 신규키라 sido/sgg 필수.
- ✅ **엔드포인트/파라미터 실사 확정**: `GET https://www.schoolinfo.go.kr/openApi.do`
  필수: `apiKey`, `apiType`, `pbanYr`(공시년도), `schulKndCode`(02초/03중/04고), `sidoCode`(2자리 행정코드), `sggCode`(5자리)
- ✅ **학교 매칭 확정**: 학교알리미는 자체 `SCHUL_CODE`(예: S010001758) 사용 — NEIS `SD_SCHUL_CODE`와 다름.
  `apiType=0`(학교기본정보 목록)이 `SCHUL_NM`+`SCHUL_RDNMA`(도로명주소)+`SCHUL_CODE`를 주므로 **학교명+주소로 매칭** → 7개 테스트교 전부 정확 매칭 검증.

### apiType 매핑 (개발자가이드 코드표 + 실사로 확정, `fetch_details.py`에 반영)
| 항목 | apiType | 컬럼 | 상태 |
|---|---|---|---|
| 학교기본정보 목록(매칭용) | 0 | SCHUL_CODE/SCHUL_NM/SCHUL_RDNMA | ✅ |
| **전교생 수** | 09 (학년별·학급별학생수) | `COL_S_SUM` (=학년별 COL_S1..6 합) | ✅ |
| **학급 수** | 09 | `COL_C_SUM` (=학년별 COL_C1..6 합) | ✅ |
| **교원 수** | 22 (직위별교원현황) | `COL_S` (=남 COL_SM + 여 COL_SW 검증) | ✅ |
| **수업일수/수업시수** | 08 (수업일수및수업시수) | `COL_1..6`(학년별 수업일수, 대표=최댓값) / `WEEK_TOT_ITRT_HR_FGR`(주당총시수) | ✅ |
| 학년별 학생/학급 | 09 | `COL_S1..6` / `COL_C1..6` → grade_breakdown JSON (상세정보 탭) | ✅ |
| **성별 학생수** | 63 | 학년별 `COL_M{g}`(남)/`COL_W{g}`(여) → breakdown male/female + 총계 `COL_MSUM`/`COL_WSUM`(특수학급 포함→전교생과 합일치) → `male_count`/`female_count` | ✅ (2026-07-12 추가) |
| **방과후학교** | 59 | `SUM_ASL_PGM_FGR`(프로그램수) / `ASL_PTPT_STDNT_FGR`(참여학생 실인원) / 돌봄=`ECC_PM_OPER_CCCLA_FGR`+`ECC_DINNR_OPER_CCCLA_FGR`>0 → care_class_yn | ✅ (집계치 → school_details 요약컬럼, 시간표 탭 하단 잠금 카드) |

주의: 전교생/학급수는 **반드시 apiType=09**(전용 dataset). apiType 10(전출입)·34(급식)·43(안전 CLASS_COUNT)은 기준일 달라 값 다름 → 09(COL_S_SUM, COL_C_SUM)로 통일.
주의: apiType 20/21의 COL_x는 학급수처럼 보이지만 실제 시설(유/무/적정설치) — COL_ 추측 금지.
주의: **반별 개별 인원(1-01=?명)은 어느 공시 apiType에도 없음** — 09/63 모두 학년 단위 총계까지만. 상세정보 "반별 펼치기"는 실데이터 불가 → 미제공(없는 정보 안 만듦). 09에도 남/여 없음(63 전용).
주의: apiType09 COL_S7/S8은 정규학년 아님(특수학급 등) → 학교급 최대학년(초6/중3/고3)까지만 학년 표시. 단 COL_S_SUM/COL_C_SUM 총계엔 특수학급 포함(숭미초 2026: 학년별합 474+특수13=487, 학급합 24+특수2=26).

⚠️ **pbanYr(공시연도)는 반드시 현재 학년도!** 학년도마다 값이 다름:
| 숭미초 apiType=09 | 전교생 | 학급 | 교원(22) |
|---|---|---|---|
| pbanYr=2024 | 570 | 32 | - |
| pbanYr=2025 | 512 | 29 | 45 |
| **pbanYr=2026 (현재·정답)** | **487** | **26** | **41** |
2026-07-12 최초 연동 때 실수로 pbanYr=2025로 돌려 작년값(512/29)이 박혔던 버그 있었음(사용자 실측 487/26으로 발견). `fetch_details.py`에 `current_school_year()` 추가 — 인자 `auto` 주면 3월 이후=올해/1~2월=작년으로 자동 계산. **매핑(09)은 처음부터 옳았고 연도만 문제였음.**

### apiType 전체 코드표(가이드 드롭다운)
0=학교기본정보, 04=자유학기제, 08=수업일수및수업시수, 09=학년별·학급별학생수, 10=전출입/학업중단,
22=직위별교원현황, 24=표시과목별교원, 51=입학생현황, 59=방과후, 62=학교현황, 63=성별학생수, 64=자격종별교원, 94=학교폭력예방교육

## 개발자 가이드
- `https://www.schoolinfo.go.kr/download/OpenAPI_Developer_Guide.pdf` (이미지 PDF라 자동 텍스트추출 안 됨 — 키 발급 시 육안 확인 필요)
- data.go.kr: "한국교육학술정보원_학교알리미 공시정보"(15098092), "공개용데이터"(15014351)

## 연동 우선순위(§지시서 6)
1. 인증키 발급 (사용자)
2. 4개 데이터셋 우선: 학생현황(전교생) / 교원현황(교원수) / 학년별학급별학생수(학급수) / 수업일수
3. 학교 매칭: 학교명+주소로 NEIS `schools.id` ↔ 학교알리미 `SCHUL_CODE` → `school_details.source_school_code`에 기록
4. `상세정보` 탭용 데이터 반환(개인화 없는 무료 공개)
5. 방과후학교 → `afterschool_courses`, 시간표 탭 하위 배치, 무료는 잠금(시간표와 동일 정책)
6. 나머지 35개 카테고리는 지금 안 가져옴(범위 과다 방지)

## D1 스키마 (school_details 단일 테이블)
- `school_details`: source_school_code / student_count / class_count / teacher_count / school_days / week_class_hours / grade_breakdown(JSON) / **afterschool_program_count / afterschool_student_count / care_class_yn** / disclosure_round
- ~~`afterschool_courses`(강좌목록)~~ **폐기(2026-07-12)** — apiType59가 집계치라 위 3개 요약컬럼으로 대체.

## 완료 (2026-07-12)
- `fetch_details.py` 완성 — 지역별 조회 → 학교명+주소 매칭 → 전교생/학급수/교원수/수업일수/주당시수/학년별 breakdown/방과후 집계 적재.
- 7개 테스트교 적재(예: 숭미초 512/29/45/191·방과후 54개242명돌봄Y, 신일고 982/32/72/191·방과후 59개702명돌봄N) → D1 동기화.
- **스탯 그리드 4칸**(전교생/학급/교원/개교 — 설립·남녀는 헤더중복이라 제거), **상세정보 탭**(학년별 학생/학급), **학사일정 탭 수업일수/주당시수 카드**, **시간표 탭 하단 방과후 요약카드**(프로그램수·참여학생·돌봄뱃지, 무료는 숫자 블러 잠금) 전부 검증.

## 남은 것
- 전국 확장: 전체 sido/sgg 순회(유치원 ETL과 동일 패턴). 현재는 7개교 지역만.
