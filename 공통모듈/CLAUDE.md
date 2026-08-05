# 공통모듈 — 이식형 모듈 원본 보관소

여기는 **여러 프로젝트에 가져다 쓰는 공용 모듈의 원본**만 두는 폴더다. 서비스 프로젝트가 아니며, 상시 서버를 돌리지 않는다.

## 규칙

1. **원본은 금고, 쓸 땐 복사** — 프로젝트에 붙일 때는 이 폴더를 import/참조하지 말고, 해당 프로젝트 폴더로 **복사**한 뒤 그 프로젝트에 맞게 수정한다. 폴더 간 직접 참조는 로컬서버 얽힘(자동리로더 연쇄 재시작)을 재발시킨다.
2. 원본을 개선했으면 어떤 프로젝트에 어떤 버전이 복사돼 있는지 아래 표에 기록한다.
3. 단독 테스트 포트: 전체 포트표는 `~\.claude\CLAUDE.md` 참조.

## 모듈 목록

| 모듈 | 설명 | 단독 테스트 | 복사되어 나간 곳 |
|---|---|---|---|
| `auth-module\` | 간편가입+이메일+휴대폰인증 회원가입 모듈 (Flask, 폰인증 어댑터로 결제 본인인증 확장 대비, 스택 미확정) | `python server.py` → http://localhost:8700/auth | (아직 없음) |
| `pwa-push\` | PWA 웹푸시 알림 세트 (Workers+D1, 의존성 0 — VAPID 발송기·서비스워커·구독 UI·크론 발송·스키마·키생성). 부착법은 폴더 README | `node gen-vapid-keys.mjs`로 키만 즉석 확인 가능 | 에듀싱크(원본, 인라인 형태로 실사용 중) |
| `공공데이터\` | 공공기관 API 클라이언트 원본 모음 (NEIS·KAMIS·축평원·참가격 등) + **전 프로젝트 공공 API 사용 대장** | 폴더 내 CLAUDE.md 참조 | 대장에 기록 |
| `foodspring\` | 식봄(업소용 식자재몰) 수집기 — GraphQL `goodsCategory(nid)` / `goodsSearch`. **카테고리 우선, 검색은 폴백.** nid 맵은 폴더 README. ⚠️ `pack_kg()` 는 2026-07-25에 배수 파싱 버그를 고쳤다(자세한 건 함수 주석) | `python foodspring_collect.py` | 올마나마(`scripts/foodspring_repair_cache.py` 에 파서 복사본) |
| `app_menu_reader.py` | 안드로이드 앱 메뉴화면 판독기 — uiautomator 텍스트 노드 순회(공짜). `detect()` 로 uiauto/devtools/canvas 판정 후 탭 순회. canvas(글자 0)면 중단·보고 | `python app_menu_reader.py <device>` | 올마나마(`scripts/app_menu_reader.py` 복사본) |
| `webview_dom.py` | 안드로이드 Chrome/웹뷰 **DevTools DOM 판독기**(의존성 0, 미니 WebSocket). 네이버 플레이스 `__APOLLO_STATE__`(매장 등록가) · 스마트오더 화면 등 «화면엔 있는데 API 못 뚫는» 값. `app_menu_reader` 가 canvas/webview 로 판정되면 이걸로. **DOM 읽기 전용** | `python webview_dom.py <device> out.txt` | 올마나마(가격수집에 사용) |
| `brand_price_fill.py` | 브랜드 메뉴 JSON(`brand_menu_list/<slug>.json`)의 **빈 가격만** {이름:가격} 맵으로 채우는 범용 헬퍼. 정규화 매칭 · 골격 보존 · 기존값 미덮음 · unmatched 반환. 지어내지 않는다 | `python brand_price_fill.py <json>` (카운트) | 올마나마(가격수집 세션) |
| `coupang\` | 쿠팡 **파트너스 API** — 상품검색·제휴(딥)링크·상품명 용량파싱. **소매가**용. `coupang_api.py` 에는 `main()`·`sys.exit` 를 두지 않는다(import 만으로 서버가 죽은 사고 때문). 분당 50회·`limit` 최대 10·**실패해도 HTTP 200**(`ok()` 로 rCode 확인)·용량은 추측 금지. 약관·고지문은 폴더 README | `python coupang_cli.py "생크림 500ml"` | 올마나마(원본 출신, 재료 소매가 수집) |
| `coupang_eats\` | 쿠팡이츠 앱 화면으로 **배달가 수집** — `ce_search_enter`(검색·가게진입) → `brand_coupangeats`(원본 저장) → `brand_coupangeats_parse`(가공). 홈페이지에 가격 없는 브랜드용. 4대 함정(검색화면 오진입·END조기종료·병렬충돌·그리드)은 폴더 README. 한글검색은 ADBKeyboard 필요 | `python ce_search_enter.py <dev> "브랜드" "가게"` | 올마나마(원본 출신, 30여 브랜드 수집) |
| `드라이브우편함\` | Claude 웹↔코드탭 비동기 통신 시스템 (구글드라이브 우편함 + watcher 상시감시 + 원클릭 깨움 매크로 + PROTOCOL v5). 함정·교훈은 폴더 CLAUDE.md | `node watcher.mjs --once` | 사장픽(원본 출신, 실사용 중) |

## 기타

- `gdrive_backup.ps1` — 구글드라이브 자동 백업 스크립트 (작업 스케줄러 "GDrive프로젝트백업"이 매일 21:00 실행). 모듈은 아니지만 공용 도구라 여기 둠.
