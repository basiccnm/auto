# pwa-push — PWA 웹푸시 알림 모듈 (Cloudflare Workers + D1)

브라우저/PWA에 푸시 알림을 보내는 완결 세트. **외부 라이브러리 0** (web-push 패키지 불필요 — VAPID 서명을 Workers 내장 crypto로 직접 함).

- 출처: 에듀싱크(우리아이학교정보)에서 2026-07-16 실기기(안드로이드·iOS PWA) 검증된 코드를 범용화
- 이식: 2026-07-17. **에듀싱크 쪽이 실사용 원본** — 그쪽에서 버그가 고쳐지면 여기에 역반영할 것
- ⚠️ 공통모듈 규칙: 프로젝트에 붙일 땐 **복사**해서 사용. 이 폴더를 직접 import 금지

## 파일 구성

| 파일 | 역할 | 붙이는 곳 |
|---|---|---|
| `push.js` | VAPID 서명 + 발송기 (핵심, 수정 없이 사용) | Workers `src/` |
| `sw.js` | 서비스워커 — 알림 표시 + 클릭 이동 | 사이트 **루트** 경로로 서빙 |
| `client-subscribe.js` | 브라우저 구독 스니펫 — 권한→구독→서버저장 | 알림 켜기 버튼 있는 페이지 |
| `routes-example.js` | 구독 저장/테스트 발송/크론 발송 라우트 예시 | Workers `fetch()`/`scheduled()` |
| `schema.sql` | `push_subscriptions` + `notif_settings` 테이블 | D1 스키마 |
| `gen-vapid-keys.mjs` | VAPID 키쌍 생성 (1회 실행) | 로컬에서 실행만 |

## 부착 5단계

1. **키 생성**: `node gen-vapid-keys.mjs` → `VAPID_PUBLIC`은 wrangler.toml `[vars]`, `VAPID_PRIVATE`은 `wrangler secret put VAPID_PRIVATE`
2. **DB**: `schema.sql`의 두 테이블을 프로젝트 schema에 추가 (`wrangler d1 execute <DB명> --file=schema.sql`)
3. **서버**: `push.js` 복사 + `routes-example.js`를 참고해 `/sw.js` 서빙, `/api/push/subscribe`, `/api/push/test` 라우트 추가
4. **클라이언트**: `client-subscribe.js`를 페이지에 넣고 `PUSH_CFG.vapidPublic`에 서버가 내려준 `env.VAPID_PUBLIC` 주입 → 버튼에서 `enablePush()` 호출
5. **자동 발송**: wrangler.toml에 `[triggers] crons = ["* * * * *"]` + `scheduled()`에서 `cronSendDue()` 패턴 사용 (보낼 대상 쿼리만 프로젝트에 맞게 교체)

## 반드시 알아야 할 것

- **무페이로드 방식**: 푸시 자체엔 내용이 없고, 서비스워커가 `sw.js`의 `CONFIG.fallback` 문구(또는 `latestUrl` API 응답)를 표시한다. 페이로드 암호화(aes128gcm) 구현 없이 동작하는 대신 문구는 서버/SW에서 정한다.
- **iOS는 PWA 설치 후에만 동작** — "홈 화면에 추가" 안내 문구를 UI에 꼭 넣을 것 (client-subscribe.js의 alert에 이미 포함).
- **만료 구독 정리**: 발송 시 404/410이 오면 그 구독을 DB에서 지운다 (routes-example.js에 구현돼 있음).
- `sw.js`는 **반드시 사이트 루트**(`/sw.js`)로 서빙 — 하위 경로면 서비스워커 스코프가 좁아져 안 됨.
- 사용자 식별은 `owner_token` 익명 쿠키 기준. 로그인 계정 체계가 있으면 그 식별자로 컬럼만 교체.

## 이 모듈을 쓰는 프로젝트 (복사 대장)

| 프로젝트 | 복사일 | 비고 |
|---|---|---|
| 에듀싱크 (원본) | — | index.js/templates.js에 인라인된 형태로 실사용 중 |
