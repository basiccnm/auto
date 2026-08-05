# -*- coding: utf-8 -*-
"""네이버 월간 검색량 — 검색광고 키워드도구 API. 2026-07-28

    python scripts/naver_keyword.py 뿌링클원가 치킨원가 엽떡원가
    python scripts/naver_keyword.py --file 키워드.txt

🔴 **네이버는 서치어드바이저·애널리틱스 조회 API를 안 준다.**(2026-07-28 확인)
   그래서 "우리 사이트에 네이버 검색으로 몇 명 왔나"는 화면으로만 볼 수 있다.
   대신 **검색광고 키워드도구**로 "그 말을 한 달에 몇 명이 찾나"는 가져올 수 있고,
   어떤 글을 쓸지 정하는 데는 이쪽이 더 쓸모 있다.

🔴 .env 에 세 값이 필요하다 (검색광고 관리시스템 → 도구 → API 사용 관리)
     NAVER_AD_API_KEY      = 액세스 라이선스
     NAVER_AD_SECRET_KEY   = 비밀키
     NAVER_AD_CUSTOMER_ID  = 고객 ID (숫자)
   ⚠️ 검색광고 계정은 네이버 아이디와 별개다. 광고를 집행하지 않아도 API 는 쓸 수 있다.

🔴 키워드는 **공백 없이** 넣는다. 네이버가 그렇게 받는다("뿌링클 원가" ✕ / "뿌링클원가" ○)
🔴 한 번에 5개까지. 검색량이 10 미만이면 네이버가 "< 10" 으로 준다 — 0 이 아니다.
"""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "https://api.searchad.naver.com"
PATH = "/keywordstool"
sys.stdout.reconfigure(encoding="utf-8")


def env():
    d = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                d[k.strip()] = v.strip()
    return d


def sign(ts, method, path, secret):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()).decode()


def ask(keywords, e):
    ts = str(int(time.time() * 1000))
    q = urllib.parse.urlencode({"hintKeywords": ",".join(keywords), "showDetail": "1"})
    req = urllib.request.Request(f"{HOST}{PATH}?{q}")
    req.add_header("X-Timestamp", ts)
    req.add_header("X-API-KEY", e["NAVER_AD_API_KEY"])
    req.add_header("X-Customer", e["NAVER_AD_CUSTOMER_ID"])
    req.add_header("X-Signature", sign(ts, "GET", PATH, e["NAVER_AD_SECRET_KEY"]))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def num(v):
    """'< 10' 은 0 이 아니라 '10 미만'이다. 정렬을 위해 5로 친다."""
    if isinstance(v, str) and "<" in v:
        return 5
    try:
        return int(v)
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="*")
    ap.add_argument("--file")
    a = ap.parse_args()
    words = a.words
    if a.file:
        words = [l.strip() for l in io.open(a.file, encoding="utf-8") if l.strip()]
    if not words:
        print(__doc__)
        return 1

    e = env()
    miss = [k for k in ("NAVER_AD_API_KEY", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID") if not e.get(k)]
    if miss:
        print("[X] .env 에 없는 값:", ", ".join(miss))
        return 1

    seen = {}
    for i in range(0, len(words), 5):
        chunk = [w.replace(" ", "") for w in words[i:i + 5]]
        try:
            r = ask(chunk, e)
        except urllib.error.HTTPError as ex:
            print("[X] HTTP", ex.code, ex.read().decode(errors="replace")[:200])
            return 1
        for x in r.get("keywordList", []):
            pc, mo = num(x.get("monthlyPcQcCnt")), num(x.get("monthlyMobileQcCnt"))
            seen[x["relKeyword"]] = (pc, mo, pc + mo, x.get("compIdx", ""))
        time.sleep(0.4)

    print(f"{'키워드':<22}{'PC':>7}{'모바일':>8}{'합계':>8}  경쟁")
    for k, (pc, mo, tot, comp) in sorted(seen.items(), key=lambda x: -x[1][2])[:40]:
        print(f"{k[:22]:<22}{pc:>7,}{mo:>8,}{tot:>8,}  {comp}")


if __name__ == "__main__":
    sys.exit(main())
