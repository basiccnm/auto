# -*- coding: utf-8 -*-
"""쿠팡 파트너스 딥링크 — 긴 추적 주소를 `link.coupang.com/a/XXXX` 로 줄인다. 2026-07-27

    python scripts/coupang_deeplink.py <URL> [URL ...]
    python scripts/coupang_deeplink.py --file 주소목록.txt      한 줄에 하나

🔴 **검색 API 의 productUrl 도 이미 제휴가 붙은 주소다.** 딥링크는 오로지 **짧게** 만들려는 것 —
   수수료가 더 붙거나 하지 않는다. 고정댓글처럼 사람이 읽는 자리에 쓸 때만 줄인다.

🔴 한 번에 여러 개를 넣을 수 있다(coupangUrls 배열). 호출을 아끼려면 모아서 한 번에.

🔴 응답은 `data:[{originalUrl, shortenUrl, landingUrl}]` 이다.
   짧은 주소는 `shortenUrl`. landingUrl 은 긴 원본이라 헷갈리지 말 것.
"""
import hashlib
import hmac
import io
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
sys.stdout.reconfigure(encoding="utf-8")


def load_env():
    env = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def sign(method, url_path, secret, access):
    """CEA HMAC-SHA256. signed-date 는 GMT 여야 한다(로컬시간 쓰면 401)."""
    parts = url_path.split("?")
    path, query = parts[0], (parts[1] if len(parts) > 1 else "")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return (f"CEA algorithm=HmacSHA256, access-key={access}, "
            f"signed-date={dt}, signature={sig}")


def shorten(urls, ak, sk):
    body = json.dumps({"coupangUrls": urls}).encode("utf-8")
    req = urllib.request.Request(DOMAIN + PATH, data=body, method="POST")
    req.add_header("Authorization", sign("POST", PATH, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    try:
        with urllib.request.urlopen(req, timeout=25,
                                    context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("[X] HTTP", e.code, e.read().decode(errors="replace")[:400])
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--file" in sys.argv:
        urls = [l.strip() for l in io.open(args[0], encoding="utf-8") if l.strip()]
    else:
        urls = args
    if not urls:
        print(__doc__)
        return 1

    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 쿠팡 키가 없습니다.")
        return 1

    res = shorten(urls, ak, sk)
    if not res:
        return 1
    if res.get("rCode") not in (None, "0", 0):
        print("[X]", res.get("rCode"), res.get("rMessage"))
        return 1
    for d in res.get("data", []):
        print(d.get("shortenUrl"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
