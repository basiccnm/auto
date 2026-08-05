# 공공데이터 API 클라이언트 — 공통모듈 원본 + 전체 대장

> ⚠️ **얼마남아 B2B는 2026-07-21 삭제됨** — 수집기·수집데이터 보관: `D:\_보관\얼마남아-b2b-기획\`.
> 그 보관본 수집기가 올마나마 것보다 최신일 수 있다(도매가 단위버그 수정본). 대조 후 사용할 것.


새 프로젝트에서 공공기관 API가 필요하면 **여기부터 확인**하고, 맞는 파일을 **프로젝트 폴더로 복사**해서 쓴다 (직접 import 금지 — `..\CLAUDE.md` 규칙).

## 이 폴더의 원본 파일

| 파일 | 기관/API | 검증 출처 |
|---|---|---|
| `neis_client.py` | NEIS 나이스 (학교·학원·급식·유치원알리미) — `neis_get()` 재시도·백오프 포함 | 에듀싱크 common.py 2026-07-15 ETL 견고화판 |
| `config.py` | 공통 설정 패턴 — 키 env 오버라이드, UA 필수, SSL 검증 비활성, 타임아웃 | 삭제된 B2B publicdata (2026-07-16) — 보관본에 있음 |
| `kamis.py` | KAMIS 농산물유통정보 — 농산물 도매/소매 시세 | 〃 |
| `ekape.py` | 축산물품질평가원(축평원) — 한우 부분육·닭·돼지 시세, 주말 역탐색 | 〃 |
| `chamgagyeok.py` | 참가격(한국소비자원) — 가공식품 소비자가격 | 〃 |
| `catalog.py` | 공공 식품 카탈로그 | 〃 |
| `http.py`, `__init__.py` | 패키지 공통 HTTP 헬퍼(fetch_xml 등) — kamis/ekape/chamgagyeok가 상대임포트로 사용. **복사할 땐 폴더(패키지)째 복사할 것** | 〃 |

## 전 프로젝트 공공 API 사용 현황 (2026-07-17 조사)

| 기관 API | 쓰는 프로젝트 | 그 프로젝트의 코드 위치 | 키 위치 |
|---|---|---|---|
| NEIS (open.neis.go.kr) | 에듀싱크(학교·급식), 학원비사이트(학원 acaInsTiInfo) | `에듀싱크\scripts\common.py` / `학원비사이트\scripts\fetch_all.py`(자체 구현·키 하드코딩) | 각 프로젝트 config / 코드 상단 |
| 유치원알리미 | 에듀싱크 | `에듀싱크\scripts\common.py` | 〃 |
| KAMIS | 올마나마(B2C). ※B2B는 2026-07-21 삭제 | `D:\_보관\얼마남아-b2b-기획\web\scripts\publicdata\kamis.py` (최신) | `config.py` (cert_id = 사용자 이메일) |
| 축평원 (data.go.kr) | 삭제된 B2B(보관: D:\_보관\얼마남아-b2b-기획) | `D:\_보관\얼마남아-b2b-기획\web\scripts\publicdata\ekape.py` + **Workers 크론용 TS판** `src\worker\collect\ekape.ts` | `config.py` |
| 참가격 (data.go.kr) | 삭제된 B2B(보관: D:\_보관\얼마남아-b2b-기획) | `D:\_보관\얼마남아-b2b-기획\web\scripts\publicdata\chamgagyeok.py` | `config.py` |
| 식약처 (레시피 COOKRCP01, 인허가 I2500) | (현재 미사용 — 보관) | `D:\_보관\마라탕레시피\` | 스크립트 상단 |
| localdata.go.kr (지방행정 인허가) | (현재 미사용 — 보관) | `D:\_보관\마라탕레시피\localdata_maratang.py` | 〃 |

※ `올마나마\scripts\`(B2C)의 kamis_kg/collect_* 는 구버전. 최신 정리본은 삭제된 B2B(보관: D:\_보관\얼마남아-b2b-기획) 쪽이며 이 폴더의 원본도 거기서 복사함.

## 주의사항 (실사고 이력)

- **엔드포인트·파라미터 추측 호출 금지** — 글로벌 CLAUDE.md 규칙. 축평원 웹방화벽이 추측 호출을 공격으로 탐지해 IP 차단한 사고 있음(2026-07-16)
- KAMIS는 **User-Agent 없으면 차단** (config.py의 UA 필수)
- 공공 API 다수가 인증서 체인 불완전 → config.py의 SSL 검증 비활성 패턴 사용
- data.go.kr 키는 기관별 "활용신청"이 승인된 API에만 동작 — 새 API는 포털에서 신청부터

## 복사해간 곳 기록

| 언제 | 어느 프로젝트로 | 무엇을 |
|---|---|---|
| (아직 없음) | | |
