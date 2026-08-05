# auth-module — 회원가입/로그인 재사용 모듈

간편가입(소셜) + 이메일 가입 + **휴대폰 인증**을 하나로 묶은 이식형 인증 모듈.
휴대폰 인증은 **어댑터 방식**이라, 지금은 SMS OTP로 쓰고 나중에 결제용 본인인증
(PASS/통신사 실명확인, CI/DI)으로 교체할 수 있습니다.

## 빠른 시작 (로컬, 계정 없이 전 흐름 테스트)

```bash
cd auth-module
pip install -r requirements.txt      # Flask만 있으면 됨
cp config.example.json config.json   # (Windows: copy)
python server.py
# → http://localhost:8700/auth
```

기본값은 **개발 모드**입니다:
- 휴대폰 인증번호가 실제 문자로 안 가고 화면·응답에 표시됨 (`reveal_code: true`)
- 소셜 로그인은 카카오/구글 **mock** 으로 동작(실제 앱 키 없이 흐름 확인 가능)

## 구성

| 파일 | 역할 |
|---|---|
| `templates/auth.html` | 위젯 마크업 (`.auth-widget` 블록만 떼어 재사용) |
| `static/auth.css` | 스타일. 360px 우선·다크모드. `--aw-*` 변수로 브랜드색 교체 |
| `static/auth.js` | 프레임워크 없는 위젯 로직. REST 규격에만 의존 |
| `auth_core.py` | DB·비번해시·OTP·세션 (스택 비종속 코어) |
| `phone_adapters.py` | 휴대폰 인증 발송 어댑터 (dev / sens / aligo / [향후 nice]) |
| `social_oauth.py` | 카카오·구글 OAuth (키 없으면 mock) |
| `server.py` | Flask 참조 백엔드 = REST 규격 |

## REST API 규격 (다른 스택 이식 기준)

| 메서드·경로 | 요청 | 응답 |
|---|---|---|
| `POST /api/phone/send` | `{phone, purpose}` | `{ok, ttl, dev_code?}` |
| `POST /api/phone/verify` | `{phone, code, purpose}` | `{ok, phone_token}` |
| `POST /api/auth/signup` | `{email, password, name?, phone_token}` | `{ok, user}` + 세션쿠키 |
| `POST /api/auth/login` | `{email, password}` | `{ok, user}` + 세션쿠키 |
| `POST /api/auth/logout` | — | `{ok}` |
| `GET  /api/auth/me` | (쿠키) | `{ok, user}` |
| `GET  /auth/start/<provider>` | — | 소셜 로그인으로 리다이렉트 |
| `GET  /auth/callback/<provider>` | `?code&state` | 세션쿠키 발급 후 리다이렉트 |
| `POST /api/phone/check-token` | `{phone_token, purpose}` | `{ok, phone}` — **결제 등에서 재사용** |

## 다른 페이지에 붙이기

```html
<link rel="stylesheet" href="/static/auth.css">
<div class="auth-widget" data-api-base="https://auth.내서비스.com"
     data-providers="kakao,google"></div>
<script src="/static/auth.js"></script>
<script>
  window.AuthWidget = { onAuthed: (user) => { location.href = '/dashboard'; } };
</script>
```

## 휴대폰 인증을 결제에서 재사용하는 법

1. 결제 직전 위젯의 휴대폰 인증 UI 재사용 → `POST /api/phone/verify`로 `phone_token` 획득
   (구조가 동일하므로 같은 프론트 컴포넌트를 `purpose:"payment"`로 재사용)
2. 결제 요청에 `phone_token` 동봉 → 서버가 `POST /api/phone/check-token`으로 검증
3. 증표는 발급 후 30분 유효, 1회성.

## SMS 실발송으로 전환

`config.json`에서:
```json
"phone": { "provider": "sens", "sens": { "access_key": "...", "secret_key": "...",
           "service_id": "...", "from_number": "025771234" } }
```
그리고 `reveal_code: false`, `cookie_secure: true`(HTTPS)로 바꾸세요.
`pip install requests` 필요.

## 결제용 본인인증(CI/DI)으로 확장할 때

`phone_adapters.py`에 `NiceVerifier`(또는 KG이니시스/다날)를 추가하고
`is_identity_verification = True`로 두면, 서버는 OTP 대신 본인인증 리다이렉트
플로우를 태우고 결과의 CI/DI를 `users`/`phone_verifications`에 저장하도록
`server.py`의 `/api/phone/*` 분기만 추가하면 됩니다. (프론트 위젯은 그대로)

## 보안 메모
- 비밀번호 pbkdf2-sha256(20만 라운드), 세션 쿠키 HttpOnly.
- OTP: 3분 TTL, 코드당 5회 시도, 번호당 30초 재발송 쿨다운·시간당 5건.
- 운영 전환 시 반드시: `reveal_code:false`, `cookie_secure:true`, OAuth state 서명,
  SQLite→관리형 DB, HTTPS.
