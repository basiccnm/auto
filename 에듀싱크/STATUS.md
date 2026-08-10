# 에듀싱크(아이서랍) — 현재 상태

**[기준일시] 2026-08-10 18:40** · 지난 기록은 `_archive/STATUS-20260810-새벽작업.md`

---

## ① 지금 상태

**8/9 밤 ~ 8/10 오후, 커밋 61개.** 폰(갤럭시 Z 폴드6) 실기 + 에뮬 CDP 로 전수조사를 마쳤다.

| 검사 | 결과 | 돌리는 법 |
|---|---|---|
| 화면 43개 순회 | 문제 0 · 콘솔오류 0 | `probe_screens` |
| 글자 대비 47화면 × 5조합 = **235회** | 미달 **0** | `probe_contrast_all` |
| 면 대비 18테마 × 라이트·다크 36조합 | 묻힘 0 | `probe_surface` |
| 유리 · 테마 누수 | 0 · 0 | `probe_glass` · `probe_theme_leak` |
| 연결(함수·화면·API 84·아이경로 14) | ✅ | `node scripts/check_wiring.mjs` |
| 아이콘·색·주석 | ✅ | `node scripts/check_app.mjs` |
| 안전영역 | ✅ | `node scripts/check_safearea.mjs` |
| 들어갔다 못 나오는 화면 | 2곳(막다른 화면이 의도) | `node scripts/map_screens.mjs` |
| 출시 전 뒷문 | 🔴 4가지 열림(정상) | `node scripts/check_release.mjs` |

**런타임 검사는 디버그 빌드 + 에뮬 CDP 가 필요하다**(릴리즈는 웹뷰 디버깅 OFF):
```
adb -s emulator-5554 forward tcp:9333 localabstract:webview_devtools_remote_<pid>
CDP_TIMEOUT=420000 node scripts/emul_eval.mjs --file scripts/probe_screens.js
```
⚠ 기본 시간 초과 30초로는 모자란다(화면당 1.2초).
⚠ 다 돌린 뒤 **릴리즈로 되돌려 놓을 것**.

- 테스트 계정 `ph5126` / `testpass123` · 자녀 「콩」(D1 id 51 · 경기초 3학년 **난초**)
- 릴리즈 키: `C:\Users\hardb\Desktop\eduthink-release-key\` (폴더명에 한글 금지)
- 워커 `eduthink-site-renderer` (workers.dev · 커스텀 도메인 없음)

**최종 검수(18:37) 추가** — 로그인·로그아웃 한 바퀴 12항목 실측 통과(`probe_auth_flow`).
몽타주 2장 업로드: `G:\내 드라이브\에듀싱크-검수\20260810-1837-최종검수-{라이트,다크}.jpg`.
발견 1건 고침: **유료 이용권이 「1주일 무료체험 쓰는 중」으로 표기**되던 것
(만료일이 `trial_expires_at` 한 칸이라 구분 불가 → `/me` 가 orders 근거 `pass_paid` 를 줌).

## ② 진행 중

🔴 **워커 미배포 1건** — `/me` 의 `pass_paid`(위 표기 수정의 서버 반쪽).
앱(APK)엔 이미 들어갔고 드라이런 통과. **「배포해」 지시가 오면 `npx wrangler deploy`** 후
이용권 화면이 「이용권 · 44일 남았어요」로 바뀌는지 에뮬로 확인할 것.

## ③ 다음 할 일 — 순서대로

### 🔴 대표님이 주셔야 진행되는 것 (출시를 막는 셋)
1. **Play Console 서비스 계정** → `npx wrangler secret put GOOGLE_PLAY_SA`
   (코드는 다 됐다 — JWT→OAuth→androidpublisher→purchaseState 0→acknowledge)
2. **Play 상품 ID** — `pass_1m` · `pass_3m` · `pass_6m` · `pass_12m`
3. **`DEV_TOOLS="false"`** — 출시 직전. 지금 끄면 결제 테스트가 막힌다

### 🟡 폰이 있어야 확인되는 것
4. **폴드6에서 `--sa-bottom` 이 실제 네비바 높이로 오는지** — 에뮬은 0(정확)으로 확인됨
5. 아직 한 번도 안 본 화면: 급식 · 시간표 · 서랍(기록) · 커뮤니티 · 서류 · 상점 · 티켓 ·
   **자녀앱 전체** · **카메라·사진찍기**

### 🟡 지시만 있으면 되는 것
6. **매뉴얼** — 스샷에 번호를 넣어 부모앱·자녀앱·관리자. **시작 안 함**
7. 확정 대기 8건 — 가격 앵커 · 코인 상한 60 · 재도전 값표 · 리그 학년군 ·
   부모 미션 점수 · 리그 게이트 500명 · 「스타코인」 이름 · 칭호 구간
8. **중·고판 A선 확정** — `docs/관리자페이지-요구사항.md` 에 정리해 뒀다

## ④ 금지사항 · 함정

- 🔴 **`env(safe-area-inset-*)` 를 직접 쓰지 말 것.** 폴드6는 네비바가 있는데도 0 을 준다.
  `var(--sa-t)` / `var(--sa-b)` 를 쓴다(MainActivity 가 네이티브 값을 넣어 준다).
  하루에 **네 번** 같은 원인으로 버튼이 죽었다 — 보이는데 안 눌리는 부류다.
- 🔴 **템플릿 문자열 안에 역따옴표·블록주석 금지.** 「내 정보·설정」 화면이 통째로 죽었었다.
  HTML 주석만 쓴다. `check_app` 이 잡는다.
- 🔴 **서버로 나가는 자녀 번호는 `server_id`.** 로컬 `id` 는 화면 안에서만.
- 🔴 **아이콘은 서브셋 폰트다.** 없는 것을 쓰면 빈칸으로 뜬다. `check_app` 이 잡는다.
- 🔴 **DB 는 읽기만.** 값이 안 맞으면 화면·설명을 DB 에 맞춘다.
- ⚠ 파이썬으로 JS/CSS 를 고칠 때 `\n`·`\s` 가 실제 문자로 치환돼 파일이 깨진 적이 여러 번.
  **고치기 전에 사본을 뜨고**, 되도록 `node` 로 편집한다.
- ⚠ 무선 디버깅 포트: 「기기 페어링」 팝업 포트 ≠ 메인 화면 「IP 주소 및 포트」. 연결은 후자.
