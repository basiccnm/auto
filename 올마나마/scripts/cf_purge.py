# -*- coding: utf-8 -*-
"""Cloudflare 엣지 캐시 퍼지 (2026-07-25 신설)

배포 후 라이브에 옛 페이지가 남는 문제 때문에 매번 대시보드에서 손으로 눌렀다.
그걸 없애려고 만든 것. 배포 직후에 실행한다.

사용:
    python scripts/cf_purge.py                 # 전체 퍼지
    python scripts/cf_purge.py dish_pizza m34  # 특정 경로만

.env 에 아래 두 줄이 있어야 한다:
    OLMANAMA_CF_PURGE_TOKEN=...   # 권한: Zone > Cache Purge > Purge, olmanama.com 한 존만
    OLMANAMA_CF_ZONE_ID=...       # olmanama.com 대시보드 Overview 우측 하단

⚠️ 이름을 `CF_API_TOKEN` 으로 두지 말 것 (2026-07-25 실제 사고).
wrangler 가 .env 의 `CF_API_TOKEN` / `CLOUDFLARE_API_TOKEN` 을 **자기 인증 토큰으로 집어간다.**
퍼지 전용 토큰에는 배포 권한이 없어서 `wrangler deploy` 가
"Failed to automatically retrieve account IDs" 로 죽는다. 그래서 접두어를 붙였다.
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.olmanama.com"
URLS_PER_CALL = 30      # Cloudflare 한계. 넘기면 요청이 거절된다
BATCH_SLEEP = 1.0       # 배치 사이 간격 — 캐시가 한꺼번에 비어 워커로 몰리는 걸 늦춘다


def _api(token, zone, body):
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/zones/%s/purge_cache" % zone,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _purge_batched(token, zone, urls, n_paths):
    """URL 30개씩 끊어서 지운다. 한 배치라도 실패하면 실패로 본다."""
    total = (len(urls) + URLS_PER_CALL - 1) // URLS_PER_CALL
    print("경로 %d개(URL %d개) → %d배치로 나눠 지운다." % (n_paths, len(urls), total))
    bad = 0
    for i in range(0, len(urls), URLS_PER_CALL):
        chunk = urls[i:i + URLS_PER_CALL]
        no = i // URLS_PER_CALL + 1
        try:
            res = _api(token, zone, {"files": chunk})
        except urllib.error.HTTPError as e:
            print("   %d/%d ❌ HTTP %s %s" % (no, total, e.code,
                                             e.read().decode("utf-8", "replace")[:160]))
            bad += 1
        else:
            if res.get("success"):
                print("   %d/%d ✅ %d건" % (no, total, len(chunk)))
            else:
                print("   %d/%d ❌ %s" % (no, total,
                                         json.dumps(res.get("errors"), ensure_ascii=False)[:160]))
                bad += 1
        if no < total:
            time.sleep(BATCH_SLEEP)
    if bad:
        print("❌ %d/%d 배치 실패 — 그 경로는 안 지워졌다." % (bad, total))
        return 1
    print("✅ 캐시 퍼지 완료 (경로 %d개 · %d배치)" % (n_paths, total))
    return 0


def load_env():
    """.env 를 읽어 dict로. python-dotenv 의존 없이 최소 파싱(다른 스크립트와 같은 방식)."""
    env = {}
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("OLMANAMA_CF_PURGE_TOKEN", "OLMANAMA_CF_ZONE_ID"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def purge(paths=None):
    env = load_env()
    token = env.get("OLMANAMA_CF_PURGE_TOKEN")
    zone = env.get("OLMANAMA_CF_ZONE_ID")
    if not token or not zone:
        print("❌ .env 에 OLMANAMA_CF_PURGE_TOKEN / OLMANAMA_CF_ZONE_ID 가 없다.")
        return 1

    paths = [p for p in (paths or []) if p != "--all"]
    full = "--all" in (sys.argv[1:] or [])

    if paths:
        # 경로 지정 퍼지는 www / 무www 둘 다 지워야 한다(둘이 별개 캐시 키)
        urls = []
        for p in paths:
            p = p.lstrip("/")
            urls.append("%s/%s" % (SITE, p))
            urls.append("https://olmanama.com/%s" % p)
        # 🔴 Cloudflare 는 요청당 URL 30개까지다. 넘겨 보내면 에러로 떨어져
        #    "지운 줄 알았는데 안 지워진" 상태가 된다(2026-07-26). 그래서 여기서 쪼갠다.
        #    HTML 경로만 지우면 일러스트·로고는 캐시에 남아 1015 위험도 낮다.
        if len(urls) > URLS_PER_CALL:
            return _purge_batched(token, zone, urls, len(paths))
        body = {"files": urls}
        what = "%d개 경로" % len(paths)
    elif full:
        # 🚨 전체 퍼지는 사고를 낸다 (2026-07-25 실제 발생).
        #  캐시가 비면 페이지 한 장이 HTML+일러스트+로고+OG 수십 건을 전부 워커로 보낸다.
        #  그 순간 레이트리밋 규칙에 걸려 사이트가 **error 1015 (HTTP 429)** 를 뱉었다.
        #  캐시가 다시 차면 저절로 낫지만, 그 사이 방문자는 사이트를 못 본다.
        print("⚠️  전체 퍼지 — 캐시가 비는 몇 분간 error 1015(429)가 뜰 수 있다.")
        print("    바뀐 페이지만 지우는 게 안전하다:  python scripts/cf_purge.py menu_34 dish_pizza")
        body = {"purge_everything": True}
        what = "전체"
    else:
        print("어느 경로를 지울지 적어라.  예:  python scripts/cf_purge.py menu_34 dish_pizza prices")
        print("정말 전체를 비우려면 --all 을 명시할 것 (1015 위험 — 위 주석 참고).")
        return 2

    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/zones/%s/purge_cache" % zone,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        print("❌ HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:400]))
        return 1

    # success 가 true 여야 실제로 지워진 것. 출력만 보고 넘기지 말 것
    if res.get("success"):
        print("✅ 캐시 퍼지 완료 (%s)" % what)
        return 0
    print("❌ 실패: %s" % json.dumps(res.get("errors"), ensure_ascii=False)[:400])
    return 1


if __name__ == "__main__":
    sys.exit(purge(sys.argv[1:] or None))
