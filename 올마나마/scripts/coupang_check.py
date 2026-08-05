# -*- coding: utf-8 -*-
"""쿠팡 파트너스 Open API 연결 확인 — 딱 1회만 호출한다.

🔴 호출 한도가 **시간당 10회**다(2026-07-24 확인). 게다가 한도 초과가 3회 쌓이면
   파트너스 계정 자체가 API 제한을 먹는다 — 그 계정은 수수료 수익이 걸린 계정이라
   테스트로 낭비하면 안 된다. 그래서 이 스크립트는 **한 번만** 호출하고 끝낸다.
   반복 실행 금지. 결과는 아래 파일로 남겨 재실행 없이 다시 볼 수 있게 한다.

키: .env 의 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY (쿠팡키설정.bat 이 만든다)
"""
import os, sys, io, json, time, hmac, hashlib, ssl
import urllib.request, urllib.error
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "research", "coupang_check.json")

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"


def load_env():
    """.env 를 읽어 dict로. python-dotenv 의존 없이 최소 파싱(naver/config.py와 같은 방식)."""
    env = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    # 환경변수가 있으면 그쪽이 우선
    for k in ("COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def sign(method, url_path, secret, access):
    """쿠팡 CEA HMAC-SHA256 서명.
    signed-date 는 GMT 기준 yymmddTHHMMSSZ 형식이어야 한다(로컬시간 쓰면 401)."""
    parts = url_path.split("?")
    path, query = parts[0], (parts[1] if len(parts) > 1 else "")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return (f"CEA algorithm=HmacSHA256, access-key={access}, "
            f"signed-date={dt}, signature={sig}")


def main():
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없습니다.")
        print("    쿠팡키설정.bat 을 실행해 키를 넣어주세요.")
        return 1

    print(f"[i] 키 확인: ACCESS {len(ak)}자 / SECRET {len(sk)}자")
    print("[i] 호출 1회만 합니다 (시간당 10회 한도 · 초과 누적 시 계정 제한 위험)")

    keyword = "양파 1kg"
    url_path = f"{PATH}?keyword={urllib.parse.quote(keyword)}&limit=5"
    req = urllib.request.Request(DOMAIN + url_path, method="GET")
    req.add_header("Authorization", sign("GET", url_path, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")

    result = {"checked_at": datetime.now().isoformat(timespec="seconds"),
              "keyword": keyword, "ok": False}
    try:
        with urllib.request.urlopen(req, timeout=20,
                                    context=ssl.create_default_context()) as r:
            body = json.loads(r.read().decode("utf-8"))
        result["http"] = 200
        result["rCode"] = body.get("rCode")
        result["rMessage"] = body.get("rMessage")
        items = (body.get("data") or {}).get("productData") or []
        result["count"] = len(items)
        result["ok"] = bool(items)
        result["sample"] = [{
            "name": it.get("productName", "")[:40],
            "price": it.get("productPrice"),
            "isRocket": it.get("isRocket"),
        } for it in items[:3]]
        print(f"[O] 연결 성공 — 상품 {len(items)}건")
        for s in result["sample"]:
            print(f"      {s['price']:>9,}원  {s['name']}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:400]
        result["http"] = e.code
        result["error"] = raw
        print(f"[X] HTTP {e.code}")
        print(f"    {raw}")
        if e.code == 401:
            print("    → 키가 틀렸거나 서명 시각이 어긋남(PC 시계 확인)")
        elif e.code == 429:
            print("    → 호출 한도 초과. 1시간 기다렸다 다시 (누적되면 계정 제한)")
    except Exception as e:
        result["error"] = str(e)
        print(f"[X] {e}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[i] 결과 저장: data/research/coupang_check.json")
    print("    (재호출 말고 이 파일을 보세요 — 한도 아낍니다)")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
