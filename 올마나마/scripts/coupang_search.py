# -*- coding: utf-8 -*-
"""쿠팡 파트너스 상품검색 — 재료명으로 조회해 가격·로켓배송·제휴링크를 받는다.

한도: **/products/search 는 분당 최대 50회.** (파트너스 Open API 문서, 2026-07-24 확인)
   참고로 /reports/* 는 시간당 500회, /deeplink 는 별도.

   ⚠️ 한때 이 파일에 "시간당 10회"라고 적혀 있었는데 **출처 없는 값이었다.**
      확인도 안 하고 "(확인)"이라고 주석까지 달아뒀고, 그걸 믿고 호출을 아끼느라
      작업을 시간 단위로 미룰 뻔했다. 한도는 반드시 문서로 확인하고 적을 것.

   캐싱 금지 규정(웹 5분)은 **Reco API 전용**이다. 검색 API에는 해당 문구가 없다.

검색 응답의 productUrl은 **이미 제휴 추적이 붙은 주소**다 — 딥링크 API를 따로
부를 필요가 없다. (상품 주소 뒤에 코드를 붙이는 식으로는 수수료가 안 붙는다)

결과는 data/research/coupang/<키워드>.json 에 쌓는다. 같은 키워드가 이미 있으면
건너뛴다 — 재실행으로 한도를 태우지 않기 위해서다. 다시 받으려면 --force.
"""
import os, sys, io, json, hmac, hashlib, ssl, time
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "data", "research", "coupang")
DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"

MAX_CALLS = 200        # 안전장치일 뿐 한도가 아니다(무한루프 방지용)
LIMIT = 10             # ⚠️ **최대 10이다.** 실측(2026-07-24): 5·10은 정상,
                       #    20·30·50·100은 HTTP 200인데 rCode=400 + 빈 목록이 온다.
                       #    "많이 받으면 이득"이라고 50으로 올렸다가 18회를 헛으로 태웠다.


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
    """CEA HMAC-SHA256. signed-date는 GMT여야 한다(로컬시간 쓰면 401)."""
    parts = url_path.split("?")
    path, query = parts[0], (parts[1] if len(parts) > 1 else "")
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    msg = dt + method + path + query
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return (f"CEA algorithm=HmacSHA256, access-key={access}, "
            f"signed-date={dt}, signature={sig}")


def search(keyword, ak, sk):
    url_path = f"{PATH}?keyword={urllib.parse.quote(keyword)}&limit={LIMIT}"
    req = urllib.request.Request(DOMAIN + url_path, method="GET")
    req.add_header("Authorization", sign("GET", url_path, sk, ak))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=25,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    gap = 1.3
    for a in sys.argv[1:]:
        if a.startswith("--gap="):
            gap = float(a.split("=", 1)[1])
    if not args:
        print("사용법: python scripts/coupang_search.py 키워드목록.json")
        return 1
    words = json.loads(io.open(args[0], encoding="utf-8").read())

    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY", ""), env.get("COUPANG_SECRET_KEY", "")
    if not ak or not sk:
        print("[X] .env 에 키가 없습니다. 쿠팡키설정.bat 을 먼저 실행하세요.")
        return 1

    os.makedirs(OUTDIR, exist_ok=True)
    used = 0
    for kw in words:
        if used >= MAX_CALLS:
            print(f"\n[i] 이번 시간 한도({MAX_CALLS}회) 다 썼습니다. 1시간 뒤 나머지를 이어서.")
            print("    남은 키워드:", ", ".join(words[words.index(kw):]))
            break
        out = os.path.join(OUTDIR, kw.replace("/", "_") + ".json")
        if os.path.exists(out) and not force:
            print(f"skip  {kw} (이미 받아둠)")
            continue
        try:
            body = search(kw, ak, sk)
            used += 1
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")[:200]
            print(f"[X] {kw} HTTP {e.code} {raw}")
            if e.code == 429:
                print("    → 한도 초과. 즉시 중단합니다(누적되면 계정 제한).")
                break
            continue
        except Exception as e:
            print(f"[X] {kw} {e}")
            continue

        # ⚠️ 이 API는 실패해도 HTTP 200을 준다. rCode를 안 보면 "0건 정상"으로 착각한다.
        if str(body.get("rCode")) != "0":
            print(f"[X] {kw} rCode={body.get('rCode')} {str(body.get('rMessage'))[:80]}")
            continue
        items = (body.get("data") or {}).get("productData") or []
        rec = {"keyword": kw, "fetched_at": datetime.now().isoformat(timespec="seconds"),
               "count": len(items),
               "items": [{"name": it.get("productName"), "price": it.get("productPrice"),
                          "rocket": it.get("isRocket"), "free": it.get("isFreeShipping"),
                          "id": it.get("productId"), "url": it.get("productUrl"),
                          "image": it.get("productImage")} for it in items]}
        io.open(out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
        rk = sum(1 for i in rec["items"] if i["rocket"])
        print(f"OK    {kw:14} {len(items):3}건 (로켓 {rk}건)  호출 {used}/{MAX_CALLS}")
        time.sleep(gap)   # 기본 1.3초 = 분당 46회로 한도(50) 안쪽. --gap 초 로 더 느리게

    print(f"\n이번 실행 호출 {used}회 · 저장 위치 data/research/coupang/")
    return 0


sys.exit(main())
