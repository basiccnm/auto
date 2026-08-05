"""
auth_core.py — 스택 비종속 회원가입/인증 코어 로직.

이 파일은 Flask/HTTP 계층과 분리돼 있습니다. 다른 백엔드(Cloudflare Workers 등)로
이식할 때는 이 파일의 함수 시그니처(=REST 규격)를 그대로 재현하면 됩니다.

저장소: SQLite (portable, 서버 불필요). 실제 서비스에선 D1/Postgres 어댑터로 교체 가능.
"""
import sqlite3
import os
import time
import hmac
import hashlib
import secrets
import base64
import json
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "auth.db")

# ---------------------------------------------------------------------------
# DB 초기화
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE,
            password_hash TEXT,                 -- 소셜 전용 계정은 NULL
            name          TEXT,
            phone         TEXT,                 -- E.164 정규화된 번호 (예: +821012345678)
            phone_verified INTEGER DEFAULT 0,
            provider      TEXT DEFAULT 'local', -- local / kakao / google / naver / apple
            provider_uid  TEXT,                 -- 소셜 제공자 고유 id
            ci            TEXT,                 -- 본인인증 시 채워짐 (결제 재사용)
            di            TEXT,
            created_at    INTEGER,
            UNIQUE(provider, provider_uid)
        );

        CREATE TABLE IF NOT EXISTS otp_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL,
            code_hash   TEXT NOT NULL,
            purpose     TEXT DEFAULT 'signup',  -- signup / login / payment
            expires_at  INTEGER NOT NULL,
            attempts    INTEGER DEFAULT 0,
            consumed    INTEGER DEFAULT 0,
            created_at  INTEGER
        );

        CREATE TABLE IF NOT EXISTS phone_verifications (
            token       TEXT PRIMARY KEY,       -- 인증 완료 증표 (결제 등에서 재사용)
            phone       TEXT NOT NULL,
            purpose     TEXT,
            ci          TEXT,
            di          TEXT,
            verified_at INTEGER,
            expires_at  INTEGER
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token       TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            created_at  INTEGER,
            expires_at  INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_codes(phone);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 비밀번호 해시 (표준 라이브러리 pbkdf2, 외부 의존성 없음)
# ---------------------------------------------------------------------------

_PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2$sha256${_PBKDF2_ROUNDS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, h, rounds, b_salt, b_dk = stored.split("$")
        salt = base64.b64decode(b_salt)
        expected = base64.b64decode(b_dk)
        dk = hashlib.pbkdf2_hmac(h, password.encode(), salt, int(rounds))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 유효성 검사
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(email: str) -> bool:
    return bool(email and EMAIL_RE.match(email))


def valid_password(pw: str) -> bool:
    # 8자 이상, 영문+숫자 포함
    return bool(pw and len(pw) >= 8 and re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw))


def normalize_phone(phone: str, default_cc: str = "82") -> str:
    """한국 휴대폰 번호를 E.164(+82...)로 정규화. 010-1234-5678 -> +821012345678"""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("0"):
        digits = default_cc + digits[1:]
    elif not digits.startswith(default_cc):
        # 이미 국가코드 없이 들어온 경우
        digits = default_cc + digits
    return "+" + digits


def valid_phone(phone: str) -> bool:
    p = normalize_phone(phone)
    return bool(re.match(r"^\+82(10|11|16|17|18|19)\d{7,8}$", p))


# ---------------------------------------------------------------------------
# OTP (SMS 인증번호)
# ---------------------------------------------------------------------------

OTP_TTL = 180          # 3분
OTP_MAX_ATTEMPTS = 5   # 코드당 검증 시도 한도
OTP_RESEND_COOLDOWN = 30   # 재발송 최소 간격(초)
OTP_HOURLY_LIMIT = 5       # 번호당 시간당 발송 한도


def _hash_code(phone: str, code: str) -> str:
    return hashlib.sha256(f"{phone}:{code}".encode()).hexdigest()


def can_send_otp(phone: str):
    """레이트리밋 체크. (ok, reason) 반환."""
    conn = get_db()
    now = int(time.time())
    row = conn.execute(
        "SELECT created_at FROM otp_codes WHERE phone=? ORDER BY created_at DESC LIMIT 1",
        (phone,),
    ).fetchone()
    if row and now - row["created_at"] < OTP_RESEND_COOLDOWN:
        conn.close()
        wait = OTP_RESEND_COOLDOWN - (now - row["created_at"])
        return False, f"{wait}초 후 재발송할 수 있습니다."
    cnt = conn.execute(
        "SELECT COUNT(*) c FROM otp_codes WHERE phone=? AND created_at > ?",
        (phone, now - 3600),
    ).fetchone()["c"]
    conn.close()
    if cnt >= OTP_HOURLY_LIMIT:
        return False, "시간당 발송 한도를 초과했습니다. 잠시 후 다시 시도하세요."
    return True, None


def create_otp(phone: str, purpose: str = "signup") -> str:
    """6자리 코드 생성·저장. 평문 코드를 반환(발송용, DB엔 해시만 저장)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = int(time.time())
    conn = get_db()
    conn.execute(
        "INSERT INTO otp_codes(phone, code_hash, purpose, expires_at, created_at) VALUES(?,?,?,?,?)",
        (phone, _hash_code(phone, code), purpose, now + OTP_TTL, now),
    )
    conn.commit()
    conn.close()
    return code


def verify_otp(phone: str, code: str, purpose: str = "signup"):
    """OTP 검증. 성공 시 인증 증표 토큰 발급. (ok, token_or_error) 반환."""
    now = int(time.time())
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM otp_codes WHERE phone=? AND purpose=? AND consumed=0
           ORDER BY created_at DESC LIMIT 1""",
        (phone, purpose),
    ).fetchone()
    if not row:
        conn.close()
        return False, "인증번호를 먼저 발송해주세요."
    if now > row["expires_at"]:
        conn.close()
        return False, "인증번호가 만료되었습니다. 다시 발송해주세요."
    if row["attempts"] >= OTP_MAX_ATTEMPTS:
        conn.close()
        return False, "시도 횟수를 초과했습니다. 다시 발송해주세요."

    if not hmac.compare_digest(row["code_hash"], _hash_code(phone, code or "")):
        conn.execute("UPDATE otp_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return False, "인증번호가 일치하지 않습니다."

    # 성공: 코드 소진 + 인증 증표 발급
    conn.execute("UPDATE otp_codes SET consumed=1 WHERE id=?", (row["id"],))
    token = secrets.token_urlsafe(24)
    conn.execute(
        """INSERT INTO phone_verifications(token, phone, purpose, verified_at, expires_at)
           VALUES(?,?,?,?,?)""",
        (token, phone, purpose, now, now + 1800),  # 증표 30분 유효
    )
    conn.commit()
    conn.close()
    return True, token


def consume_phone_token(token: str, purpose: str = None):
    """인증 증표 검증 후 소진(1회성). 유효하면 phone 반환, 아니면 None.
    성공 시 토큰을 삭제해 재사용을 막는다 (결제/가입 각각 새 토큰 필요)."""
    if not token:
        return None
    now = int(time.time())
    conn = get_db()
    row = conn.execute("SELECT * FROM phone_verifications WHERE token=?", (token,)).fetchone()
    if not row or now > row["expires_at"] or (purpose and row["purpose"] != purpose):
        conn.close()
        return None
    conn.execute("DELETE FROM phone_verifications WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return {"phone": row["phone"], "ci": row["ci"], "di": row["di"]}


# ---------------------------------------------------------------------------
# 사용자 / 세션
# ---------------------------------------------------------------------------

SESSION_TTL = 60 * 60 * 24 * 14  # 14일


def find_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_user_by_provider(provider, provider_uid):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE provider=? AND provider_uid=?", (provider, provider_uid)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(email=None, password=None, name=None, phone=None,
                phone_verified=0, provider="local", provider_uid=None,
                ci=None, di=None):
    conn = get_db()
    pw_hash = hash_password(password) if password else None
    cur = conn.execute(
        """INSERT INTO users(email, password_hash, name, phone, phone_verified,
                             provider, provider_uid, ci, di, created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (email, pw_hash, name, phone, phone_verified, provider, provider_uid,
         ci, di, int(time.time())),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES(?,?,?,?)",
        (token, user_id, now, now + SESSION_TTL),
    )
    conn.commit()
    conn.close()
    return token


def get_session_user(token):
    if not token:
        return None
    now = int(time.time())
    conn = get_db()
    row = conn.execute(
        """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token=? AND s.expires_at > ?""",
        (token, now),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def destroy_session(token):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()


def public_user(user: dict) -> dict:
    """클라이언트로 내보내도 되는 필드만."""
    if not user:
        return None
    return {
        "id": user["id"],
        "email": user.get("email"),
        "name": user.get("name"),
        "phone": user.get("phone"),
        "phone_verified": bool(user.get("phone_verified")),
        "provider": user.get("provider"),
    }
