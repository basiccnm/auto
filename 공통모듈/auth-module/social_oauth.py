"""
social_oauth.py — 간편가입(소셜 로그인) 제공자.

각 제공자는 두 단계:
  1) authorize_url(state)  -> 사용자를 제공자 로그인 페이지로 보낼 URL
  2) exchange(code)        -> 콜백으로 받은 code를 프로필로 교환
                              {provider, uid, email, name, phone?} 반환

키(client_id/secret)가 config에 없으면 provider가 자동으로 'mock' 모드가 되어,
실제 카카오/구글 앱 없이도 가입 흐름 전체를 로컬에서 테스트할 수 있습니다.
"""
import json
import urllib.parse
import urllib.request


def _post_form(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


class Provider:
    name = "base"

    def __init__(self, cfg, redirect_uri):
        self.cfg = cfg or {}
        self.redirect_uri = redirect_uri
        self.mock = not (self.cfg.get("client_id") and self.cfg.get("client_secret"))

    def authorize_url(self, state):
        raise NotImplementedError

    def exchange(self, code):
        raise NotImplementedError


class KakaoProvider(Provider):
    name = "kakao"

    def authorize_url(self, state):
        if self.mock:
            return f"/auth/mock/kakao?state={state}"
        q = urllib.parse.urlencode({
            "client_id": self.cfg["client_id"],
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "account_email profile_nickname",
        })
        return "https://kauth.kakao.com/oauth/authorize?" + q

    def exchange(self, code):
        if self.mock:
            return {"provider": "kakao", "uid": f"mock_{code}",
                    "email": f"kakao_{code}@example.com", "name": "카카오테스트"}
        tok = _post_form(
            "https://kauth.kakao.com/oauth/token",
            {
                "grant_type": "authorization_code",
                "client_id": self.cfg["client_id"],
                "client_secret": self.cfg.get("client_secret", ""),
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        prof = _get_json(
            "https://kapi.kakao.com/v2/user/me",
            {"Authorization": f"Bearer {tok['access_token']}"},
        )
        acc = prof.get("kakao_account", {})
        return {
            "provider": "kakao",
            "uid": str(prof.get("id")),
            "email": acc.get("email"),
            "name": (acc.get("profile") or {}).get("nickname"),
        }


class GoogleProvider(Provider):
    name = "google"

    def authorize_url(self, state):
        if self.mock:
            return f"/auth/mock/google?state={state}"
        q = urllib.parse.urlencode({
            "client_id": self.cfg["client_id"],
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        })
        return "https://accounts.google.com/o/oauth2/v2/auth?" + q

    def exchange(self, code):
        if self.mock:
            return {"provider": "google", "uid": f"mock_{code}",
                    "email": f"google_{code}@example.com", "name": "구글테스트"}
        tok = _post_form(
            "https://oauth2.googleapis.com/token",
            {
                "grant_type": "authorization_code",
                "client_id": self.cfg["client_id"],
                "client_secret": self.cfg["client_secret"],
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        prof = _get_json(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            {"Authorization": f"Bearer {tok['access_token']}"},
        )
        return {
            "provider": "google",
            "uid": str(prof.get("id")),
            "email": prof.get("email"),
            "name": prof.get("name"),
        }


_REGISTRY = {"kakao": KakaoProvider, "google": GoogleProvider}


def get_provider(name, cfg, redirect_uri):
    cls = _REGISTRY.get(name)
    if not cls:
        return None
    social_cfg = (cfg.get("social", {}) or {}).get(name, {})
    return cls(social_cfg, redirect_uri)


def enabled_providers(cfg):
    """config.social.enabled 목록 (기본: kakao, google)."""
    return (cfg.get("social", {}) or {}).get("enabled", ["kakao", "google"])
