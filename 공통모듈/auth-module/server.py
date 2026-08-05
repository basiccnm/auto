"""
server.py — 회원가입/인증 모듈 참조 백엔드 (Flask, 포트 8700, SQLite).

기존 webgui.py(포트 8899)와 완전히 분리된 독립 앱입니다.
이 파일의 라우트 = REST API 규격. 다른 스택(Cloudflare Workers 등)으로 이식할 때
동일한 경로/요청·응답 형태를 재현하면 프론트 위젯을 그대로 재사용할 수 있습니다.

실행:  python server.py   ->  http://localhost:8700/auth
"""
import os
import json
import secrets

from flask import (Flask, request, jsonify, redirect, make_response,
                   render_template, send_from_directory)

import auth_core as core
from phone_adapters import get_verifier
import social_oauth as social

BASE = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE, "config.json")

# --- config 로드 (없으면 example에서 복사) ---------------------------------

def load_config():
    path = CONFIG_PATH
    if not os.path.exists(path):
        path = os.path.join(BASE, "config.example.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()
core.init_db()

app = Flask(__name__, static_folder="static", template_folder="templates")
COOKIE = "auth_session"
# state -> provider 임시 저장(데모용 메모리; 운영은 서명된 state 권장)
_oauth_states = {}


def is_dev():
    return CONFIG.get("phone", {}).get("provider", "dev") == "dev" and CONFIG.get("reveal_code", True)


# ---------------------------------------------------------------------------
# 위젯 화면
# ---------------------------------------------------------------------------

@app.route("/auth")
def auth_page():
    return render_template(
        "auth.html",
        providers=social.enabled_providers(CONFIG),
        brand=CONFIG.get("brand", "우리 서비스"),
    )


@app.route("/static/<path:p>")
def static_files(p):
    return send_from_directory(app.static_folder, p)


# ---------------------------------------------------------------------------
# 이메일 회원가입 / 로그인
# ---------------------------------------------------------------------------

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    d = request.get_json(force=True, silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    name = (d.get("name") or "").strip()
    phone_token = d.get("phone_token")  # 폰 인증 증표(선택/필수는 정책에 따라)

    if not core.valid_email(email):
        return jsonify(ok=False, error="이메일 형식이 올바르지 않습니다."), 400
    if not core.valid_password(pw):
        return jsonify(ok=False, error="비밀번호는 8자 이상, 영문과 숫자를 포함해야 합니다."), 400
    if core.find_user_by_email(email):
        return jsonify(ok=False, error="이미 가입된 이메일입니다."), 409

    phone, phone_verified = None, 0
    if CONFIG.get("require_phone", True):
        info = core.consume_phone_token(phone_token, purpose="signup") if phone_token else None
        if not info:
            return jsonify(ok=False, error="휴대폰 인증을 먼저 완료해주세요."), 400
        phone, phone_verified = info["phone"], 1

    uid = core.create_user(email=email, password=pw, name=name,
                           phone=phone, phone_verified=phone_verified)
    token = core.create_session(uid)
    resp = jsonify(ok=True, user=core.public_user(core.find_user_by_email(email)))
    _set_cookie(resp, token)
    return resp


@app.route("/api/auth/login", methods=["POST"])
def login():
    d = request.get_json(force=True, silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    user = core.find_user_by_email(email)
    if not user or not user.get("password_hash") or not core.verify_password(pw, user["password_hash"]):
        return jsonify(ok=False, error="이메일 또는 비밀번호가 올바르지 않습니다."), 401
    token = core.create_session(user["id"])
    resp = jsonify(ok=True, user=core.public_user(user))
    _set_cookie(resp, token)
    return resp


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    core.destroy_session(request.cookies.get(COOKIE))
    resp = jsonify(ok=True)
    resp.set_cookie(COOKIE, "", max_age=0)
    return resp


@app.route("/api/auth/me")
def me():
    user = core.get_session_user(request.cookies.get(COOKIE))
    return jsonify(ok=bool(user), user=core.public_user(user))


# ---------------------------------------------------------------------------
# 휴대폰 인증 (OTP)  — 결제에서도 재사용 가능한 증표(token)를 발급
# ---------------------------------------------------------------------------

@app.route("/api/phone/send", methods=["POST"])
def phone_send():
    d = request.get_json(force=True, silent=True) or {}
    raw = d.get("phone") or ""
    purpose = d.get("purpose", "signup")
    if not core.valid_phone(raw):
        return jsonify(ok=False, error="휴대폰 번호 형식이 올바르지 않습니다."), 400
    phone = core.normalize_phone(raw)

    ok, reason = core.can_send_otp(phone)
    if not ok:
        return jsonify(ok=False, error=reason), 429

    code = core.create_otp(phone, purpose)
    verifier = get_verifier(CONFIG)
    result = verifier.send_code(phone, code)
    if not result.get("ok"):
        return jsonify(ok=False, error=result.get("error", "발송 실패")), 502

    payload = {"ok": True, "message": "인증번호를 발송했습니다.", "ttl": core.OTP_TTL}
    if is_dev():  # 개발 모드에서만 코드 노출
        payload["dev_code"] = code
    return jsonify(payload)


@app.route("/api/phone/verify", methods=["POST"])
def phone_verify():
    d = request.get_json(force=True, silent=True) or {}
    raw = d.get("phone") or ""
    code = (d.get("code") or "").strip()
    purpose = d.get("purpose", "signup")
    phone = core.normalize_phone(raw)
    ok, result = core.verify_otp(phone, code, purpose)
    if not ok:
        return jsonify(ok=False, error=result), 400
    # result = 인증 증표 토큰. 회원가입/결제 등에서 이 토큰을 제출하면 됨.
    return jsonify(ok=True, phone_token=result, phone=phone)


# ---------------------------------------------------------------------------
# 간편가입 (소셜 OAuth)
# ---------------------------------------------------------------------------

def _redirect_uri(provider):
    return request.host_url.rstrip("/") + f"/auth/callback/{provider}"


@app.route("/auth/start/<provider>")
def oauth_start(provider):
    p = social.get_provider(provider, CONFIG, _redirect_uri(provider))
    if not p:
        return "지원하지 않는 제공자", 404
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = provider
    return redirect(p.authorize_url(state))


@app.route("/auth/mock/<provider>")
def oauth_mock(provider):
    """개발용 mock 로그인: 실제 제공자 없이 콜백으로 바로 넘김."""
    state = request.args.get("state", "")
    fake_code = secrets.token_hex(4)
    return redirect(f"/auth/callback/{provider}?code={fake_code}&state={state}")


@app.route("/auth/callback/<provider>")
def oauth_callback(provider):
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or _oauth_states.get(state) != provider:
        # mock 흐름은 state가 남아있지 않을 수 있어 dev에서는 통과
        if not (is_dev() and code):
            return "잘못된 요청(state 불일치)", 400
    _oauth_states.pop(state, None)

    p = social.get_provider(provider, CONFIG, _redirect_uri(provider))
    profile = p.exchange(code)
    uid = profile.get("uid")

    user = core.find_user_by_provider(provider, uid)
    if user:
        user_pk = user["id"]
    else:
        # 이메일이 이미 로컬 가입돼 있으면 그 계정에 연결, 아니면 신규 소셜 계정 생성
        existing = core.find_user_by_email(profile.get("email")) if profile.get("email") else None
        user_pk = existing["id"] if existing else core.create_user(
            email=profile.get("email"), name=profile.get("name"),
            provider=provider, provider_uid=uid,
        )
    session_token = core.create_session(user_pk)

    resp = make_response(redirect(CONFIG.get("after_login_redirect", "/auth?logged_in=1")))
    _set_cookie(resp, session_token)
    return resp


# ---------------------------------------------------------------------------
# 결제 재사용 예시: 인증 증표로 폰 소유 확인
# ---------------------------------------------------------------------------

@app.route("/api/phone/check-token", methods=["POST"])
def phone_check_token():
    d = request.get_json(force=True, silent=True) or {}
    info = core.consume_phone_token(d.get("phone_token"), purpose=d.get("purpose"))
    if not info:
        return jsonify(ok=False, error="유효하지 않거나 만료된 인증입니다."), 400
    return jsonify(ok=True, phone=info["phone"])


# ---------------------------------------------------------------------------

def _set_cookie(resp, token):
    resp.set_cookie(
        COOKIE, token, httponly=True, samesite="Lax",
        secure=CONFIG.get("cookie_secure", False),
        max_age=core.SESSION_TTL,
    )


if __name__ == "__main__":
    port = CONFIG.get("port", 8700)
    print(f"[auth-module] http://localhost:{port}/auth  (phone provider={CONFIG.get('phone',{}).get('provider')})")
    app.run(host="127.0.0.1", port=port, debug=True)
